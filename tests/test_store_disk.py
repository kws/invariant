"""Tests for DiskStore."""

import shutil
from decimal import Decimal

import pytest

from invariant.hashing import hash_value
from invariant.store.disk import DiskStore


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory."""
    cache_dir = tmp_path / "test_cache"
    yield cache_dir
    # Cleanup
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)


class TestDiskStore:
    """Tests for DiskStore."""

    def test_creation_default(self):
        """Test DiskStore creation with default directory."""
        store = DiskStore()
        assert store.cache_dir.exists()
        assert store.cache_dir.name == "cache"

    def test_creation_custom_dir(self, temp_cache_dir):
        """Test DiskStore creation with custom directory."""
        store = DiskStore(temp_cache_dir)
        assert store.cache_dir == temp_cache_dir
        assert store.cache_dir.exists()

    def test_get_path(self, temp_cache_dir):
        """Test _get_path method."""
        store = DiskStore(temp_cache_dir)
        op_name = "test:op"
        digest = "a" * 64
        path = store._get_path(op_name, digest)
        assert "test_op" in str(path.parent)
        assert path.name == "a" * 62

    def test_get_path_invalid_digest(self, temp_cache_dir):
        """Test _get_path with invalid digest length."""
        store = DiskStore(temp_cache_dir)
        op_name = "test:op"
        with pytest.raises(ValueError, match="Invalid digest length"):
            store._get_path(op_name, "short")

    def test_exists_false(self, temp_cache_dir):
        """Test exists returns False for non-existent artifact."""
        store = DiskStore(temp_cache_dir)
        op_name = "test:op"
        assert not store.exists(op_name, "a" * 64)

    def test_put_and_get(self, temp_cache_dir):
        """Test storing and retrieving an artifact."""
        store = DiskStore(temp_cache_dir)
        op_name = "test:op"
        artifact = "test"
        digest = hash_value(artifact)

        store.put(op_name, digest, artifact)
        assert store.exists(op_name, digest)

        retrieved = store.get(op_name, digest)
        assert isinstance(retrieved, str)
        assert retrieved == "test"

    def test_get_nonexistent(self, temp_cache_dir):
        """Test that getting non-existent artifact raises KeyError."""
        store = DiskStore(temp_cache_dir)
        op_name = "test:op"
        with pytest.raises(KeyError):
            store.get(op_name, "a" * 64)

    def test_put_and_get_integer(self, temp_cache_dir):
        """Test storing and retrieving integer."""
        store = DiskStore(temp_cache_dir)
        op_name = "test:op"
        artifact = 42
        digest = hash_value(artifact)

        store.put(op_name, digest, artifact)
        retrieved = store.get(op_name, digest)
        assert isinstance(retrieved, int)
        assert retrieved == 42

    def test_put_and_get_decimal(self, temp_cache_dir):
        """Test storing and retrieving Decimal."""
        store = DiskStore(temp_cache_dir)
        op_name = "test:op"
        artifact = Decimal("3.14159")
        digest = hash_value(artifact)

        store.put(op_name, digest, artifact)
        retrieved = store.get(op_name, digest)
        assert isinstance(retrieved, Decimal)
        assert retrieved == artifact

    def test_persistence(self, temp_cache_dir):
        """Test that artifacts persist across store instances."""
        store1 = DiskStore(temp_cache_dir)
        op_name = "test:op"
        artifact = "persistent"
        digest = hash_value(artifact)

        store1.put(op_name, digest, artifact)

        # Create new store instance
        store2 = DiskStore(temp_cache_dir)
        assert store2.exists(op_name, digest)
        retrieved = store2.get(op_name, digest)
        assert retrieved == "persistent"

    def test_atomic_write(self, temp_cache_dir):
        """Test that writes are atomic (use temp file then rename)."""
        store = DiskStore(temp_cache_dir)
        op_name = "test:op"
        artifact = "atomic"
        digest = hash_value(artifact)

        # This should not leave a .tmp file
        store.put(op_name, digest, artifact)

        # Check no .tmp files exist
        tmp_files = list(temp_cache_dir.rglob("*.tmp"))
        assert len(tmp_files) == 0

    def test_directory_structure(self, temp_cache_dir):
        """Test that directory structure is created correctly."""
        store = DiskStore(temp_cache_dir)
        op_name = "test:op"
        artifact = "test"
        digest = hash_value(artifact)

        store.put(op_name, digest, artifact)

        # Check directory structure: {op_name}/{digest[:2]}/{digest[2:]}
        expected_dir = temp_cache_dir / "test_op" / digest[:2]
        assert expected_dir.exists()
        expected_file = expected_dir / digest[2:]
        assert expected_file.exists()
