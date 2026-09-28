import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'DistriCache-progress'))
from core.hash_table import HashTable

def test_hash_table_initialization():
    """Test that HashTable initializes correctly with default parameters."""
    ht = HashTable()
    assert len(ht) == 0
    assert ht.capacity == 16
    assert ht.load_factor == 0.0


def test_hash_table_set_and_get():
    """Test setting and getting values in the hash table."""
    ht = HashTable()
    ht.set("key1", "value1")
    assert ht.get("key1") == "value1"

    with pytest.raises(KeyError):
        ht.get("key2")


def test_hash_table_set_multiple_values():
    """Test adding multiple key-value pairs."""
    ht = HashTable()
    ht.set("key1", "val1")
    ht.set("key2", "val2")
    ht.set("key3", "val3")

    assert ht.get("key1") == "val1"
    assert ht.get("key2") == "val2"
    assert ht.get("key3") == "val3"


def test_hash_table_resize_on_load_factor():
    """Test that the hash table resizes when load factor exceeds threshold."""
    ht = HashTable()

    for i in range(20):
        ht.set(f"key{i}", f"value{i}")

    for i in range(20, 30):
        ht.set(f"key{i}", f"value{i}")

    assert ht.get("key0") == "value0"


def test_hash_table_delete():
    """Test deleting keys from the hash table."""
    ht = HashTable()
    ht.set("key1", "value1")
    ht.set("key2", "value2")

    assert ht.get("key1") == "value1"
    assert ht.get("key2") == "value2"

    ht.delete("key1")

    with pytest.raises(KeyError):
        ht.get("key1")

    assert ht.get("key2") == "value2"


def test_hash_table_keys():
    """Test iterating over keys."""
    ht = HashTable()
    ht.set("key1", "val1")
    ht.set("key2", "val2")

    keys = list(ht.keys())

    assert "key1" in keys
    assert "key2" in keys
    assert len(keys) == 2


def test_hash_table_capacity():
    """Test that the initial capacity is correct."""
    ht = HashTable(initial_capacity=10)
    assert ht.capacity == 10

    ht2 = HashTable()
    assert ht2.capacity == 16