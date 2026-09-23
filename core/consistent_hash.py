"""
Consistent hashing ring.

Why not `hash(key) % num_nodes`?
Because when a node is added or removed, nearly every key maps to a
different node (a full reshuffle) -- expensive and disruptive for a
live cache. Consistent hashing places both nodes and keys on a circular
hash space (0 .. 2^32-1). A key belongs to the first node clockwise
from its hash position. Adding/removing a node only affects the keys
between it and its neighbor on the ring -- a small, bounded fraction.

Virtual nodes: each physical node is hashed multiple times (with a
suffix like "node-1#0", "node-1#1", ...) and placed at multiple ring
positions. This spreads a node's keys more evenly and avoids hot spots
that a single ring position per node would create.
"""
from __future__ import annotations
import bisect
import hashlib
from typing import Optional


class ConsistentHashRing:
    def __init__(self, virtual_nodes_per_node: int = 150):
        self._vnodes = virtual_nodes_per_node
        # Sorted list of ring positions, and a parallel dict mapping
        # ring position -> physical node id. bisect gives O(log n) lookup.
        self._ring_positions: list[int] = []
        self._position_to_node: dict[int, str] = {}
        self._nodes: set[str] = set()

    @staticmethod
    def _hash(key: str) -> int:
        digest = hashlib.md5(key.encode("utf-8")).hexdigest()
        return int(digest, 16)

    def add_node(self, node_id: str) -> None:
        if node_id in self._nodes:
            return
        self._nodes.add(node_id)
        for i in range(self._vnodes):
            vkey = f"{node_id}#{i}"
            pos = self._hash(vkey)
            self._position_to_node[pos] = node_id
            bisect.insort(self._ring_positions, pos)

    def remove_node(self, node_id: str) -> None:
        if node_id not in self._nodes:
            return
        self._nodes.discard(node_id)
        for i in range(self._vnodes):
            vkey = f"{node_id}#{i}"
            pos = self._hash(vkey)
            del self._position_to_node[pos]
            idx = bisect.bisect_left(self._ring_positions, pos)
            if idx < len(self._ring_positions) and self._ring_positions[idx] == pos:
                self._ring_positions.pop(idx)

    def get_node(self, key: str) -> Optional[str]:
        """Return the node responsible for `key` (first node clockwise)."""
        if not self._ring_positions:
            return None
        pos = self._hash(key)
        idx = bisect.bisect_right(self._ring_positions, pos)
        if idx == len(self._ring_positions):
            idx = 0  # wrap around the ring
        ring_pos = self._ring_positions[idx]
        return self._position_to_node[ring_pos]

    def get_preference_list(self, key: str, n: int) -> list[str]:
        """
        Return up to n distinct physical nodes for `key`, walking
        clockwise from its ring position. Used for replication: the
        first entry is the leader, the rest are replica candidates.
        """
        if not self._ring_positions or n <= 0:
            return []
        pos = self._hash(key)
        idx = bisect.bisect_right(self._ring_positions, pos)
        result: list[str] = []
        seen: set[str] = set()
        total = len(self._ring_positions)
        for i in range(total):
            ring_pos = self._ring_positions[(idx + i) % total]
            node = self._position_to_node[ring_pos]
            if node not in seen:
                seen.add(node)
                result.append(node)
            if len(result) == n:
                break
        return result

    @property
    def nodes(self) -> list[str]:
        return sorted(self._nodes)

    def __len__(self) -> int:
        return len(self._nodes)
