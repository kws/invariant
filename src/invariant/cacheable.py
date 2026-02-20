"""Cacheable type boundary: the single source of truth for allowed types.

This module defines the Cacheable Type Universe and provides two core functions
that are used throughout the Invariant system to validate and convert values.

The Allowed Types (recursive for containers):
  - int, str, bool, None
  - Decimal (safe numerics — no float!)
  - dict[str, CacheableValue]  (string keys only)
  - list[CacheableValue], tuple[CacheableValue, ...]
  - Any ICacheable implementor

FORBIDDEN: float (IEEE 754 non-determinism), bytes, arbitrary objects
"""

from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from invariant.protocol import ICacheable
from invariant.types import DecimalValue, Integer, String


def is_cacheable(value: Any) -> bool:
    """Check if a value belongs to the Cacheable Type Universe.

    This is the authoritative predicate for determining whether a value
    can be used in manifests, stored as artifacts, or passed between nodes.
    It recursively validates containers to ensure all nested values are cacheable.

    Args:
        value: The value to check.

    Returns:
        True if the value is cacheable, False otherwise.

    Examples:
        >>> is_cacheable(42)
        True
        >>> is_cacheable("hello")
        True
        >>> is_cacheable(3.14)  # float is forbidden
        False
        >>> is_cacheable(Integer(42))
        True
        >>> is_cacheable({"a": 1, "b": 2})
        True
        >>> is_cacheable([1, 2, 3])
        True
        >>> is_cacheable({"a": 1.5})  # nested float is forbidden
        False
    """
    # None is cacheable
    if value is None:
        return True

    # ICacheable implementors are always cacheable
    if isinstance(value, ICacheable):
        return True

    # Primitives: int, str, bool
    if isinstance(value, (int, str, bool)):
        return True

    # Decimal is cacheable (safe numeric, unlike float)
    if isinstance(value, Decimal):
        return True

    # FORBIDDEN: float (IEEE 754 non-determinism)
    if isinstance(value, float):
        return False

    # FORBIDDEN: bytes
    if isinstance(value, bytes):
        return False

    # Containers: dict with string keys
    if isinstance(value, Mapping):
        if not isinstance(value, dict):
            # Only plain dict is allowed, not arbitrary Mapping
            return False
        # All keys must be strings
        for key in value.keys():
            if not isinstance(key, str):
                return False
        # All values must be cacheable (recursive)
        for val in value.values():
            if not is_cacheable(val):
                return False
        return True

    # Containers: list, tuple
    if isinstance(value, Sequence) and not isinstance(value, str):
        # All elements must be cacheable (recursive)
        for item in value:
            if not is_cacheable(item):
                return False
        return True

    # Everything else is forbidden
    return False


def to_cacheable(value: Any) -> ICacheable:
    """Wrap a native cacheable value into its ICacheable form for storage.

    This function converts native types (int, str, Decimal) into their
    corresponding ICacheable wrappers (Integer, String, DecimalValue).
    ICacheable values are passed through unchanged.

    Args:
        value: The value to wrap. Must be cacheable (use is_cacheable first).

    Returns:
        An ICacheable object suitable for storage in ArtifactStore.

    Raises:
        TypeError: If value is not cacheable.
        NotImplementedError: If value is a container (dict/list/tuple).
            Container wrapping will be implemented when ListArtifact/DictArtifact
            types are added.

    Examples:
        >>> to_cacheable(42)
        Integer(42)
        >>> to_cacheable("hello")
        String('hello')
        >>> to_cacheable(Decimal("3.14"))
        DecimalValue('3.14')
        >>> to_cacheable(Integer(42))
        Integer(42)  # passed through unchanged
    """
    # Already ICacheable - pass through
    if isinstance(value, ICacheable):
        return value

    # Wrap primitives
    # Check bool before int since bool is a subclass of int in Python
    if isinstance(value, bool):
        return Integer(int(value))

    if isinstance(value, int):
        return Integer(value)

    if isinstance(value, str):
        return String(value)

    if isinstance(value, Decimal):
        return DecimalValue(value)

    if value is None:
        # None is cacheable but we need an ICacheable representation
        # For now, we could use a special NoneArtifact, but that's not implemented.
        # Let's raise NotImplementedError for now.
        raise NotImplementedError("None values are cacheable but not yet wrappable")

    # Containers - not yet implemented
    if isinstance(value, (dict, list, tuple)):
        raise NotImplementedError(
            f"Container types ({type(value).__name__}) are cacheable but not yet "
            "wrappable. ListArtifact/DictArtifact types need to be implemented."
        )

    # Not cacheable
    raise TypeError(
        f"Cannot convert {type(value).__name__} to ICacheable. "
        f"Value must be cacheable (use is_cacheable() to check)."
    )
