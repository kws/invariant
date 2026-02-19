"""Tests for ChainStore."""

import tempfile
from pathlib import Path

import pytest

from invariant.store.chain import ChainStore
from invariant.store.disk import DiskStore
from invariant.store.memory import MemoryStore
from invariant.types import DecimalValue, Integer, String


class TestChainStore:
    """Tests for ChainStore."""

    def test_creation_defaults(self):
        """Test ChainStore creation with default stores."""
        store = ChainStore()
        assert isinstance(store.l1, MemoryStore)
        assert isinstance(store.l2, DiskStore)

    def test_creation_custom(self):
        """Test ChainStore creation with custom stores."""
        l1 = MemoryStore()
        with tempfile.TemporaryDirectory() as tmpdir:
            l2 = DiskStore(cache_dir=Path(tmpdir))
            store = ChainStore(l1=l1, l2=l2)
            assert store.l1 is l1
            assert store.l2 is l2

    def test_exists_l1_hit(self):
        """Test exists returns True when artifact is in L1."""
        store = ChainStore()
        artifact = String("test")
        digest = artifact.get_stable_hash()

        store.l1.put(digest, artifact)
        assert store.exists(digest)

    def test_exists_l2_hit(self):
        """Test exists returns True when artifact is in L2 but not L1."""
        store = ChainStore()
        artifact = String("test")
        digest = artifact.get_stable_hash()

        store.l2.put(digest, artifact)
        assert store.exists(digest)

    def test_exists_miss(self):
        """Test exists returns False when artifact is in neither store."""
        store = ChainStore()
        assert not store.exists("nonexistent" * 8)

    def test_get_l1_hit(self):
        """Test get retrieves from L1 when present."""
        store = ChainStore()
        artifact = String("test")
        digest = artifact.get_stable_hash()

        store.l1.put(digest, artifact)
        retrieved = store.get(digest)

        assert isinstance(retrieved, String)
        assert retrieved.value == "test"
        # Verify it's still in L1 (not removed)
        assert store.l1.exists(digest)

    def test_get_l2_hit_promotes(self):
        """Test get retrieves from L2 and promotes to L1."""
        store = ChainStore()
        artifact = String("test")
        digest = artifact.get_stable_hash()

        # Put only in L2
        store.l2.put(digest, artifact)
        assert not store.l1.exists(digest)
        assert store.l2.exists(digest)

        # Get should promote to L1
        retrieved = store.get(digest)

        assert isinstance(retrieved, String)
        assert retrieved.value == "test"
        # Verify it's now in L1 (promoted)
        assert store.l1.exists(digest)
        # Verify it's still in L2
        assert store.l2.exists(digest)

    def test_get_miss(self):
        """Test that getting non-existent artifact raises KeyError."""
        store = ChainStore()
        with pytest.raises(KeyError):
            store.get("nonexistent" * 8)

    def test_put_writes_both(self):
        """Test put writes to both L1 and L2."""
        store = ChainStore()
        artifact = String("test")
        digest = artifact.get_stable_hash()

        store.put(digest, artifact)

        assert store.l1.exists(digest)
        assert store.l2.exists(digest)

        # Verify we can retrieve from both
        l1_retrieved = store.l1.get(digest)
        l2_retrieved = store.l2.get(digest)

        assert l1_retrieved.value == "test"
        assert l2_retrieved.value == "test"

    def test_serialization_roundtrip(self):
        """Test that serialization preserves data through chain."""
        store = ChainStore()
        original = String("hello world")
        digest = original.get_stable_hash()

        store.put(digest, original)
        retrieved = store.get(digest)

        assert retrieved.value == original.value
        assert retrieved.get_stable_hash() == original.get_stable_hash()

    def test_multiple_artifacts(self):
        """Test storing multiple artifacts."""
        store = ChainStore()
        a1 = String("hello")
        a2 = Integer(42)
        d1 = a1.get_stable_hash()
        d2 = a2.get_stable_hash()

        store.put(d1, a1)
        store.put(d2, a2)

        assert store.exists(d1)
        assert store.exists(d2)
        assert store.get(d1).value == "hello"
        assert store.get(d2).value == 42

    def test_decimal_value(self):
        """Test storing and retrieving DecimalValue."""
        store = ChainStore()
        artifact = DecimalValue("3.14159")
        digest = artifact.get_stable_hash()

        store.put(digest, artifact)
        retrieved = store.get(digest)

        assert isinstance(retrieved, DecimalValue)
        assert retrieved.value == artifact.value

    def test_l2_promotion_preserves_data(self):
        """Test that promotion from L2 to L1 preserves artifact data."""
        store = ChainStore()
        artifact = String("promote me")
        digest = artifact.get_stable_hash()

        # Put only in L2
        store.l2.put(digest, artifact)

        # First get promotes to L1
        first = store.get(digest)
        assert first.value == "promote me"

        # Second get should come from L1 (faster)
        second = store.get(digest)
        assert second.value == "promote me"
        assert first.get_stable_hash() == second.get_stable_hash()
