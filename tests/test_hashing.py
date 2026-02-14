"""Tests for hashing utilities."""

from decimal import Decimal

import pytest

from invariant.hashing import hash_manifest, hash_value
from invariant.types import DecimalValue, Integer, String


class TestHashValue:
    """Tests for hash_value function."""

    def test_hash_string(self):
        """Test hashing a string."""
        h1 = hash_value("hello")
        h2 = hash_value("hello")
        assert h1 == h2
        assert len(h1) == 64
        assert hash_value("world") != h1

    def test_hash_integer(self):
        """Test hashing an integer."""
        h1 = hash_value(42)
        h2 = hash_value(42)
        assert h1 == h2
        assert len(h1) == 64
        assert hash_value(43) != h1

    def test_hash_decimal(self):
        """Test hashing a Decimal."""
        h1 = hash_value(Decimal("1.5"))
        h2 = hash_value(Decimal("1.5"))
        assert h1 == h2
        assert len(h1) == 64

    def test_hash_none(self):
        """Test hashing None."""
        h1 = hash_value(None)
        h2 = hash_value(None)
        assert h1 == h2
        assert len(h1) == 64

    def test_hash_cacheable(self):
        """Test hashing an ICacheable object."""
        s = String("test")
        h1 = hash_value(s)
        h2 = hash_value(s)
        assert h1 == h2
        assert h1 == s.get_stable_hash()

    def test_hash_dict(self):
        """Test hashing a dictionary."""
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 2, "a": 1}  # Different key order
        h1 = hash_value(d1)
        h2 = hash_value(d2)
        # Should be same (keys sorted)
        assert h1 == h2

    def test_hash_dict_different_values(self):
        """Test that different dict values produce different hashes."""
        d1 = {"a": 1}
        d2 = {"a": 2}
        assert hash_value(d1) != hash_value(d2)

    def test_hash_list(self):
        """Test hashing a list."""
        l1 = [1, 2, 3]
        l2 = [1, 2, 3]
        h1 = hash_value(l1)
        h2 = hash_value(l2)
        assert h1 == h2

    def test_hash_list_order_matters(self):
        """Test that list order matters for hashing."""
        l1 = [1, 2, 3]
        l2 = [3, 2, 1]
        assert hash_value(l1) != hash_value(l2)

    def test_hash_nested_structures(self):
        """Test hashing nested structures."""
        d = {"a": 1, "b": {"c": 2, "d": [3, 4]}, "e": String("test")}
        h1 = hash_value(d)
        h2 = hash_value(d)
        assert h1 == h2

    def test_hash_unsupported_type(self):
        """Test that unsupported types raise TypeError."""
        with pytest.raises(TypeError):
            hash_value(1.5)  # float not allowed

    def test_hash_determinism(self):
        """Test that hashing is deterministic across runs."""
        # Same input should always produce same hash
        value = {"a": Integer(1), "b": String("test")}
        hashes = [hash_value(value) for _ in range(10)]
        assert len(set(hashes)) == 1  # All same


class TestHashManifest:
    """Tests for hash_manifest function."""

    def test_hash_simple_manifest(self):
        """Test hashing a simple manifest."""
        manifest = {"a": Integer(1), "b": String("test")}
        h1 = hash_manifest(manifest)
        h2 = hash_manifest(manifest)
        assert h1 == h2
        assert len(h1) == 64

    def test_hash_manifest_key_order(self):
        """Test that key order doesn't matter for manifest hashing."""
        m1 = {"a": 1, "b": 2}
        m2 = {"b": 2, "a": 1}
        h1 = hash_manifest(m1)
        h2 = hash_manifest(m2)
        assert h1 == h2  # Keys are sorted

    def test_hash_manifest_different_values(self):
        """Test that different values produce different hashes."""
        m1 = {"a": 1}
        m2 = {"a": 2}
        assert hash_manifest(m1) != hash_manifest(m2)

    def test_hash_manifest_nested(self):
        """Test hashing nested manifests."""
        manifest = {
            "param1": Integer(1),
            "param2": String("test"),
            "nested": {"inner": DecimalValue("1.5")},
        }
        h1 = hash_manifest(manifest)
        h2 = hash_manifest(manifest)
        assert h1 == h2

    def test_hash_manifest_with_cacheable(self):
        """Test hashing manifest with ICacheable values."""
        manifest = {"value": String("hello"), "number": Integer(42)}
        h1 = hash_manifest(manifest)
        h2 = hash_manifest(manifest)
        assert h1 == h2

    def test_hash_empty_manifest(self):
        """Test hashing an empty manifest."""
        manifest = {}
        h = hash_manifest(manifest)
        assert len(h) == 64
