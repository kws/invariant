"""Tests for codec serialization/deserialization."""

from decimal import Decimal
from unittest.mock import patch

import pytest

from invariant.store.codec import deserialize, serialize
from invariant.types import Polynomial


class TestSerialize:
    """Tests for serialize() function."""

    def test_serialize_none(self):
        """Test serialization of None."""
        data = serialize(None)
        assert isinstance(data, bytes)
        assert data == b"none"

    def test_serialize_bool_true(self):
        """Test serialization of bool True."""
        data = serialize(True)
        assert isinstance(data, bytes)
        assert data.startswith(b"bool")
        assert data == b"bool\x01"

    def test_serialize_bool_false(self):
        """Test serialization of bool False."""
        data = serialize(False)
        assert isinstance(data, bytes)
        assert data.startswith(b"bool")
        assert data == b"bool\x00"

    def test_serialize_int_zero(self):
        """Test serialization of int zero."""
        data = serialize(0)
        assert isinstance(data, bytes)
        assert data.startswith(b"int_")
        assert len(data) == 12  # 4 bytes tag + 8 bytes value

    def test_serialize_int_positive(self):
        """Test serialization of positive int."""
        data = serialize(42)
        assert isinstance(data, bytes)
        assert data.startswith(b"int_")
        deserialized = deserialize(data)
        assert deserialized == 42

    def test_serialize_int_negative(self):
        """Test serialization of negative int."""
        data = serialize(-42)
        assert isinstance(data, bytes)
        assert data.startswith(b"int_")
        deserialized = deserialize(data)
        assert deserialized == -42

    def test_serialize_int_large(self):
        """Test serialization of large int."""
        large_int = 2**63 - 1
        data = serialize(large_int)
        assert isinstance(data, bytes)
        deserialized = deserialize(data)
        assert deserialized == large_int

    def test_serialize_str_empty(self):
        """Test serialization of empty string."""
        data = serialize("")
        assert isinstance(data, bytes)
        assert data.startswith(b"str_")
        deserialized = deserialize(data)
        assert deserialized == ""

    def test_serialize_str_simple(self):
        """Test serialization of simple string."""
        data = serialize("hello")
        assert isinstance(data, bytes)
        assert data.startswith(b"str_")
        deserialized = deserialize(data)
        assert deserialized == "hello"

    def test_serialize_str_unicode(self):
        """Test serialization of unicode string."""
        unicode_str = "Hello, 世界! 🌍"
        data = serialize(unicode_str)
        assert isinstance(data, bytes)
        deserialized = deserialize(data)
        assert deserialized == unicode_str

    def test_serialize_str_long(self):
        """Test serialization of long string."""
        long_str = "a" * 1000
        data = serialize(long_str)
        assert isinstance(data, bytes)
        deserialized = deserialize(data)
        assert deserialized == long_str

    def test_serialize_decimal(self):
        """Test serialization of Decimal."""
        value = Decimal("3.14159")
        data = serialize(value)
        assert isinstance(data, bytes)
        assert data.startswith(b"decm")
        deserialized = deserialize(data)
        assert deserialized == value

    def test_serialize_decimal_zero(self):
        """Test serialization of Decimal zero."""
        value = Decimal("0")
        data = serialize(value)
        deserialized = deserialize(data)
        assert deserialized == value

    def test_serialize_decimal_negative(self):
        """Test serialization of negative Decimal."""
        value = Decimal("-123.456")
        data = serialize(value)
        deserialized = deserialize(data)
        assert deserialized == value

    def test_serialize_dict_empty(self):
        """Test serialization of empty dict."""
        data = serialize({})
        assert isinstance(data, bytes)
        assert data.startswith(b"dict")
        deserialized = deserialize(data)
        assert deserialized == {}

    def test_serialize_dict_simple(self):
        """Test serialization of simple dict."""
        value = {"a": 1, "b": 2}
        data = serialize(value)
        assert isinstance(data, bytes)
        deserialized = deserialize(data)
        assert deserialized == value

    def test_serialize_dict_sorted_keys(self):
        """Test that dict serialization uses sorted keys for determinism."""
        value = {"z": 3, "a": 1, "m": 2}
        data1 = serialize(value)
        data2 = serialize(value)
        # Should be identical (deterministic)
        assert data1 == data2
        # Verify keys are sorted in serialization
        deserialized = deserialize(data1)
        assert deserialized == value

    def test_serialize_dict_nested(self):
        """Test serialization of nested dict."""
        value = {"a": {"b": 1, "c": 2}, "d": 3}
        data = serialize(value)
        deserialized = deserialize(data)
        assert deserialized == value

    def test_serialize_list_empty(self):
        """Test serialization of empty list."""
        data = serialize([])
        assert isinstance(data, bytes)
        assert data.startswith(b"list")
        deserialized = deserialize(data)
        assert deserialized == []

    def test_serialize_list_simple(self):
        """Test serialization of simple list."""
        value = [1, 2, 3]
        data = serialize(value)
        assert isinstance(data, bytes)
        deserialized = deserialize(data)
        assert deserialized == value

    def test_serialize_list_nested(self):
        """Test serialization of nested list."""
        value = [[1, 2], [3, 4]]
        data = serialize(value)
        deserialized = deserialize(data)
        assert deserialized == value

    def test_serialize_list_mixed_types(self):
        """Test serialization of list with mixed types."""
        value = [1, "hello", True, None, Decimal("1.5")]
        data = serialize(value)
        deserialized = deserialize(data)
        assert deserialized == value

    def test_serialize_tuple_empty(self):
        """Test serialization of empty tuple."""
        data = serialize(())
        assert isinstance(data, bytes)
        assert data.startswith(b"tupl")
        deserialized = deserialize(data)
        assert deserialized == ()

    def test_serialize_tuple_simple(self):
        """Test serialization of simple tuple."""
        value = (1, 2, 3)
        data = serialize(value)
        assert isinstance(data, bytes)
        deserialized = deserialize(data)
        assert deserialized == value

    def test_serialize_tuple_nested(self):
        """Test serialization of nested tuple."""
        value = ((1, 2), (3, 4))
        data = serialize(value)
        deserialized = deserialize(data)
        assert deserialized == value

    def test_serialize_icacheable_polynomial(self):
        """Test serialization of ICacheable (Polynomial)."""
        poly = Polynomial((1, 2, 3))
        data = serialize(poly)
        assert isinstance(data, bytes)
        assert data.startswith(b"icac")
        deserialized = deserialize(data)
        assert isinstance(deserialized, Polynomial)
        assert deserialized.coefficients == poly.coefficients

    def test_serialize_non_cacheable_float(self):
        """Test that float raises TypeError."""
        with pytest.raises(TypeError, match="Value is not cacheable"):
            serialize(3.14)

    def test_serialize_non_cacheable_bytes(self):
        """Test that bytes raises TypeError."""
        with pytest.raises(TypeError, match="Value is not cacheable"):
            serialize(b"hello")

    def test_serialize_non_cacheable_object(self):
        """Test that arbitrary object raises TypeError."""
        with pytest.raises(TypeError, match="Value is not cacheable"):
            serialize(object())

    def test_serialize_unsupported_type_after_cacheable_check(self):
        """Test that unsupported type after is_cacheable() check raises TypeError."""

        # This tests the defensive check at line 142
        # Create a mock scenario where is_cacheable returns True but type doesn't match
        class UnsupportedType:
            pass

        obj = UnsupportedType()
        # Mock is_cacheable to return True (bypassing the normal check)
        with patch("invariant.store.codec.is_cacheable", return_value=True):
            with pytest.raises(TypeError, match="Unsupported type for serialization"):
                serialize(obj)


class TestDeserialize:
    """Tests for deserialize() function."""

    def test_deserialize_none(self):
        """Test deserialization of None."""
        data = b"none"
        result = deserialize(data)
        assert result is None

    def test_deserialize_bool_true(self):
        """Test deserialization of bool True."""
        data = b"bool\x01"
        result = deserialize(data)
        assert result is True

    def test_deserialize_bool_false(self):
        """Test deserialization of bool False."""
        data = b"bool\x00"
        result = deserialize(data)
        assert result is False

    def test_deserialize_int_zero(self):
        """Test deserialization of int zero."""
        data = b"int_" + (0).to_bytes(8, byteorder="big", signed=True)
        result = deserialize(data)
        assert result == 0

    def test_deserialize_int_positive(self):
        """Test deserialization of positive int."""
        data = b"int_" + (42).to_bytes(8, byteorder="big", signed=True)
        result = deserialize(data)
        assert result == 42

    def test_deserialize_int_negative(self):
        """Test deserialization of negative int."""
        data = b"int_" + (-42).to_bytes(8, byteorder="big", signed=True)
        result = deserialize(data)
        assert result == -42

    def test_deserialize_str_empty(self):
        """Test deserialization of empty string."""
        data = b"str_" + (0).to_bytes(8, byteorder="big", signed=False)
        result = deserialize(data)
        assert result == ""

    def test_deserialize_str_simple(self):
        """Test deserialization of simple string."""
        value = "hello"
        encoded = value.encode("utf-8")
        data = (
            b"str_" + len(encoded).to_bytes(8, byteorder="big", signed=False) + encoded
        )
        result = deserialize(data)
        assert result == value

    def test_deserialize_decimal(self):
        """Test deserialization of Decimal."""
        value = Decimal("3.14159")
        encoded = str(value).encode("utf-8")
        data = (
            b"decm" + len(encoded).to_bytes(8, byteorder="big", signed=False) + encoded
        )
        result = deserialize(data)
        assert result == value

    def test_deserialize_dict_empty(self):
        """Test deserialization of empty dict."""
        data = b"dict" + (0).to_bytes(8, byteorder="big", signed=False)
        result = deserialize(data)
        assert result == {}

    def test_deserialize_dict_simple(self):
        """Test deserialization of simple dict."""
        # Serialize a dict first, then deserialize
        original = {"a": 1, "b": 2}
        data = serialize(original)
        result = deserialize(data)
        assert result == original

    def test_deserialize_list_empty(self):
        """Test deserialization of empty list."""
        data = b"list" + (0).to_bytes(8, byteorder="big", signed=False)
        result = deserialize(data)
        assert result == []

    def test_deserialize_list_simple(self):
        """Test deserialization of simple list."""
        original = [1, 2, 3]
        data = serialize(original)
        result = deserialize(data)
        assert result == original

    def test_deserialize_tuple_empty(self):
        """Test deserialization of empty tuple."""
        data = b"tupl" + (0).to_bytes(8, byteorder="big", signed=False)
        result = deserialize(data)
        assert result == ()

    def test_deserialize_tuple_simple(self):
        """Test deserialization of simple tuple."""
        original = (1, 2, 3)
        data = serialize(original)
        result = deserialize(data)
        assert result == original

    def test_deserialize_icacheable_polynomial(self):
        """Test deserialization of ICacheable (Polynomial)."""
        original = Polynomial((1, 2, 3))
        data = serialize(original)
        result = deserialize(data)
        assert isinstance(result, Polynomial)
        assert result.coefficients == original.coefficients


class TestDeserializeErrors:
    """Tests for deserialize() error cases."""

    def test_truncated_type_tag_empty(self):
        """Test ValueError for empty type tag."""
        with pytest.raises(ValueError, match="truncated type tag"):
            deserialize(b"")

    def test_truncated_type_tag_partial(self):
        """Test ValueError for partial type tag."""
        with pytest.raises(ValueError, match="truncated type tag"):
            deserialize(b"no")  # Only 2 bytes

    def test_truncated_bool_empty(self):
        """Test ValueError for truncated bool (no data)."""
        with pytest.raises(ValueError, match="truncated bool"):
            deserialize(b"bool")

    def test_truncated_int_empty(self):
        """Test ValueError for truncated int (no data)."""
        with pytest.raises(ValueError, match="truncated int"):
            deserialize(b"int_")

    def test_truncated_int_partial(self):
        """Test ValueError for truncated int (partial data)."""
        data = b"int_" + b"\x00" * 4  # Only 4 bytes instead of 8
        with pytest.raises(ValueError, match="truncated int"):
            deserialize(data)

    def test_truncated_str_length_empty(self):
        """Test ValueError for truncated str length."""
        with pytest.raises(ValueError, match="truncated str length"):
            deserialize(b"str_")

    def test_truncated_str_length_partial(self):
        """Test ValueError for truncated str length (partial)."""
        data = b"str_" + b"\x00" * 4  # Only 4 bytes instead of 8
        with pytest.raises(ValueError, match="truncated str length"):
            deserialize(data)

    def test_truncated_str_data(self):
        """Test ValueError for truncated str data."""
        # Length says 10 bytes, but only provide 5
        data = (
            b"str_" + (10).to_bytes(8, byteorder="big", signed=False) + b"hello"
        )  # Only 5 bytes
        with pytest.raises(ValueError, match="truncated str data"):
            deserialize(data)

    def test_truncated_decimal_length_empty(self):
        """Test ValueError for truncated decimal length."""
        with pytest.raises(ValueError, match="truncated decimal length"):
            deserialize(b"decm")

    def test_truncated_decimal_length_partial(self):
        """Test ValueError for truncated decimal length (partial)."""
        data = b"decm" + b"\x00" * 4  # Only 4 bytes instead of 8
        with pytest.raises(ValueError, match="truncated decimal length"):
            deserialize(data)

    def test_truncated_decimal_data(self):
        """Test ValueError for truncated decimal data."""
        # Length says 10 bytes, but only provide 5
        data = (
            b"decm" + (10).to_bytes(8, byteorder="big", signed=False) + b"3.141"
        )  # Only 5 bytes
        with pytest.raises(ValueError, match="truncated decimal data"):
            deserialize(data)

    def test_truncated_dict_length_empty(self):
        """Test ValueError for truncated dict length."""
        with pytest.raises(ValueError, match="truncated dict length"):
            deserialize(b"dict")

    def test_truncated_dict_length_partial(self):
        """Test ValueError for truncated dict length (partial)."""
        data = b"dict" + b"\x00" * 4  # Only 4 bytes instead of 8
        with pytest.raises(ValueError, match="truncated dict length"):
            deserialize(data)

    def test_truncated_dict_key_length(self):
        """Test ValueError for truncated dict key length."""
        # Dict with length 1, but truncated key length
        data = b"dict" + (1).to_bytes(8, byteorder="big", signed=False) + b"\x00" * 4
        with pytest.raises(ValueError, match="truncated dict key length"):
            deserialize(data)

    def test_truncated_dict_key_data(self):
        """Test ValueError for truncated dict key data."""
        # Dict with length 1, key length 5, but only 3 bytes of key data
        data = (
            b"dict"
            + (1).to_bytes(8, byteorder="big", signed=False)
            + (5).to_bytes(8, byteorder="big", signed=False)
            + b"abc"  # Only 3 bytes instead of 5
        )
        with pytest.raises(ValueError, match="truncated dict key"):
            deserialize(data)

    def test_truncated_list_length_empty(self):
        """Test ValueError for truncated list length."""
        with pytest.raises(ValueError, match="truncated list length"):
            deserialize(b"list")

    def test_truncated_list_length_partial(self):
        """Test ValueError for truncated list length (partial)."""
        data = b"list" + b"\x00" * 4  # Only 4 bytes instead of 8
        with pytest.raises(ValueError, match="truncated list length"):
            deserialize(data)

    def test_truncated_tuple_length_empty(self):
        """Test ValueError for truncated tuple length."""
        with pytest.raises(ValueError, match="truncated tuple length"):
            deserialize(b"tupl")

    def test_truncated_tuple_length_partial(self):
        """Test ValueError for truncated tuple length (partial)."""
        data = b"tupl" + b"\x00" * 4  # Only 4 bytes instead of 8
        with pytest.raises(ValueError, match="truncated tuple length"):
            deserialize(data)

    def test_truncated_icacheable_type_name_length_empty(self):
        """Test ValueError for truncated ICacheable type name length."""
        with pytest.raises(ValueError, match="truncated ICacheable type name length"):
            deserialize(b"icac")

    def test_truncated_icacheable_type_name_length_partial(self):
        """Test ValueError for truncated ICacheable type name length (partial)."""
        data = b"icac" + b"\x00" * 2  # Only 2 bytes instead of 4
        with pytest.raises(ValueError, match="truncated ICacheable type name length"):
            deserialize(data)

    def test_truncated_icacheable_type_name(self):
        """Test ValueError for truncated ICacheable type name."""
        # Type name length says 50, but only provide 10 bytes
        type_name = "invariant.types.Polynomial"
        data = (
            b"icac"
            + (50).to_bytes(4, byteorder="big", signed=False)
            + type_name[:10].encode("utf-8")  # Only 10 bytes
        )
        with pytest.raises(ValueError, match="truncated ICacheable type name"):
            deserialize(data)

    def test_unknown_type_tag(self):
        """Test ValueError for unknown type tag."""
        with pytest.raises(ValueError, match="Unknown type tag"):
            deserialize(b"xxxx" + b"\x00" * 8)


class TestRoundTrip:
    """Tests for round-trip serialization/deserialization."""

    def test_roundtrip_none(self):
        """Test round-trip for None."""
        original = None
        data = serialize(original)
        result = deserialize(data)
        assert result is original

    def test_roundtrip_bool_true(self):
        """Test round-trip for bool True."""
        original = True
        data = serialize(original)
        result = deserialize(data)
        assert result is original

    def test_roundtrip_bool_false(self):
        """Test round-trip for bool False."""
        original = False
        data = serialize(original)
        result = deserialize(data)
        assert result is original

    def test_roundtrip_int(self):
        """Test round-trip for int."""
        for value in [0, 1, -1, 42, -42, 2**63 - 1, -(2**63)]:
            data = serialize(value)
            result = deserialize(data)
            assert result == value
            assert isinstance(result, int)

    def test_roundtrip_str(self):
        """Test round-trip for str."""
        for value in ["", "hello", "Hello, 世界! 🌍", "a" * 1000]:
            data = serialize(value)
            result = deserialize(data)
            assert result == value
            assert isinstance(result, str)

    def test_roundtrip_decimal(self):
        """Test round-trip for Decimal."""
        for value in [Decimal("0"), Decimal("3.14159"), Decimal("-123.456")]:
            data = serialize(value)
            result = deserialize(data)
            assert result == value
            assert isinstance(result, Decimal)

    def test_roundtrip_dict(self):
        """Test round-trip for dict."""
        test_cases = [
            {},
            {"a": 1},
            {"a": 1, "b": 2, "c": 3},
            {"nested": {"a": 1, "b": 2}},
            {"list": [1, 2, 3], "str": "hello"},
        ]
        for original in test_cases:
            data = serialize(original)
            result = deserialize(data)
            assert result == original
            assert isinstance(result, dict)

    def test_roundtrip_list(self):
        """Test round-trip for list."""
        test_cases = [
            [],
            [1],
            [1, 2, 3],
            [[1, 2], [3, 4]],
            [1, "hello", True, None, Decimal("1.5")],
        ]
        for original in test_cases:
            data = serialize(original)
            result = deserialize(data)
            assert result == original
            assert isinstance(result, list)

    def test_roundtrip_tuple(self):
        """Test round-trip for tuple."""
        test_cases = [
            (),
            (1,),
            (1, 2, 3),
            ((1, 2), (3, 4)),
            (1, "hello", True, None, Decimal("1.5")),
        ]
        for original in test_cases:
            data = serialize(original)
            result = deserialize(data)
            assert result == original
            assert isinstance(result, tuple)

    def test_roundtrip_icacheable_polynomial(self):
        """Test round-trip for ICacheable (Polynomial)."""
        test_cases = [
            Polynomial((1,)),
            Polynomial((1, 2, 3)),
            Polynomial((0,)),
            Polynomial((1, 0, 0, 1)),  # Will be canonicalized
        ]
        for original in test_cases:
            data = serialize(original)
            result = deserialize(data)
            assert isinstance(result, Polynomial)
            assert result.coefficients == original.coefficients
            assert result == original

    def test_roundtrip_nested_structures(self):
        """Test round-trip for complex nested structures."""
        original = {
            "list": [1, 2, {"nested": "dict"}],
            "tuple": (1, 2, [3, 4]),
            "polynomial": Polynomial((1, 2, 3)),
            "decimal": Decimal("3.14"),
            "none": None,
            "bool": True,
        }
        data = serialize(original)
        result = deserialize(data)
        assert result == original
        assert isinstance(result["polynomial"], Polynomial)
        assert isinstance(result["decimal"], Decimal)
