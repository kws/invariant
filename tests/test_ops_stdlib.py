"""Tests for standard operations library."""

from decimal import Decimal

import pytest

from invariant.ops.stdlib import add, identity, multiply
from invariant.types import DecimalValue, Integer, String


class TestIdentity:
    """Tests for identity operation."""

    def test_identity_string(self):
        """Test identity with String."""
        value = String("test")
        result = identity({"value": value})
        assert result == value
        assert isinstance(result, String)

    def test_identity_integer(self):
        """Test identity with Integer."""
        value = Integer(42)
        result = identity({"value": value})
        assert result == value
        assert isinstance(result, Integer)

    def test_identity_missing_key(self):
        """Test that missing 'value' key raises KeyError."""
        with pytest.raises(KeyError, match="requires 'value'"):
            identity({})

    def test_identity_non_cacheable(self):
        """Test that non-ICacheable value raises TypeError."""
        with pytest.raises(TypeError):
            identity({"value": "not cacheable"})


class TestAdd:
    """Tests for add operation."""

    def test_add_integers(self):
        """Test adding two integers."""
        result = add({"a": Integer(1), "b": Integer(2)})
        assert isinstance(result, Integer)
        assert result.value == 3

    def test_add_integer_and_decimal(self):
        """Test adding integer and decimal."""
        result = add({"a": Integer(1), "b": DecimalValue("2.5")})
        assert isinstance(result, DecimalValue)
        assert result.value == Decimal("3.5")

    def test_add_decimals(self):
        """Test adding two decimals."""
        result = add({"a": DecimalValue("1.5"), "b": DecimalValue("2.5")})
        assert isinstance(result, DecimalValue)
        assert result.value == Decimal("4.0")

    def test_add_primitive_int(self):
        """Test adding primitive integers."""
        result = add({"a": 1, "b": 2})
        assert isinstance(result, Integer)
        assert result.value == 3

    def test_add_missing_key(self):
        """Test that missing key raises KeyError."""
        with pytest.raises(KeyError, match="requires 'a' and 'b'"):
            add({"a": Integer(1)})

    def test_add_float_raises(self):
        """Test that float raises TypeError."""
        with pytest.raises(TypeError, match="must be numeric"):
            add({"a": 1.5, "b": 2.5})


class TestMultiply:
    """Tests for multiply operation."""

    def test_multiply_integers(self):
        """Test multiplying two integers."""
        result = multiply({"a": Integer(3), "b": Integer(4)})
        assert isinstance(result, Integer)
        assert result.value == 12

    def test_multiply_integer_and_decimal(self):
        """Test multiplying integer and decimal."""
        result = multiply({"a": Integer(2), "b": DecimalValue("3.5")})
        assert isinstance(result, DecimalValue)
        assert result.value == Decimal("7.0")

    def test_multiply_decimals(self):
        """Test multiplying two decimals."""
        result = multiply({"a": DecimalValue("1.5"), "b": DecimalValue("2.0")})
        assert isinstance(result, DecimalValue)
        assert result.value == Decimal("3.0")

    def test_multiply_primitive_int(self):
        """Test multiplying primitive integers."""
        result = multiply({"a": 2, "b": 3})
        assert isinstance(result, Integer)
        assert result.value == 6

    def test_multiply_missing_key(self):
        """Test that missing key raises KeyError."""
        with pytest.raises(KeyError, match="requires 'a' and 'b'"):
            multiply({"a": Integer(1)})

    def test_multiply_float_raises(self):
        """Test that float raises TypeError."""
        with pytest.raises(TypeError, match="must be numeric"):
            multiply({"a": 1.5, "b": 2.5})


class TestDictGet:
    """Tests for dict_get operation."""

    def test_dict_get_not_implemented(self):
        """Test that dict_get raises NotImplementedError for now."""
        from invariant.ops.stdlib import dict_get

        # dict_get requires a Dict cacheable type which we haven't implemented
        with pytest.raises((NotImplementedError, TypeError, KeyError)):
            # The actual error depends on what we pass
            dict_get({"dict": {}, "key": "test"})


class TestDictMerge:
    """Tests for dict_merge operation."""

    def test_dict_merge_not_implemented(self):
        """Test that dict_merge raises NotImplementedError."""
        from invariant.ops.stdlib import dict_merge

        with pytest.raises(NotImplementedError):
            dict_merge({"dicts": []})


class TestListAppend:
    """Tests for list_append operation."""

    def test_list_append_not_implemented(self):
        """Test that list_append raises NotImplementedError."""
        from invariant.ops.stdlib import list_append

        with pytest.raises(NotImplementedError):
            list_append({"list": [], "item": String("test")})
