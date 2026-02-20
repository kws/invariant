"""Tests for standard operations library."""

import pytest

from invariant.ops.stdlib import add, from_integer, identity, multiply
from invariant.types import Integer, String


class TestIdentity:
    """Tests for identity operation."""

    def test_identity_string(self):
        """Test identity with String."""
        value = String("test")
        result = identity(value)
        assert result == value
        assert isinstance(result, String)

    def test_identity_integer(self):
        """Test identity with Integer."""
        value = Integer(42)
        result = identity(value)
        assert result == value
        assert isinstance(result, Integer)


class TestAdd:
    """Tests for add operation."""

    def test_add_integers(self):
        """Test adding two integers."""
        result = add(a=1, b=2)
        assert isinstance(result, int)
        assert result == 3

    def test_add_negative(self):
        """Test adding negative integers."""
        result = add(a=-5, b=3)
        assert result == -2

    def test_add_zero(self):
        """Test adding with zero."""
        result = add(a=42, b=0)
        assert result == 42


class TestMultiply:
    """Tests for multiply operation."""

    def test_multiply_integers(self):
        """Test multiplying two integers."""
        result = multiply(a=3, b=4)
        assert isinstance(result, int)
        assert result == 12

    def test_multiply_negative(self):
        """Test multiplying negative integers."""
        result = multiply(a=-2, b=3)
        assert result == -6

    def test_multiply_zero(self):
        """Test multiplying by zero."""
        result = multiply(a=42, b=0)
        assert result == 0


class TestFromInteger:
    """Tests for from_integer operation."""

    def test_from_integer(self):
        """Test creating Integer from int."""
        result = from_integer(42)
        assert isinstance(result, Integer)
        assert result.value == 42

    def test_from_integer_zero(self):
        """Test creating Integer from zero."""
        result = from_integer(0)
        assert isinstance(result, Integer)
        assert result.value == 0

    def test_from_integer_negative(self):
        """Test creating Integer from negative int."""
        result = from_integer(-10)
        assert isinstance(result, Integer)
        assert result.value == -10


class TestDictGet:
    """Tests for dict_get operation."""

    def test_dict_get_not_implemented(self):
        """Test that dict_get requires ICacheable dict (not yet implemented)."""
        from invariant.ops.stdlib import dict_get

        # dict_get requires a Dict cacheable type which we haven't implemented
        with pytest.raises((TypeError, KeyError)):
            # The actual error depends on what we pass
            dict_get(dict_obj={}, key="test")
