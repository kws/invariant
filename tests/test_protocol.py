"""Tests for ICacheable protocol."""

from io import BytesIO

import pytest

from invariant.protocol import ICacheable
from invariant.types import DecimalValue, Integer, String


def test_string_implements_protocol():
    """Test that String implements ICacheable protocol."""
    s = String("hello")
    assert isinstance(s, ICacheable)
    
    # Test get_stable_hash
    hash1 = s.get_stable_hash()
    assert isinstance(hash1, str)
    assert len(hash1) == 64  # SHA-256 hex string
    
    # Hash should be deterministic
    s2 = String("hello")
    assert s2.get_stable_hash() == hash1
    
    # Different values should have different hashes
    s3 = String("world")
    assert s3.get_stable_hash() != hash1


def test_integer_implements_protocol():
    """Test that Integer implements ICacheable protocol."""
    i = Integer(42)
    assert isinstance(i, ICacheable)
    
    hash1 = i.get_stable_hash()
    assert isinstance(hash1, str)
    assert len(hash1) == 64
    
    # Deterministic
    i2 = Integer(42)
    assert i2.get_stable_hash() == hash1
    
    # Different values
    i3 = Integer(43)
    assert i3.get_stable_hash() != hash1


def test_decimal_implements_protocol():
    """Test that DecimalValue implements ICacheable protocol."""
    d = DecimalValue("3.14159")
    assert isinstance(d, ICacheable)
    
    hash1 = d.get_stable_hash()
    assert isinstance(hash1, str)
    assert len(hash1) == 64
    
    # Deterministic
    d2 = DecimalValue("3.14159")
    assert d2.get_stable_hash() == hash1


def test_serialization_roundtrip():
    """Test that serialization/deserialization works correctly."""
    # String
    s1 = String("test")
    stream = BytesIO()
    s1.to_stream(stream)
    stream.seek(0)
    s2 = String.from_stream(stream)
    assert s1.value == s2.value
    assert s1.get_stable_hash() == s2.get_stable_hash()
    
    # Integer
    i1 = Integer(123)
    stream = BytesIO()
    i1.to_stream(stream)
    stream.seek(0)
    i2 = Integer.from_stream(stream)
    assert i1.value == i2.value
    assert i1.get_stable_hash() == i2.get_stable_hash()
    
    # Decimal
    d1 = DecimalValue("1.23")
    stream = BytesIO()
    d1.to_stream(stream)
    stream.seek(0)
    d2 = DecimalValue.from_stream(stream)
    assert d1.value == d2.value
    assert d1.get_stable_hash() == d2.get_stable_hash()

