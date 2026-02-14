"""Tests for DiskStore."""

import shutil

import pytest

from invariant.store.disk import DiskStore
from invariant.types import DecimalValue, Integer, String


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
        digest = "a" * 64
        path = store._get_path(digest)
        assert path.parent.name == "aa"
        assert path.name == "a" * 62

    def test_get_path_invalid_digest(self, temp_cache_dir):
        """Test _get_path with invalid digest length."""
        store = DiskStore(temp_cache_dir)
        with pytest.raises(ValueError, match="Invalid digest length"):
            store._get_path("short")

    def test_exists_false(self, temp_cache_dir):
        """Test exists returns False for non-existent artifact."""
        store = DiskStore(temp_cache_dir)
        assert not store.exists("a" * 64)

    def test_put_and_get(self, temp_cache_dir):
        """Test storing and retrieving an artifact."""
        store = DiskStore(temp_cache_dir)
        artifact = String("test")
        digest = artifact.get_stable_hash()

        store.put(digest, artifact)
        assert store.exists(digest)

        retrieved = store.get(digest)
        assert isinstance(retrieved, String)
        assert retrieved.value == "test"

    def test_get_nonexistent(self, temp_cache_dir):
        """Test that getting non-existent artifact raises KeyError."""
        store = DiskStore(temp_cache_dir)
        with pytest.raises(KeyError):
            store.get("a" * 64)

    def test_put_and_get_integer(self, temp_cache_dir):
        """Test storing and retrieving Integer."""
        store = DiskStore(temp_cache_dir)
        artifact = Integer(42)
        digest = artifact.get_stable_hash()

        store.put(digest, artifact)
        retrieved = store.get(digest)
        assert isinstance(retrieved, Integer)
        assert retrieved.value == 42

    def test_put_and_get_decimal(self, temp_cache_dir):
        """Test storing and retrieving DecimalValue."""
        store = DiskStore(temp_cache_dir)
        artifact = DecimalValue("3.14159")
        digest = artifact.get_stable_hash()

        store.put(digest, artifact)
        retrieved = store.get(digest)
        assert isinstance(retrieved, DecimalValue)
        assert retrieved.value == artifact.value

    def test_persistence(self, temp_cache_dir):
        """Test that artifacts persist across store instances."""
        store1 = DiskStore(temp_cache_dir)
        artifact = String("persistent")
        digest = artifact.get_stable_hash()

        store1.put(digest, artifact)

        # Create new store instance
        store2 = DiskStore(temp_cache_dir)
        assert store2.exists(digest)
        retrieved = store2.get(digest)
        assert retrieved.value == "persistent"

    def test_atomic_write(self, temp_cache_dir):
        """Test that writes are atomic (use temp file then rename)."""
        store = DiskStore(temp_cache_dir)
        artifact = String("atomic")
        digest = artifact.get_stable_hash()

        # This should not leave a .tmp file
        store.put(digest, artifact)

        # Check no .tmp files exist
        tmp_files = list(temp_cache_dir.rglob("*.tmp"))
        assert len(tmp_files) == 0

    def test_directory_structure(self, temp_cache_dir):
        """Test that directory structure is created correctly."""
        store = DiskStore(temp_cache_dir)
        artifact = String("test")
        digest = artifact.get_stable_hash()

        store.put(digest, artifact)

        # Check directory structure: {digest[:2]}/{digest[2:]}
        expected_dir = temp_cache_dir / digest[:2]
        assert expected_dir.exists()
        expected_file = expected_dir / digest[2:]
        assert expected_file.exists()
