"""Serialization codec for the full is_cacheable universe.

Handles native types (int, str, Decimal, bool, None, dict, list, tuple)
and ICacheable domain types (e.g. Polynomial) uniformly.
"""

import importlib
from decimal import Decimal
from io import BytesIO
from typing import Any

from invariant.cacheable import is_cacheable
from invariant.protocol import ICacheable


def serialize(value: Any) -> bytes:
    """Serialize a cacheable value to bytes.

    Supports the full is_cacheable universe:
    - Native types: int, str, bool, None, Decimal
    - Containers: dict, list, tuple (recursive)
    - ICacheable domain types: uses to_stream()

    Args:
        value: The value to serialize. Must be cacheable.

    Returns:
        Serialized bytes with type information.

    Raises:
        TypeError: If value is not cacheable.
    """
    if not is_cacheable(value):
        raise TypeError(f"Value is not cacheable: {type(value)}")

    stream = BytesIO()
    _serialize_value(value, stream)
    return stream.getvalue()


def deserialize(data: bytes) -> Any:
    """Deserialize bytes to a cacheable value.

    Args:
        data: Serialized bytes from serialize().

    Returns:
        The deserialized value.

    Raises:
        ValueError: If data format is invalid.
    """
    stream = BytesIO(data)
    return _deserialize_value(stream)


def _serialize_value(value: Any, stream: BytesIO) -> None:
    """Internal recursive serialization."""
    # None
    if value is None:
        stream.write(b"none")
        return

    # bool (check before int since bool is subclass of int)
    if isinstance(value, bool):
        stream.write(b"bool")
        stream.write(b"\x01" if value else b"\x00")
        return

    # int
    if isinstance(value, int):
        stream.write(b"int_")
        # Use 8-byte signed big-endian
        stream.write(value.to_bytes(8, byteorder="big", signed=True))
        return

    # str
    if isinstance(value, str):
        stream.write(b"str_")
        data = value.encode("utf-8")
        stream.write(len(data).to_bytes(8, byteorder="big", signed=False))
        stream.write(data)
        return

    # Decimal
    if isinstance(value, Decimal):
        stream.write(b"decm")
        # Store as canonical string
        data = str(value).encode("utf-8")
        stream.write(len(data).to_bytes(8, byteorder="big", signed=False))
        stream.write(data)
        return

    # dict
    if isinstance(value, dict):
        stream.write(b"dict")
        # Write length
        stream.write(len(value).to_bytes(8, byteorder="big", signed=False))
        # Write key-value pairs (sorted by key for determinism)
        for key, val in sorted(value.items()):
            # Key (must be str)
            key_data = key.encode("utf-8")
            stream.write(len(key_data).to_bytes(8, byteorder="big", signed=False))
            stream.write(key_data)
            # Value (recursive)
            _serialize_value(val, stream)
        return

    # list
    if isinstance(value, list):
        stream.write(b"list")
        # Write length
        stream.write(len(value).to_bytes(8, byteorder="big", signed=False))
        # Write elements (recursive)
        for item in value:
            _serialize_value(item, stream)
        return

    # tuple
    if isinstance(value, tuple):
        stream.write(b"tupl")
        # Write length
        stream.write(len(value).to_bytes(8, byteorder="big", signed=False))
        # Write elements (recursive)
        for item in value:
            _serialize_value(item, stream)
        return

    # ICacheable domain types
    if isinstance(value, ICacheable):
        stream.write(b"icac")
        # Store type information
        type_name = f"{value.__class__.__module__}.{value.__class__.__name__}"
        type_name_bytes = type_name.encode("utf-8")
        stream.write(len(type_name_bytes).to_bytes(4, byteorder="big", signed=False))
        stream.write(type_name_bytes)
        # Use existing to_stream() method
        value.to_stream(stream)
        return

    # Should never reach here if is_cacheable() is correct
    raise TypeError(f"Unsupported type for serialization: {type(value)}")


def _deserialize_value(stream: BytesIO) -> Any:
    """Internal recursive deserialization."""
    # Read type tag (4 bytes)
    tag = stream.read(4)
    if len(tag) != 4:
        raise ValueError("Invalid serialization format: truncated type tag")

    # None
    if tag == b"none":
        return None

    # bool
    if tag == b"bool":
        byte = stream.read(1)
        if len(byte) != 1:
            raise ValueError("Invalid serialization format: truncated bool")
        return byte == b"\x01"

    # int
    if tag == b"int_":
        data = stream.read(8)
        if len(data) != 8:
            raise ValueError("Invalid serialization format: truncated int")
        return int.from_bytes(data, byteorder="big", signed=True)

    # str
    if tag == b"str_":
        length_data = stream.read(8)
        if len(length_data) != 8:
            raise ValueError("Invalid serialization format: truncated str length")
        length = int.from_bytes(length_data, byteorder="big", signed=False)
        data = stream.read(length)
        if len(data) != length:
            raise ValueError("Invalid serialization format: truncated str data")
        return data.decode("utf-8")

    # Decimal
    if tag == b"decm":
        length_data = stream.read(8)
        if len(length_data) != 8:
            raise ValueError("Invalid serialization format: truncated decimal length")
        length = int.from_bytes(length_data, byteorder="big", signed=False)
        data = stream.read(length)
        if len(data) != length:
            raise ValueError("Invalid serialization format: truncated decimal data")
        return Decimal(data.decode("utf-8"))

    # dict
    if tag == b"dict":
        length_data = stream.read(8)
        if len(length_data) != 8:
            raise ValueError("Invalid serialization format: truncated dict length")
        length = int.from_bytes(length_data, byteorder="big", signed=False)
        result = {}
        for _ in range(length):
            # Read key
            key_length_data = stream.read(8)
            if len(key_length_data) != 8:
                raise ValueError(
                    "Invalid serialization format: truncated dict key length"
                )
            key_length = int.from_bytes(key_length_data, byteorder="big", signed=False)
            key_data = stream.read(key_length)
            if len(key_data) != key_length:
                raise ValueError("Invalid serialization format: truncated dict key")
            key = key_data.decode("utf-8")
            # Read value (recursive)
            value = _deserialize_value(stream)
            result[key] = value
        return result

    # list
    if tag == b"list":
        length_data = stream.read(8)
        if len(length_data) != 8:
            raise ValueError("Invalid serialization format: truncated list length")
        length = int.from_bytes(length_data, byteorder="big", signed=False)
        result = []
        for _ in range(length):
            item = _deserialize_value(stream)
            result.append(item)
        return result

    # tuple
    if tag == b"tupl":
        length_data = stream.read(8)
        if len(length_data) != 8:
            raise ValueError("Invalid serialization format: truncated tuple length")
        length = int.from_bytes(length_data, byteorder="big", signed=False)
        result = []
        for _ in range(length):
            item = _deserialize_value(stream)
            result.append(item)
        return tuple(result)

    # ICacheable domain types
    if tag == b"icac":
        # Read type name length
        type_name_len_data = stream.read(4)
        if len(type_name_len_data) != 4:
            raise ValueError(
                "Invalid serialization format: truncated ICacheable type name length"
            )
        type_name_len = int.from_bytes(
            type_name_len_data, byteorder="big", signed=False
        )
        # Read type name
        type_name_bytes = stream.read(type_name_len)
        if len(type_name_bytes) != type_name_len:
            raise ValueError(
                "Invalid serialization format: truncated ICacheable type name"
            )
        type_name = type_name_bytes.decode("utf-8")
        # Import the class
        module_path, class_name = type_name.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        # Deserialize using from_stream()
        return cls.from_stream(stream)

    raise ValueError(f"Unknown type tag: {tag!r}")
