"""Tests for the Store implementation in core/store.py."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'DistriCache-progress'))

from core.store import Store


def test_store_initialization():
    """Test that Store initializes correctly."""
    store = Store()
    assert len(store) == 0


def test_store_get():
    """Test getting a value from the store."""
    store = Store()
    store.set("key1", "value1")

    assert store.get("key1") == "value1"


def test_store_set():
    """Test setting a value in the store."""
    store = Store()
    store.set("key1", "value1")

    assert store.get("key1") == "value1"


def test_store_delete():
    """Test deleting a value from the store."""
    store = Store()
    store.set("key1", "value1")

    assert store.delete("key1") is True

    with pytest.raises(Exception):
        store.get("key1")


def test_store_exists():
    """Test checking if a key exists."""
    store = Store()

    assert store.exists("key1") is False

    store.set("key1", "value1")

    assert store.exists("key1") is True


def test_store_keys():
    """Test listing keys in the store."""
    store = Store()
    store.set("key1", "value1")
    store.set("key2", "value2")

    keys = store.keys()

    assert "key1" in keys
    assert "key2" in keys
    assert len(keys) == 2


def test_store_stats():
    """Test storing statistics from the store."""
    store = Store()
    store.set("key1", "value1")
    store.set("key2", "value2")

    stats = store.stats()

    assert stats["size"] == 2
    assert stats["capacity"] == 10_000
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["hit_rate"] == 0.0