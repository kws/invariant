"""Tests for MemoryStore."""

import math
from decimal import Decimal

import pytest

from cachetools import LRUCache

from invariant.hashing import hash_value
from invariant.store.memory import MemoryStore


class TestMemoryStore:
    """Tests for MemoryStore."""

    def test_creation(self):
        """Test MemoryStore creation."""
        store = MemoryStore(cache="unbounded")
        assert store is not None

    def test_exists_false(self):
        """Test exists returns False for non-existent artifact."""
        store = MemoryStore(cache="unbounded")
        op_name = "test:op"
        assert not store.exists(op_name, "nonexistent" * 8)  # 64 char digest

    def test_put_and_get(self):
        """Test storing and retrieving an artifact."""
        store = MemoryStore(cache="unbounded")
        op_name = "test:op"
        artifact = "test"
        digest = hash_value(artifact)

        store.put(op_name, digest, artifact)
        assert store.exists(op_name, digest)

        retrieved = store.get(op_name, digest)
        assert isinstance(retrieved, str)
        assert retrieved == "test"

    def test_get_nonexistent(self):
        """Test that getting non-existent artifact raises KeyError."""
        store = MemoryStore(cache="unbounded")
        op_name = "test:op"
        with pytest.raises(KeyError):
            store.get(op_name, "nonexistent" * 8)

    def test_put_and_get_integer(self):
        """Test storing and retrieving integer."""
        store = MemoryStore(cache="unbounded")
        op_name = "test:op"
        artifact = 42
        digest = hash_value(artifact)

        store.put(op_name, digest, artifact)
        retrieved = store.get(op_name, digest)
        assert isinstance(retrieved, int)
        assert retrieved == 42

    def test_put_and_get_decimal(self):
        """Test storing and retrieving Decimal."""
        store = MemoryStore(cache="unbounded")
        op_name = "test:op"
        artifact = Decimal("3.14159")
        digest = hash_value(artifact)

        store.put(op_name, digest, artifact)
        retrieved = store.get(op_name, digest)
        assert isinstance(retrieved, Decimal)
        assert retrieved == artifact

    def test_put_get_roundtrip(self):
        """Test that put/get preserves data."""
        store = MemoryStore(cache="unbounded")
        op_name = "test:op"
        original = "hello world"
        digest = hash_value(original)

        store.put(op_name, digest, original)
        retrieved = store.get(op_name, digest)

        assert retrieved == original
        assert hash_value(retrieved) == hash_value(original)

    def test_clear(self):
        """Test clear method."""
        store = MemoryStore(cache="unbounded")
        op_name = "test:op"
        artifact = "test"
        digest = hash_value(artifact)

        store.put(op_name, digest, artifact)
        assert store.exists(op_name, digest)

        store.clear()
        assert not store.exists(op_name, digest)

    def test_multiple_artifacts(self):
        """Test storing multiple artifacts."""
        store = MemoryStore(cache="unbounded")
        op_name = "test:op"
        a1 = "hello"
        a2 = 42
        d1 = hash_value(a1)
        d2 = hash_value(a2)

        store.put(op_name, d1, a1)
        store.put(op_name, d2, a2)

        assert store.exists(op_name, d1)
        assert store.exists(op_name, d2)
        assert store.get(op_name, d1) == "hello"
        assert store.get(op_name, d2) == 42

    def test_lru_eviction(self):
        """Test LRU eviction when max_size exceeded."""
        store = MemoryStore(cache="lru", max_size=2)
        op_name = "test:op"
        d1, d2, d3 = hash_value("a"), hash_value("b"), hash_value("c")
        store.put(op_name, d1, "a")
        store.put(op_name, d2, "b")
        store.put(op_name, d3, "c")
        assert not store.exists(op_name, d1)
        assert store.exists(op_name, d2)
        assert store.exists(op_name, d3)

    def test_lru_access_order(self):
        """Test that get() updates LRU order (touched item not evicted)."""
        store = MemoryStore(cache="lru", max_size=2)
        op_name = "test:op"
        d1, d2, d3 = hash_value("a"), hash_value("b"), hash_value("c")
        store.put(op_name, d1, "a")
        store.put(op_name, d2, "b")
        store.get(op_name, d1)  # touch a
        store.put(op_name, d3, "c")
        assert store.exists(op_name, d1)
        assert not store.exists(op_name, d2)
        assert store.exists(op_name, d3)

    def test_lfu_eviction(self):
        """Test LFU eviction: least frequently used is evicted."""
        store = MemoryStore(cache="lfu", max_size=2)
        op_name = "test:op"
        d1, d2, d3 = hash_value("a"), hash_value("b"), hash_value("c")
        store.put(op_name, d1, "a")
        store.put(op_name, d2, "b")
        store.get(op_name, d1)
        store.get(op_name, d1)  # a has count 2, b has count 1
        store.put(op_name, d3, "c")
        assert store.exists(op_name, d1)
        assert not store.exists(op_name, d2)
        assert store.exists(op_name, d3)

    def test_max_size_zero_raises(self):
        """Test max_size=0 raises ValueError."""
        with pytest.raises(ValueError, match="max_size must be at least 1"):
            MemoryStore(cache="lru", max_size=0)

    def test_max_size_inf_raises(self):
        """Test max_size=inf raises ValueError."""
        with pytest.raises(ValueError, match="cannot be infinity"):
            MemoryStore(cache="lru", max_size=math.inf)

    def test_cache_lfu_default_max_size(self):
        """Test cache='lfu' without max_size uses default 1000."""
        store = MemoryStore(cache="lfu")
        assert store is not None

    def test_cache_instance_forbids_max_size(self):
        """Test cache instance with max_size raises ValueError."""
        with pytest.raises(ValueError, match="max_size must not be set"):
            MemoryStore(cache=LRUCache(maxsize=10), max_size=5)

    def test_clear_bounded(self):
        """Test clear with bounded cache."""
        store = MemoryStore(cache="lru", max_size=10)
        op_name = "test:op"
        digest = hash_value("x")
        store.put(op_name, digest, "x")
        store.clear()
        assert not store.exists(op_name, digest)

    def test_cache_instance(self):
        """Test injecting a cache instance."""
        store = MemoryStore(cache=LRUCache(maxsize=2))
        op_name = "test:op"
        d1, d2, d3 = hash_value("a"), hash_value("b"), hash_value("c")
        store.put(op_name, d1, "a")
        store.put(op_name, d2, "b")
        store.put(op_name, d3, "c")
        assert not store.exists(op_name, d1)
        assert store.exists(op_name, d2)
        assert store.exists(op_name, d3)
