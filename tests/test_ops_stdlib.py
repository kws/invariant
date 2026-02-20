"""Tests for standard operations library."""

import pytest

from invariant.ops.stdlib import add, dict_get, identity, multiply


class TestIdentity:
    """Tests for identity operation."""

    def test_identity_string(self):
        """Test identity with string."""
        value = "test"
        result = identity(value)
        assert result == value
        assert isinstance(result, str)

    def test_identity_integer(self):
        """Test identity with integer."""
        value = 42
        result = identity(value)
        assert result == value
        assert isinstance(result, int)


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


class TestDictGet:
    """Tests for dict_get operation."""

    def test_dict_get(self):
        """Test extracting value from dict."""
        result = dict_get(dict_obj={"a": 1, "b": 2}, key="a")
        assert result == 1

    def test_dict_get_missing_key(self):
        """Test that missing key raises KeyError."""
        with pytest.raises(KeyError):
            dict_get(dict_obj={"a": 1}, key="missing")

    def test_dict_get_not_dict(self):
        """Test that non-dict raises TypeError."""
        with pytest.raises(TypeError):
            dict_get(dict_obj="not a dict", key="a")
