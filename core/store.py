"""
Store: the thread-safe storage engine used by the TCP/REST server.

Design note (worth understanding for interviews): this project has two
separate hash-table-style structures for a reason:
  - `HashTable` (hash_table.py) is a from-scratch demonstration of a
    hash table with explicit collision chaining and manual resizing --
    kept standalone and unit-tested to show the underlying mechanics.
  - `LRUCache` (lru_cache.py) is the one actually used for storage here,
    because it needs O(1) *reordering* on every access (move-to-head),
    which requires node pointers a plain hash table doesn't give you.
    It uses Python's dict for the key->node index (dict is itself a
    hash table) combined with an explicit doubly linked list for
    recency order -- that combination is the actual LRU algorithm.
Both are real, defensible pieces; they solve different problems.
"""
from __future__ import annotations
import sys
import threading
from typing import Any, Optional

from core.lru_cache import LRUCache, CacheStats


class KeyNotFound(Exception):
    pass


class Store:
    def __init__(self, capacity: int = 10_000):
        self._cache = LRUCache(capacity=capacity)
        self._lock = threading.RLock()

    def get(self, key: str) -> Any:
        with self._lock:
            try:
                return self._cache.get(key)
            except KeyError:
                raise KeyNotFound(key)

    def set(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        with self._lock:
            self._cache.set(key, value, ttl_seconds=ttl_seconds)

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._cache.delete(key)

    def expire(self, key: str, ttl_seconds: float) -> bool:
        with self._lock:
            return self._cache.expire(key, ttl_seconds)

    def ttl(self, key: str) -> Optional[float]:
        with self._lock:
            try:
                return self._cache.ttl(key)
            except KeyError:
                raise KeyNotFound(key)

    def exists(self, key: str) -> bool:
        with self._lock:
            return key in self._cache

    def keys(self) -> list[str]:
        with self._lock:
            return list(self._cache._map.keys())

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

    def stats(self) -> dict:
        with self._lock:
            s: CacheStats = self._cache.stats
            approx_bytes = sum(
                sys.getsizeof(k) + sys.getsizeof(node.value)
                for k, node in self._cache._map.items()
            )
            return {
                "size": len(self._cache),
                "capacity": self._cache.capacity,
                "hits": s.hits,
                "misses": s.misses,
                "hit_rate": round(s.hit_rate, 4),
                "evictions": s.evictions,
                "expirations": s.expirations,
                "approx_memory_bytes": approx_bytes,
            }
