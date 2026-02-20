"""Tests for cacheable type boundary functions."""

from decimal import Decimal

import pytest

from invariant.cacheable import is_cacheable, to_cacheable
from invariant.types import DecimalValue, Integer, Polynomial, String


class TestIsCacheable:
    """Tests for is_cacheable() function."""

    def test_primitives(self):
        """Test that primitives are cacheable."""
        assert is_cacheable(42) is True
        assert is_cacheable("hello") is True
        assert is_cacheable(True) is True
        assert is_cacheable(False) is True
        assert is_cacheable(None) is True

    def test_decimal(self):
        """Test that Decimal is cacheable."""
        assert is_cacheable(Decimal("3.14")) is True

    def test_float_forbidden(self):
        """Test that float is explicitly forbidden."""
        assert is_cacheable(3.14) is False

    def test_bytes_forbidden(self):
        """Test that bytes is forbidden."""
        assert is_cacheable(b"hello") is False

    def test_icacheable_types(self):
        """Test that ICacheable implementors are cacheable."""
        assert is_cacheable(Integer(42)) is True
        assert is_cacheable(String("hello")) is True
        assert is_cacheable(DecimalValue("3.14")) is True
        assert is_cacheable(Polynomial((1, 2, 3))) is True

    def test_dict_cacheable(self):
        """Test that dicts with string keys and cacheable values are cacheable."""
        assert is_cacheable({"a": 1, "b": 2}) is True
        assert is_cacheable({"x": String("hello"), "y": Integer(42)}) is True
        assert is_cacheable({"nested": {"a": 1, "b": 2}}) is True

    def test_dict_non_string_keys_forbidden(self):
        """Test that dicts with non-string keys are forbidden."""
        assert is_cacheable({1: "a", 2: "b"}) is False

    def test_dict_nested_forbidden_value(self):
        """Test that dicts with forbidden nested values are not cacheable."""
        assert is_cacheable({"a": 1.5}) is False  # nested float
        assert is_cacheable({"a": b"bytes"}) is False  # nested bytes

    def test_list_cacheable(self):
        """Test that lists of cacheable values are cacheable."""
        assert is_cacheable([1, 2, 3]) is True
        assert is_cacheable([String("a"), Integer(42)]) is True
        assert is_cacheable([[1, 2], [3, 4]]) is True  # nested lists

    def test_list_nested_forbidden(self):
        """Test that lists with forbidden nested values are not cacheable."""
        assert is_cacheable([1, 2.5, 3]) is False  # nested float

    def test_tuple_cacheable(self):
        """Test that tuples of cacheable values are cacheable."""
        assert is_cacheable((1, 2, 3)) is True
        assert is_cacheable(("a", "b", "c")) is True

    def test_tuple_nested_forbidden(self):
        """Test that tuples with forbidden nested values are not cacheable."""
        assert is_cacheable((1, 2.5, 3)) is False  # nested float

    def test_arbitrary_objects_forbidden(self):
        """Test that arbitrary objects are forbidden."""
        assert is_cacheable(object()) is False
        assert is_cacheable([]) is True  # empty list is cacheable
        assert is_cacheable({}) is True  # empty dict is cacheable


class TestToCacheable:
    """Tests for to_cacheable() function."""

    def test_integer_wrapping(self):
        """Test wrapping int to Integer."""
        result = to_cacheable(42)
        assert isinstance(result, Integer)
        assert result.value == 42

    def test_string_wrapping(self):
        """Test wrapping str to String."""
        result = to_cacheable("hello")
        assert isinstance(result, String)
        assert result.value == "hello"

    def test_decimal_wrapping(self):
        """Test wrapping Decimal to DecimalValue."""
        result = to_cacheable(Decimal("3.14"))
        assert isinstance(result, DecimalValue)
        assert result.value == Decimal("3.14")

    def test_bool_wrapping(self):
        """Test wrapping bool to Integer."""
        result_true = to_cacheable(True)
        assert isinstance(result_true, Integer)
        assert result_true.value == 1

        result_false = to_cacheable(False)
        assert isinstance(result_false, Integer)
        assert result_false.value == 0

    def test_icacheable_passthrough(self):
        """Test that ICacheable values are passed through unchanged."""
        original = Integer(42)
        result = to_cacheable(original)
        assert result is original

        original_str = String("hello")
        result_str = to_cacheable(original_str)
        assert result_str is original_str

    def test_none_not_implemented(self):
        """Test that None raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="None values"):
            to_cacheable(None)

    def test_containers_not_implemented(self):
        """Test that containers raise NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Container types"):
            to_cacheable([1, 2, 3])

        with pytest.raises(NotImplementedError, match="Container types"):
            to_cacheable({"a": 1, "b": 2})

        with pytest.raises(NotImplementedError, match="Container types"):
            to_cacheable((1, 2, 3))

    def test_forbidden_types(self):
        """Test that forbidden types raise TypeError."""
        with pytest.raises(TypeError, match="Cannot convert"):
            to_cacheable(3.14)  # float

        with pytest.raises(TypeError, match="Cannot convert"):
            to_cacheable(b"bytes")  # bytes

        with pytest.raises(TypeError, match="Cannot convert"):
            to_cacheable(object())  # arbitrary object
