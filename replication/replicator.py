"""
Replication: leader-to-follower write propagation.

Transport decision (explicit, per the fixed design): the leader opens
its own outbound TCP connection to each follower's TCP server port and
replays write commands using the *same* RESP protocol clients use
(server/protocol.py). A follower can't tell the difference between a
command from a real client and one from the leader's replication
stream -- it just executes it. This keeps the system to one protocol
instead of inventing a second one.

Consistency model (say this plainly in an interview, don't dodge it):
this is asynchronous replication. The leader acknowledges a write to
the client as soon as it's applied locally and appended to its own
AOF -- it does NOT wait for followers to confirm. That means a leader
crash between "acked to client" and "replicated to followers" loses
that write on failover. This is a deliberate simplicity/availability
trade-off, not an oversight -- and it's the same trade-off Redis makes
by default (Redis calls this WAIT if you want stronger guarantees).
"""
from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from server.protocol import encode_array, parse_resp, ProtocolError

logger = logging.getLogger("districache.replication")


@dataclass
class FollowerConnection:
    host: str
    port: int
    reader: Optional[asyncio.StreamReader] = None
    writer: Optional[asyncio.StreamWriter] = None
    connected: bool = False
    lag_ops: int = 0  # commands sent but not yet ack'd -- exposed via /cluster/stats

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"


class ReplicationManager:
    """
    Owned by the leader node. Call `replicate(op, key, value, ttl)` after
    every local write; it fans the command out to all followers.
    Runs a background reconnect loop per follower so a transient network
    blip doesn't require restarting the leader.
    """

    def __init__(self, retry_interval_seconds: float = 2.0):
        self._followers: dict[str, FollowerConnection] = {}
        self._retry_interval = retry_interval_seconds
        self._connect_tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    def add_follower(self, host: str, port: int) -> None:
        conn = FollowerConnection(host=host, port=port)
        self._followers[conn.address] = conn
        task = asyncio.ensure_future(self._maintain_connection(conn))
        self._connect_tasks[conn.address] = task

    async def _maintain_connection(self, conn: FollowerConnection) -> None:
        """Keep (re)connecting to a follower forever, with backoff on failure."""
        while True:
            try:
                reader, writer = await asyncio.open_connection(conn.host, conn.port)
                conn.reader, conn.writer = reader, writer
                conn.connected = True
                logger.info(f"replication: connected to follower {conn.address}")
                # Block here until the connection actually drops (read
                # returns empty), so we notice disconnects promptly.
                await reader.read(1)
                raise ConnectionError("follower connection closed")
            except (ConnectionError, OSError) as e:
                conn.connected = False
                conn.reader, conn.writer = None, None
                logger.warning(f"replication: lost connection to {conn.address} ({e}); retrying")
                await asyncio.sleep(self._retry_interval)

    async def replicate(
        self, op: str, key: str, value: Optional[str] = None, ttl_seconds: Optional[float] = None
    ) -> None:
        """
        Fan out one write command to all currently-connected followers.
        Best-effort: a disconnected follower is skipped (it will catch
        up via its own AOF + a future full resync -- resync is out of
        scope for this project's core; documented as a known gap).
        """
        args = [op, key]
        if value is not None:
            args.append(value)
        if ttl_seconds is not None:
            args.append(str(ttl_seconds))
        payload = encode_array(args)

        async with self._lock:
            targets = [c for c in self._followers.values() if c.connected and c.writer]

        for conn in targets:
            try:
                conn.writer.write(payload)
                await conn.writer.drain()
            except (ConnectionError, OSError) as e:
                logger.warning(f"replication: write to {conn.address} failed ({e})")
                conn.connected = False

    def follower_status(self) -> list[dict]:
        return [
            {"address": c.address, "connected": c.connected}
            for c in self._followers.values()
        ]

    async def shutdown(self) -> None:
        for task in self._connect_tasks.values():
            task.cancel()
        for conn in self._followers.values():
            if conn.writer:
                conn.writer.close()


class ReplicaApplier:
    """
    Owned by a follower node. Reads a persistent stream of replicated
    commands from the leader connection and applies them to the local
    Store (and local AOF, via the same code path a real client write
    would take) -- so a follower's own on-disk state stays consistent
    too, and it can be promoted to leader later using its own AOF.
    """

    def __init__(self, apply_fn):
        # apply_fn(op: str, key: str, value: Optional[str], ttl: Optional[float]) -> None
        self._apply_fn = apply_fn

    async def handle_leader_stream(self, reader: asyncio.StreamReader) -> None:
        buffer = b""
        while True:
            chunk = await reader.read(4096)
            if not chunk:
                logger.warning("replication: leader stream closed")
                return
            buffer += chunk
            while True:
                try:
                    result = parse_resp(buffer)
                except ProtocolError as e:
                    logger.error(f"replication: malformed command from leader: {e}")
                    return
                if result.command is None:
                    break
                buffer = buffer[result.bytes_consumed:]
                await self._apply(result.command)

    async def _apply(self, command: list[str]) -> None:
        if not command:
            return
        op = command[0].upper()
        key = command[1] if len(command) > 1 else None
        value = command[2] if len(command) > 2 else None
        ttl = float(command[3]) if len(command) > 3 else None
        if key is None:
            return
        self._apply_fn(op, key, value, ttl)
