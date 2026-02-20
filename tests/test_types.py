"""Tests for domain types (ICacheable implementors)."""

from io import BytesIO

from invariant.types import Polynomial


class TestPolynomial:
    """Tests for Polynomial type."""

    def test_creation(self):
        """Test Polynomial creation."""
        p = Polynomial((1, 2, 3))
        assert p.coefficients == (1, 2, 3)

    def test_hash_determinism(self):
        """Test that hash is deterministic."""
        p1 = Polynomial((1, 2, 3))
        p2 = Polynomial((1, 2, 3))
        assert p1.get_stable_hash() == p2.get_stable_hash()

    def test_serialization(self):
        """Test serialization roundtrip."""
        p1 = Polynomial((1, 2, 3))
        stream = BytesIO()
        p1.to_stream(stream)
        stream.seek(0)
        p2 = Polynomial.from_stream(stream)
        assert p1.coefficients == p2.coefficients
        assert p1 == p2
