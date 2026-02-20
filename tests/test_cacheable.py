"""Tests for cacheable type boundary functions."""

from decimal import Decimal


from invariant.cacheable import is_cacheable
from invariant.types import Polynomial


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
        assert is_cacheable(Polynomial((1, 2, 3))) is True

    def test_dict_cacheable(self):
        """Test that dicts with string keys and cacheable values are cacheable."""
        assert is_cacheable({"a": 1, "b": 2}) is True
        assert is_cacheable({"x": "hello", "y": 42}) is True
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
        assert is_cacheable(["a", 42]) is True
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
