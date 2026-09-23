"""
Custom hash table implementation with separate chaining for collision handling.

Why not just use Python's dict?
This project is meant to demonstrate understanding of hash table internals:
bucket arrays, hash functions, load factor, and dynamic resizing (rehashing).
A raw dict would hide all of that.
"""
from __future__ import annotations
from typing import Any, Iterator, Optional


class _Entry:
    __slots__ = ("key", "value", "next")

    def __init__(self, key: str, value: Any, next_entry: "Optional[_Entry]" = None):
        self.key = key
        self.value = value
        self.next = next_entry


class HashTable:
    """
    A hash table using separate chaining (linked lists per bucket) for
    collision resolution, with automatic resizing when the load factor
    exceeds a threshold.

    Average case: O(1) get/set/delete.
    Worst case (many collisions): O(n) for a single bucket's chain.
    """

    INITIAL_CAPACITY = 16
    LOAD_FACTOR_THRESHOLD = 0.75
    GROWTH_FACTOR = 2

    def __init__(self, initial_capacity: int = INITIAL_CAPACITY):
        self._capacity = max(initial_capacity, 4)
        self._buckets: list[Optional[_Entry]] = [None] * self._capacity
        self._size = 0

    def _hash(self, key: str) -> int:
        """Map a string key to a bucket index."""
        return hash(key) % self._capacity

    def _load_factor(self) -> float:
        return self._size / self._capacity

    def _resize(self) -> None:
        """Double capacity and rehash every existing entry into new buckets."""
        old_buckets = self._buckets
        self._capacity *= self.GROWTH_FACTOR
        self._buckets = [None] * self._capacity
        old_size = self._size
        self._size = 0

        for head in old_buckets:
            entry = head
            while entry is not None:
                self._set_internal(entry.key, entry.value)
                entry = entry.next

        assert self._size == old_size, "rehash must preserve size"

    def _set_internal(self, key: str, value: Any) -> None:
        """Set without triggering a resize check (used during rehashing)."""
        idx = self._hash(key)
        entry = self._buckets[idx]
        while entry is not None:
            if entry.key == key:
                entry.value = value
                return
            entry = entry.next
        self._buckets[idx] = _Entry(key, value, self._buckets[idx])
        self._size += 1

    def set(self, key: str, value: Any) -> None:
        self._set_internal(key, value)
        if self._load_factor() > self.LOAD_FACTOR_THRESHOLD:
            self._resize()

    def get(self, key: str) -> Any:
        idx = self._hash(key)
        entry = self._buckets[idx]
        while entry is not None:
            if entry.key == key:
                return entry.value
            entry = entry.next
        raise KeyError(key)

    def get_or_default(self, key: str, default: Any = None) -> Any:
        try:
            return self.get(key)
        except KeyError:
            return default

    def contains(self, key: str) -> bool:
        idx = self._hash(key)
        entry = self._buckets[idx]
        while entry is not None:
            if entry.key == key:
                return True
            entry = entry.next
        return False

    def delete(self, key: str) -> bool:
        idx = self._hash(key)
        entry = self._buckets[idx]
        prev: Optional[_Entry] = None
        while entry is not None:
            if entry.key == key:
                if prev is None:
                    self._buckets[idx] = entry.next
                else:
                    prev.next = entry.next
                self._size -= 1
                return True
            prev = entry
            entry = entry.next
        return False

    def keys(self) -> Iterator[str]:
        for head in self._buckets:
            entry = head
            while entry is not None:
                yield entry.key
                entry = entry.next

    def __len__(self) -> int:
        return self._size

    def __contains__(self, key: str) -> bool:
        return self.contains(key)

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def load_factor(self) -> float:
        return self._load_factor()
