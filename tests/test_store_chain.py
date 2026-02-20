"""Tests for ChainStore."""

import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from invariant.hashing import hash_value
from invariant.store.chain import ChainStore
from invariant.store.disk import DiskStore
from invariant.store.memory import MemoryStore


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
        op_name = "test:op"
        artifact = "test"
        digest = hash_value(artifact)

        store.l1.put(op_name, digest, artifact)
        assert store.exists(op_name, digest)

    def test_exists_l2_hit(self):
        """Test exists returns True when artifact is in L2 but not L1."""
        store = ChainStore()
        op_name = "test:op"
        artifact = "test"
        digest = hash_value(artifact)

        store.l2.put(op_name, digest, artifact)
        assert store.exists(op_name, digest)

    def test_exists_miss(self):
        """Test exists returns False when artifact is in neither store."""
        store = ChainStore()
        op_name = "test:op"
        # Use a valid 64-character hex digest
        digest = "0" * 64
        assert not store.exists(op_name, digest)

    def test_get_l1_hit(self):
        """Test get retrieves from L1 when present."""
        store = ChainStore()
        op_name = "test:op"
        artifact = "test"
        digest = hash_value(artifact)

        store.l1.put(op_name, digest, artifact)
        retrieved = store.get(op_name, digest)

        assert isinstance(retrieved, str)
        assert retrieved == "test"
        # Verify it's still in L1 (not removed)
        assert store.l1.exists(op_name, digest)

    def test_get_l2_hit_promotes(self):
        """Test get retrieves from L2 and promotes to L1."""
        store = ChainStore()
        op_name = "test:op"
        artifact = "test"
        digest = hash_value(artifact)

        # Put only in L2
        store.l2.put(op_name, digest, artifact)
        assert not store.l1.exists(op_name, digest)
        assert store.l2.exists(op_name, digest)

        # Get should promote to L1
        retrieved = store.get(op_name, digest)

        assert isinstance(retrieved, str)
        assert retrieved == "test"
        # Verify it's now in L1 (promoted)
        assert store.l1.exists(op_name, digest)
        # Verify it's still in L2
        assert store.l2.exists(op_name, digest)

    def test_get_miss(self):
        """Test that getting non-existent artifact raises KeyError."""
        store = ChainStore()
        op_name = "test:op"
        # Use a valid 64-character hex digest
        digest = "0" * 64
        with pytest.raises(KeyError):
            store.get(op_name, digest)

    def test_put_writes_both(self):
        """Test put writes to both L1 and L2."""
        store = ChainStore()
        op_name = "test:op"
        artifact = "test"
        digest = hash_value(artifact)

        store.put(op_name, digest, artifact)

        assert store.l1.exists(op_name, digest)
        assert store.l2.exists(op_name, digest)

        # Verify we can retrieve from both
        l1_retrieved = store.l1.get(op_name, digest)
        l2_retrieved = store.l2.get(op_name, digest)

        assert l1_retrieved == "test"
        assert l2_retrieved == "test"

    def test_serialization_roundtrip(self):
        """Test that serialization preserves data through chain."""
        store = ChainStore()
        op_name = "test:op"
        original = "hello world"
        digest = hash_value(original)

        store.put(op_name, digest, original)
        retrieved = store.get(op_name, digest)

        assert retrieved == original
        assert hash_value(retrieved) == hash_value(original)

    def test_multiple_artifacts(self):
        """Test storing multiple artifacts."""
        store = ChainStore()
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

    def test_decimal_value(self):
        """Test storing and retrieving Decimal."""
        store = ChainStore()
        op_name = "test:op"
        artifact = Decimal("3.14159")
        digest = hash_value(artifact)

        store.put(op_name, digest, artifact)
        retrieved = store.get(op_name, digest)

        assert isinstance(retrieved, Decimal)
        assert retrieved == artifact

    def test_l2_promotion_preserves_data(self):
        """Test that promotion from L2 to L1 preserves artifact data."""
        store = ChainStore()
        op_name = "test:op"
        artifact = "promote me"
        digest = hash_value(artifact)

        # Put only in L2
        store.l2.put(op_name, digest, artifact)

        # First get promotes to L1
        first = store.get(op_name, digest)
        assert first == "promote me"

        # Second get should come from L1 (faster)
        second = store.get(op_name, digest)
        assert second == "promote me"
        assert hash_value(first) == hash_value(second)
