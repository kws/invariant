"""Standard operations library for basic data manipulation."""

from typing import Any


def identity(value: Any) -> Any:
    """Identity operation: returns the input unchanged.

    Args:
        value: Any cacheable value.

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


def dict_get(dict_obj: dict[str, Any], key: str) -> Any:
    """Extract a value from a dictionary.

    Args:
        dict_obj: Dictionary object.
        key: String key to look up.

    Returns:
        The value at the specified key in the dictionary.

    Raises:
        KeyError: If key not in dictionary.
        TypeError: If dict_obj is not a dict.
    """
    if not isinstance(dict_obj, dict):
        raise TypeError(f"dict_get op requires dict, got {type(dict_obj)}")

    if key not in dict_obj:
        raise KeyError(f"Key '{key}' not found in dictionary")

    return dict_obj[key]


# Package of standard operations
OPS: dict[str, Any] = {
    "identity": identity,
    "add": add,
    "multiply": multiply,
    "dict_get": dict_get,
}
