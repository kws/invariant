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
        assert not store.exists("nonexistent" * 8)  # 64 char digest
    
    def test_put_and_get(self):
        """Test storing and retrieving an artifact."""
        store = MemoryStore()
        artifact = String("test")
        digest = artifact.get_stable_hash()
        
        store.put(digest, artifact)
        assert store.exists(digest)
        
        retrieved = store.get(digest)
        assert isinstance(retrieved, String)
        assert retrieved.value == "test"
    
    def test_get_nonexistent(self):
        """Test that getting non-existent artifact raises KeyError."""
        store = MemoryStore()
        with pytest.raises(KeyError):
            store.get("nonexistent" * 8)
    
    def test_put_and_get_integer(self):
        """Test storing and retrieving Integer."""
        store = MemoryStore()
        artifact = Integer(42)
        digest = artifact.get_stable_hash()
        
        store.put(digest, artifact)
        retrieved = store.get(digest)
        assert isinstance(retrieved, Integer)
        assert retrieved.value == 42
    
    def test_put_and_get_decimal(self):
        """Test storing and retrieving DecimalValue."""
        store = MemoryStore()
        artifact = DecimalValue("3.14159")
        digest = artifact.get_stable_hash()
        
        store.put(digest, artifact)
        retrieved = store.get(digest)
        assert isinstance(retrieved, DecimalValue)
        assert retrieved.value == artifact.value
    
    def test_serialization_roundtrip(self):
        """Test that serialization preserves data."""
        store = MemoryStore()
        original = String("hello world")
        digest = original.get_stable_hash()
        
        store.put(digest, original)
        retrieved = store.get(digest)
        
        assert retrieved.value == original.value
        assert retrieved.get_stable_hash() == original.get_stable_hash()
    
    def test_clear(self):
        """Test clear method."""
        store = MemoryStore()
        artifact = String("test")
        digest = artifact.get_stable_hash()
        
        store.put(digest, artifact)
        assert store.exists(digest)
        
        store.clear()
        assert not store.exists(digest)
    
    def test_multiple_artifacts(self):
        """Test storing multiple artifacts."""
        store = MemoryStore()
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

