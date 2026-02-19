"""Standard operations library for basic data manipulation."""

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from invariant.protocol import ICacheable
from invariant.types import DecimalValue, Integer, String


def identity(manifest: dict[str, Any]) -> ICacheable:
    """Identity operation: returns the input unchanged.

    Args:
        manifest: Must contain 'value' key with an ICacheable value.

    Returns:
        The input value unchanged.

    Raises:
        KeyError: If 'value' key is missing.
        TypeError: If value is not ICacheable.
    """
    if "value" not in manifest:
        raise KeyError("identity op requires 'value' in manifest")
    value = manifest["value"]
    if not isinstance(value, ICacheable):
        raise TypeError(f"identity op requires ICacheable value, got {type(value)}")
    return value


def add(manifest: dict[str, Any]) -> ICacheable:
    """Add two numbers (integers or Decimals).

    Args:
        manifest: Must contain 'a' and 'b' keys with numeric values.
                 Values can be Integer, DecimalValue, or int.

    Returns:
        Integer if both inputs are integers, DecimalValue otherwise.

    Raises:
        KeyError: If 'a' or 'b' keys are missing.
        TypeError: If values are not numeric or are floats.
    """
    if "a" not in manifest or "b" not in manifest:
        raise KeyError("add op requires 'a' and 'b' in manifest")

    a = manifest["a"]
    b = manifest["b"]

    # Extract numeric values
    a_val = _extract_numeric(a, "a")
    b_val = _extract_numeric(b, "b")

    # Floats are caught in _extract_numeric, so we don't need to check here

    # Perform addition
    result = a_val + b_val

    # Return appropriate type
    if isinstance(a_val, int) and isinstance(b_val, int):
        return Integer(result)
    else:
        return DecimalValue(result)


def multiply(manifest: dict[str, Any]) -> ICacheable:
    """Multiply two numbers (integers or Decimals).

    Args:
        manifest: Must contain 'a' and 'b' keys with numeric values.
                 Values can be Integer, DecimalValue, or int.

    Returns:
        Integer if both inputs are integers, DecimalValue otherwise.

    Raises:
        KeyError: If 'a' or 'b' keys are missing.
        TypeError: If values are not numeric or are floats.
    """
    if "a" not in manifest or "b" not in manifest:
        raise KeyError("multiply op requires 'a' and 'b' in manifest")

    a = manifest["a"]
    b = manifest["b"]

    # Extract numeric values
    a_val = _extract_numeric(a, "a")
    b_val = _extract_numeric(b, "b")

    # Floats are caught in _extract_numeric, so we don't need to check here

    # Perform multiplication
    result = a_val * b_val

    # Return appropriate type
    if isinstance(a_val, int) and isinstance(b_val, int):
        return Integer(result)
    else:
        return DecimalValue(result)


def dict_get(manifest: dict[str, Any]) -> ICacheable:
    """Extract a value from a dictionary artifact.

    Args:
        manifest: Must contain 'dict' (ICacheable dict) and 'key' (string) keys.

    Returns:
        The value at the specified key in the dictionary.

    Raises:
        KeyError: If 'dict' or 'key' missing, or key not in dictionary.
        TypeError: If dict is not a dict-like ICacheable.
    """
    if "dict" not in manifest:
        raise KeyError("dict_get op requires 'dict' in manifest")
    if "key" not in manifest:
        raise KeyError("dict_get op requires 'key' in manifest")

    dict_obj = manifest["dict"]
    key = manifest["key"]

    if not isinstance(dict_obj, ICacheable):
        raise TypeError(f"dict_get op requires ICacheable dict, got {type(dict_obj)}")

    # For now, we'll assume dict_obj is a DictArtifact or similar
    # We need a Dict type that implements ICacheable
    # For now, let's raise an error if it's not a dict-like object
    # Actually, we should create a Dict cacheable type, but for now
    # let's assume the dict is stored in a way we can access it

    # Since we don't have a Dict type yet, let's check if it's a dict
    # or has dict-like access. For now, raise NotImplementedError
    # and we'll implement a Dict type if needed.

    # Actually, let me check if it's a Mapping or has __getitem__
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


def dict_merge(manifest: dict[str, Any]) -> ICacheable:
    """Merge multiple dictionary artifacts.

    Args:
        manifest: Must contain 'dicts' key with a list of dict-like ICacheable objects.
                 Later dicts override earlier ones for duplicate keys.

    Returns:
        A merged dictionary (as a DictArtifact - for now, we'll need to implement this).

    Raises:
        KeyError: If 'dicts' key is missing.
        TypeError: If values are not dict-like.
    """
    # This requires a Dict cacheable type which we haven't implemented yet
    # For now, raise NotImplementedError
    raise NotImplementedError(
        "dict_merge requires Dict cacheable type, not yet implemented"
    )


def list_append(manifest: dict[str, Any]) -> ICacheable:
    """Append an item to a list.

    Args:
        manifest: Must contain 'list' (ICacheable list) and 'item' (ICacheable) keys.

    Returns:
        A new list with the item appended.

    Raises:
        KeyError: If 'list' or 'item' keys are missing.
        TypeError: If list is not list-like.
    """
    # This requires a List cacheable type which we haven't implemented yet
    # For now, raise NotImplementedError
    raise NotImplementedError(
        "list_append requires List cacheable type, not yet implemented"
    )


def from_integer(manifest: dict[str, Any]) -> ICacheable:
    """Create an Integer from an integer value.

    Args:
        manifest: Must contain 'value' key with an integer value.

    Returns:
        Integer wrapping the value.

    Raises:
        KeyError: If 'value' key is missing.
        TypeError: If value is not an integer.
    """
    if "value" not in manifest:
        raise KeyError("stdlib:from_integer op requires 'value' in manifest")

    value = manifest["value"]
    if isinstance(value, Integer):
        return value
    elif isinstance(value, int):
        return Integer(value)
    else:
        raise TypeError(
            f"stdlib:from_integer op requires int or Integer value, got {type(value)}"
        )


def _extract_numeric(value: Any, name: str) -> int | Decimal:
    """Extract numeric value from various types.

    Args:
        value: Can be Integer, DecimalValue, int, or Decimal.
        name: Name of the parameter (for error messages).

    Returns:
        int or Decimal value.

    Raises:
        TypeError: If value is not numeric.
    """
    if isinstance(value, Integer):
        return value.value
    elif isinstance(value, DecimalValue):
        return value.value
    elif isinstance(value, int):
        return value
    elif isinstance(value, Decimal):
        return value
    elif isinstance(value, str):
        # Try to parse as number
        try:
            if "." in value:
                return Decimal(value)
            else:
                return int(value)
        except ValueError:
            raise TypeError(f"{name} must be numeric, got string '{value}'")
    else:
        raise TypeError(
            f"{name} must be numeric (Integer, DecimalValue, int, or Decimal), got {type(value)}"
        )
