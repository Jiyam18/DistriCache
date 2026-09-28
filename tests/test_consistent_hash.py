"""Tests for the ConsistentHashRing implementation in core/consistent_hash.py."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'DistriCache-progress'))

from core.consistent_hash import ConsistentHashRing


def test_consistent_hash_ring_creation():
    """Test that ConsistentHashRing creates with default parameters."""
    ring = ConsistentHashRing()
    assert len(ring) == 0
    assert ring.nodes == []


def test_add_node():
    """Test adding a node to the ring."""
    ring = ConsistentHashRing()
    ring.add_node("node1")
    assert "node1" in ring.nodes
    assert len(ring) == 1


def test_add_multiple_nodes():
    """Test adding multiple nodes."""
    ring = ConsistentHashRing()
    ring.add_node("node1")
    ring.add_node("node2")
    ring.add_node("node3")

    assert len(ring) == 3
    assert "node1" in ring.nodes
    assert "node2" in ring.nodes
    assert "node3" in ring.nodes


def test_remove_node():
    """Test removing a node from the ring."""
    ring = ConsistentHashRing()
    ring.add_node("node1")
    ring.add_node("node2")
    ring.remove_node("node1")

    assert "node1" not in ring.nodes
    assert "node2" in ring.nodes
    assert len(ring) == 1


def test_get_node():
    """Test getting the node responsible for a key."""
    ring = ConsistentHashRing()
    ring.add_node("node1")
    ring.add_node("node2")

    result = ring.get_node("some_key")

    assert result in ("node1", "node2")


def test_get_preference_list():
    """Test getting the preference list for a key."""
    ring = ConsistentHashRing()
    ring.add_node("node1")
    ring.add_node("node2")

    prefs = ring.get_preference_list("some_key", n=2)

    assert isinstance(prefs, list)
    assert len(prefs) <= 2

    for node in ("node1", "node2"):
        assert node in prefs


def test_nodes_property():
    """Test the nodes property returns a sorted list."""
    ring = ConsistentHashRing()
    ring.add_node("node1")
    ring.add_node("node2")

    nodes = ring.nodes

    assert isinstance(nodes, list)
    assert nodes == sorted(nodes)


def test_length_property():
    """Test the length property returns the number of nodes."""
    ring = ConsistentHashRing()
    ring.add_node("node1")
    ring.add_node("node2")

    assert ring.__len__() == 2


def test_empty_ring():
    """Test behavior of an empty ring."""
    ring = ConsistentHashRing()

    assert ring.get_node("any_key") is None
    assert ring.get_preference_list("any_key", n=1) == []