"""
LRU (Least Recently Used) cache: O(1) get and put via a hash map
(key -> node pointer) combined with a doubly linked list that tracks
recency order. Most-recently-used sits at the head; least-recently-used
sits at the tail and is what gets evicted when capacity is exceeded.

This also layers in per-key TTL (time-to-live) expiry, checked lazily
on access.
"""
from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Any, Optional


class _Node:
    __slots__ = ("key", "value", "expires_at", "prev", "next")

    def __init__(self, key: str, value: Any, expires_at: Optional[float]):
        self.key = key
        self.value = value
        self.expires_at = expires_at  # unix timestamp or None
        self.prev: "Optional[_Node]" = None
        self.next: "Optional[_Node]" = None


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


class LRUCache:
    """
    Doubly linked list + dict of key->node gives O(1):
      - get: look up node in dict, move it to head
      - put: if exists, update + move to head; else create node at head,
             evict tail if over capacity
    """

    def __init__(self, capacity: int = 10_000):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._map: dict[str, _Node] = {}
        # Sentinel head/tail nodes simplify edge cases (empty list, single node)
        self._head = _Node("__head__", None, None)
        self._tail = _Node("__tail__", None, None)
        self._head.next = self._tail
        self._tail.prev = self._head
        self.stats = CacheStats()

    # -- internal linked-list helpers -----------------------------------

    def _remove_node(self, node: _Node) -> None:
        node.prev.next = node.next
        node.next.prev = node.prev

    def _insert_at_head(self, node: _Node) -> None:
        node.next = self._head.next
        node.prev = self._head
        self._head.next.prev = node
        self._head.next = node

    def _move_to_head(self, node: _Node) -> None:
        self._remove_node(node)
        self._insert_at_head(node)

    def _evict_tail(self) -> None:
        lru_node = self._tail.prev
        if lru_node is self._head:
            return  # empty
        self._remove_node(lru_node)
        del self._map[lru_node.key]
        self.stats.evictions += 1

    def _is_expired(self, node: _Node) -> bool:
        return node.expires_at is not None and node.expires_at <= time.time()

    # -- public API -------------------------------------------------------

    def get(self, key: str) -> Any:
        node = self._map.get(key)
        if node is None:
            self.stats.misses += 1
            raise KeyError(key)
        if self._is_expired(node):
            self._remove_node(node)
            del self._map[key]
            self.stats.expirations += 1
            self.stats.misses += 1
            raise KeyError(key)
        self._move_to_head(node)
        self.stats.hits += 1
        return node.value

    def get_or_default(self, key: str, default: Any = None) -> Any:
        try:
            return self.get(key)
        except KeyError:
            return default

    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        expires_at = time.time() + ttl_seconds if ttl_seconds is not None else None
        existing = self._map.get(key)
        if existing is not None:
            existing.value = value
            existing.expires_at = expires_at
            self._move_to_head(existing)
            return

        node = _Node(key, value, expires_at)
        self._map[key] = node
        self._insert_at_head(node)

        if len(self._map) > self._capacity:
            self._evict_tail()

    def delete(self, key: str) -> bool:
        node = self._map.get(key)
        if node is None:
            return False
        self._remove_node(node)
        del self._map[key]
        return True

    def expire(self, key: str, ttl_seconds: float) -> bool:
        """Set/update TTL on an existing key without changing its value."""
        node = self._map.get(key)
        if node is None or self._is_expired(node):
            return False
        node.expires_at = time.time() + ttl_seconds
        return True

    def ttl(self, key: str) -> Optional[float]:
        """Seconds remaining, None if no TTL, raises KeyError if missing/expired."""
        node = self._map.get(key)
        if node is None or self._is_expired(node):
            raise KeyError(key)
        if node.expires_at is None:
            return None
        return max(0.0, node.expires_at - time.time())

    def __len__(self) -> int:
        return len(self._map)

    def __contains__(self, key: str) -> bool:
        node = self._map.get(key)
        return node is not None and not self._is_expired(node)

    @property
    def capacity(self) -> int:
        return self._capacity
