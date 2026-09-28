"""Tests for the LRUCache implementation in core/lru_cache.py."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'DistriCache-progress'))

from core.lru_cache import LRUCache


def test_lru_cache_initialization():
    """Test that LRUCache initializes correctly with default capacity."""
    lru = LRUCache()
    assert len(lru) == 0
    assert lru.capacity == 10_000


def test_lru_cache_set_and_get():
    """Test setting and getting values in the LRU cache."""
    lru = LRUCache()
    lru.set("key1", "value1")
    lru.set("key2", "value2")

    assert lru.get("key1") == "value1"
    assert lru.get("key2") == "value2"


def test_lru_cache_get_missing_key():
    """Test that getting a missing key raises KeyError."""
    lru = LRUCache()

    with pytest.raises(KeyError):
        lru.get("nonexistent_key")


def test_lru_cache_put_existing_key_updates():
    """Test that updating an existing key moves it to the front."""
    lru_small = LRUCache(capacity=2)

    lru_small.set("key1", "value1")
    lru_small.set("key2", "value2")
    lru_small.get("key1")

    lru_small.set("key3", "value3")

    with pytest.raises(KeyError):
        lru_small.get("key2")


def test_lru_cache_put_with_ttl():
    """Test that LRUCache accepts TTL values."""
    lru = LRUCache()

    lru.set("key1", "value1", ttl_seconds=1.0)

    assert lru.get("key1") == "value1"


def test_lru_cache_stats():
    """Test that LRU cache statistics are tracked."""
    lru = LRUCache()

    lru.set("key1", "value1")
    lru.set("key2", "value2")
    lru.get("key1")
    lru.get("key2")

    stats = lru.stats

    assert stats.hits == 2
    assert stats.misses == 0
    assert stats.evictions == 0
    assert stats.expirations == 0


def test_lru_cache_delete():
    """Test deleting keys from the LRU cache."""
    lru = LRUCache()

    lru.set("key1", "value1")
    lru.set("key2", "value2")
    lru.delete("key1")

    with pytest.raises(KeyError):
        lru.get("key1")

    assert lru.get("key2") == "value2"


def test_lru_cache_evicts_oldest():
    """Test that LRU evicts the least recently used item."""
    lru = LRUCache(capacity=2)

    lru.set("key1", "value1")
    lru.set("key2", "value2")
    lru.get("key1")

    lru.set("key3", "value3")

    with pytest.raises(KeyError):
        lru.get("key2")

    assert lru.get("key1") == "value1"
    assert lru.get("key3") == "value3"