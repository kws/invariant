"""Cacheable type boundary: the single source of truth for allowed types.

This module defines the Cacheable Type Universe and provides the core function
that validates values throughout the Invariant system.

The Allowed Types (recursive for containers):
  - int, str, bool, None
  - Decimal (safe numerics — no float!)
  - dict[str, CacheableValue]  (string keys only)
  - list[CacheableValue], tuple[CacheableValue, ...]
  - Any ICacheable implementor (domain types like Polynomial)

FORBIDDEN: float (IEEE 754 non-determinism), bytes, arbitrary objects

Native types are stored directly without wrapping. The store codec handles
serialization of all cacheable types uniformly.
"""

from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from invariant.protocol import ICacheable


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
