"""Standard operations library for basic data manipulation."""

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from invariant.protocol import ICacheable
from invariant.types import DecimalValue, Integer, String


def identity(value: ICacheable) -> ICacheable:
    """Identity operation: returns the input unchanged.

    Args:
        value: An ICacheable value.

    Returns:
        The input value unchanged.
    """
    return value


def add(a: int, b: int) -> int:
    """Add two integers.

    Args:
        a: First integer.
        b: Second integer.

    Returns:
        Sum of a and b.
    """
    return a + b


def multiply(a: int, b: int) -> int:
    """Multiply two integers.

    Args:
        a: First integer.
        b: Second integer.

    Returns:
        Product of a and b.
    """
    return a * b


def dict_get(dict_obj: Mapping[str, Any], key: str) -> Any:
    """Extract a value from a dictionary artifact.

    Args:
        dict_obj: Dictionary-like object (must be ICacheable and Mapping).
        key: String key to look up.

    Returns:
        The value at the specified key in the dictionary.

    Raises:
        KeyError: If key not in dictionary.
        TypeError: If dict_obj is not dict-like or not ICacheable.
    """
    if not isinstance(dict_obj, ICacheable):
        raise TypeError(f"dict_get op requires ICacheable dict, got {type(dict_obj)}")

    if not isinstance(dict_obj, Mapping) and not hasattr(dict_obj, "__getitem__"):
        raise TypeError(f"dict_get op requires dict-like object, got {type(dict_obj)}")

    # Try to get the value
    try:
        value = dict_obj[key]  # type: ignore
    except (KeyError, TypeError):
        raise KeyError(f"Key '{key}' not found in dictionary")

    # Return as ICacheable if it is, otherwise wrap it
    if isinstance(value, ICacheable):
        return value
    elif isinstance(value, str):
        return String(value)
    elif isinstance(value, int):
        return Integer(value)
    elif isinstance(value, Decimal):
        return DecimalValue(value)
    else:
        raise TypeError(f"Cannot convert value type {type(value)} to ICacheable")


def from_integer(value: int) -> Integer:
    """Create an Integer from an integer value.

    Args:
        value: An integer value.

    Returns:
        Integer wrapping the value.
    """
    return Integer(value)


# Package of standard operations
OPS: dict[str, Any] = {
    "identity": identity,
    "add": add,
    "multiply": multiply,
    "from_integer": from_integer,
    "dict_get": dict_get,
}
