"""Tests for MemoryStore."""

import pytest

from invariant.store.memory import MemoryStore
from invariant.types import DecimalValue, Integer, String


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
        artifact = String("test")
        digest = artifact.get_stable_hash()

        store.put(op_name, digest, artifact)
        assert store.exists(op_name, digest)

        retrieved = store.get(op_name, digest)
        assert isinstance(retrieved, String)
        assert retrieved.value == "test"

    def test_get_nonexistent(self):
        """Test that getting non-existent artifact raises KeyError."""
        store = MemoryStore()
        op_name = "test:op"
        with pytest.raises(KeyError):
            store.get(op_name, "nonexistent" * 8)

    def test_put_and_get_integer(self):
        """Test storing and retrieving Integer."""
        store = MemoryStore()
        op_name = "test:op"
        artifact = Integer(42)
        digest = artifact.get_stable_hash()

        store.put(op_name, digest, artifact)
        retrieved = store.get(op_name, digest)
        assert isinstance(retrieved, Integer)
        assert retrieved.value == 42

    def test_put_and_get_decimal(self):
        """Test storing and retrieving DecimalValue."""
        store = MemoryStore()
        op_name = "test:op"
        artifact = DecimalValue("3.14159")
        digest = artifact.get_stable_hash()

        store.put(op_name, digest, artifact)
        retrieved = store.get(op_name, digest)
        assert isinstance(retrieved, DecimalValue)
        assert retrieved.value == artifact.value

    def test_serialization_roundtrip(self):
        """Test that serialization preserves data."""
        store = MemoryStore()
        op_name = "test:op"
        original = String("hello world")
        digest = original.get_stable_hash()

        store.put(op_name, digest, original)
        retrieved = store.get(op_name, digest)

        assert retrieved.value == original.value
        assert retrieved.get_stable_hash() == original.get_stable_hash()

    def test_clear(self):
        """Test clear method."""
        store = MemoryStore()
        op_name = "test:op"
        artifact = String("test")
        digest = artifact.get_stable_hash()

        store.put(op_name, digest, artifact)
        assert store.exists(op_name, digest)

        store.clear()
        assert not store.exists(op_name, digest)

    def test_multiple_artifacts(self):
        """Test storing multiple artifacts."""
        store = MemoryStore()
        op_name = "test:op"
        a1 = String("hello")
        a2 = Integer(42)
        d1 = a1.get_stable_hash()
        d2 = a2.get_stable_hash()

        store.put(op_name, d1, a1)
        store.put(op_name, d2, a2)

        assert store.exists(op_name, d1)
        assert store.exists(op_name, d2)
        assert store.get(op_name, d1).value == "hello"
        assert store.get(op_name, d2).value == 42
