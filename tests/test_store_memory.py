"""Tests for MemoryStore."""

from decimal import Decimal

import pytest

from invariant.hashing import hash_value
from invariant.store.memory import MemoryStore


class TestMemoryStore:
    """Tests for MemoryStore."""

    def test_creation(self):
        """Test MemoryStore creation."""
        store = MemoryStore()
        assert store is not None

    def test_exists_false(self):
        """Test exists returns False for non-existent artifact."""
        store = MemoryStore()
        op_name = "test:op"
        assert not store.exists(op_name, "nonexistent" * 8)  # 64 char digest

    def test_put_and_get(self):
        """Test storing and retrieving an artifact."""
        store = MemoryStore()
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
        store = MemoryStore()
        op_name = "test:op"
        with pytest.raises(KeyError):
            store.get(op_name, "nonexistent" * 8)

    def test_put_and_get_integer(self):
        """Test storing and retrieving integer."""
        store = MemoryStore()
        op_name = "test:op"
        artifact = 42
        digest = hash_value(artifact)

        store.put(op_name, digest, artifact)
        retrieved = store.get(op_name, digest)
        assert isinstance(retrieved, int)
        assert retrieved == 42

    def test_put_and_get_decimal(self):
        """Test storing and retrieving Decimal."""
        store = MemoryStore()
        op_name = "test:op"
        artifact = Decimal("3.14159")
        digest = hash_value(artifact)

        store.put(op_name, digest, artifact)
        retrieved = store.get(op_name, digest)
        assert isinstance(retrieved, Decimal)
        assert retrieved == artifact

    def test_serialization_roundtrip(self):
        """Test that serialization preserves data."""
        store = MemoryStore()
        op_name = "test:op"
        original = "hello world"
        digest = hash_value(original)

        store.put(op_name, digest, original)
        retrieved = store.get(op_name, digest)

        assert retrieved == original
        assert hash_value(retrieved) == hash_value(original)

    def test_clear(self):
        """Test clear method."""
        store = MemoryStore()
        op_name = "test:op"
        artifact = "test"
        digest = hash_value(artifact)

        store.put(op_name, digest, artifact)
        assert store.exists(op_name, digest)

        store.clear()
        assert not store.exists(op_name, digest)

    def test_multiple_artifacts(self):
        """Test storing multiple artifacts."""
        store = MemoryStore()
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
