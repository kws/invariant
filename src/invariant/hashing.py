"""Recursive hashing utilities for manifests and cacheable objects."""

import hashlib
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from invariant.protocol import ICacheable


def hash_value(value: Any) -> str:
    """Recursively hash a value to produce a deterministic SHA-256 hash.

    Supports:
    - ICacheable objects: Uses their get_stable_hash() method
    - dict/Mapping: Sorts keys, recursively hashes values
    - list/Sequence: Recursively hashes each element
    - int, str: Direct hashing
    - Decimal: Canonicalized to string then hashed
    - None: Special hash value

    Args:
        value: The value to hash. Can be any of the supported types.

    Returns:
        A hexadecimal SHA-256 hash string (64 characters).

    Raises:
        TypeError: If value type is not supported.
    """
    if value is None:
        return hashlib.sha256(b"None").hexdigest()

    if isinstance(value, ICacheable):
        return value.get_stable_hash()

    if isinstance(value, str):
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    if isinstance(value, int):
        return hashlib.sha256(str(value).encode("utf-8")).hexdigest()

    if isinstance(value, Decimal):
        # Canonicalize to string for deterministic hashing
        canonical = str(value)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    if isinstance(value, Mapping):
        # Sort keys for canonical ordering
        sorted_items = sorted(value.items(), key=lambda x: x[0])
        hasher = hashlib.sha256()
        for key, val in sorted_items:
            # Hash key
            key_hash = hash_value(key)
            hasher.update(key_hash.encode("utf-8"))
            # Hash value
            val_hash = hash_value(val)
            hasher.update(val_hash.encode("utf-8"))
        return hasher.hexdigest()

    if isinstance(value, Sequence) and not isinstance(value, str):
        # Hash each element in order
        hasher = hashlib.sha256()
        for item in value:
            item_hash = hash_value(item)
            hasher.update(item_hash.encode("utf-8"))
        return hasher.hexdigest()

    raise TypeError(
        f"Unsupported type for hashing: {type(value).__name__}. "
        f"Value must be ICacheable, dict, list, str, int, Decimal, or None."
    )


def hash_manifest(manifest: dict[str, Any]) -> str:
    """Hash a manifest dictionary to produce a Digest.

    A manifest is a dictionary mapping input names to values. The hash is
    computed by:
    1. Sorting keys for canonical ordering
    2. Recursively hashing each value
    3. Combining into a single SHA-256 hash

    Args:
        manifest: The manifest dictionary to hash. Keys should be strings,
                 values can be ICacheable, dict, list, or primitives.

    Returns:
        A hexadecimal SHA-256 hash string (64 characters) representing
        the Digest (cache key) for this manifest.
    """
    # Sort keys for canonical ordering
    sorted_items = sorted(manifest.items(), key=lambda x: x[0])

    hasher = hashlib.sha256()
    for key, value in sorted_items:
        # Hash key
        key_hash = hash_value(key)
        hasher.update(key_hash.encode("utf-8"))
        # Hash value
        value_hash = hash_value(value)
        hasher.update(value_hash.encode("utf-8"))

    return hasher.hexdigest()
