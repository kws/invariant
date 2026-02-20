"""Tests for ICacheable protocol."""

from io import BytesIO

from invariant.protocol import ICacheable
from invariant.types import Polynomial


def test_polynomial_implements_protocol():
    """Test that Polynomial implements ICacheable protocol."""
    p = Polynomial((1, 2, 3))
    assert isinstance(p, ICacheable)

    # Test get_stable_hash
    hash1 = p.get_stable_hash()
    assert isinstance(hash1, str)
    assert len(hash1) == 64  # SHA-256 hex string

    # Hash should be deterministic
    p2 = Polynomial((1, 2, 3))
    assert p2.get_stable_hash() == hash1

    # Different values should have different hashes
    p3 = Polynomial((1, 2, 4))
    assert p3.get_stable_hash() != hash1


def test_serialization_roundtrip():
    """Test that serialization/deserialization works correctly."""
    # Polynomial
    p1 = Polynomial((1, 2, 3))
    stream = BytesIO()
    p1.to_stream(stream)
    stream.seek(0)
    p2 = Polynomial.from_stream(stream)
    assert p1.coefficients == p2.coefficients
    assert p1.get_stable_hash() == p2.get_stable_hash()
