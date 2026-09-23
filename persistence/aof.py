"""
Append-only file (AOF) persistence.

Every mutating command (SET, DEL, EXPIRE) is appended to a log file as
one JSON line *before* being acknowledged to the client. On startup,
the log is replayed in order to rebuild in-memory state. This trades
some write latency (a disk append per write) for durability against
process crashes.

Known limitation (worth stating in an interview, not hiding): this is
a *synchronous* fsync-per-write AOF, which is safe but not the fastest
option. Real systems (e.g. Redis) offer configurable fsync policies
(always / every second / never) to trade durability for throughput --
that's a natural "what would you improve" follow-up.
"""
from __future__ import annotations
import json
import os
import threading
import time
from typing import Any, Callable, Optional


class AOFWriter:
    def __init__(self, log_path: str):
        self._log_path = log_path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(os.path.abspath(log_path)) or ".", exist_ok=True)
        self._file = open(self._log_path, "a", buffering=1)  # line-buffered

    def append(self, op: str, key: str, value: Any = None, ttl_seconds: Optional[float] = None) -> None:
        record = {
            "ts": time.time(),
            "op": op,             # "SET" | "DEL" | "EXPIRE"
            "key": key,
            "value": value,
            "ttl": ttl_seconds,
        }
        line = json.dumps(record)
        with self._lock:
            self._file.write(line + "\n")
            self._file.flush()
            os.fsync(self._file.fileno())

    def close(self) -> None:
        with self._lock:
            self._file.close()


def replay(log_path: str, apply_fn: Callable[[str, str, Any, Optional[float]], None]) -> int:
    """
    Read the AOF line by line and call apply_fn(op, key, value, ttl)
    for each record, in order. Returns the number of records replayed.
    Missing file is not an error (fresh start).
    """
    if not os.path.exists(log_path):
        return 0

    count = 0
    with open(log_path, "r") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                # A truncated last line (e.g. crash mid-write) is skipped,
                # not fatal -- this is a deliberate, documented trade-off.
                print(f"[AOF] skipping corrupt line {line_no}")
                continue
            apply_fn(record["op"], record["key"], record.get("value"), record.get("ttl"))
            count += 1
    return count
