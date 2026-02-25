"""MemoryStore: In-memory artifact storage for testing."""

import math
from collections.abc import MutableMapping
from typing import Any, Literal

from cachetools import LFUCache, LRUCache

from invariant.cacheable import is_cacheable
from invariant.store.base import ArtifactStore

CachePolicy = Literal["unbounded", "lru", "lfu"]


def _create_cache(
    max_size: int,
    cache: Literal["lru", "lfu"],
) -> MutableMapping[str, Any]:
    """Create a cachetools cache."""
    if cache == "lfu":
        return LFUCache(maxsize=max_size)
    return LRUCache(maxsize=max_size)


class MemoryStore(ArtifactStore):
    """In-memory artifact store using a dictionary or cachetools cache.

    Fast and ephemeral - suitable for testing. Artifacts are lost when
    the store instance is destroyed.

    Default is cache="lru" with max_size=1000 (safe bounded). Use
    cache="unbounded" for explicit unbounded. Use cache="lfu" for
    least-frequently-used eviction (e.g. graphics pipelines).
    """

    def __init__(
        self,
        cache: CachePolicy | MutableMapping[str, Any] = "lru",
        max_size: int | None = None,
    ) -> None:
        """Initialize memory store.

        Args:
            cache: "unbounded" (plain dict), "lru", "lfu", or a MutableMapping
                instance (e.g. cachetools.TTLCache). Default "lru".
            max_size: Maximum number of artifacts. Default 1000 when cache is
                "lru" or "lfu". Ignored for "unbounded". Must be None for
                cache instance.

        Raises:
            ValueError: Invalid combination of cache and max_size.
        """
        super().__init__()

        # Cache instance provided: use it, max_size forbidden
        if isinstance(cache, MutableMapping):
            if max_size is not None:
                raise ValueError(
                    "max_size must not be set when cache is a cache instance"
                )
            self._artifacts: dict[str, Any] | MutableMapping[str, Any] = cache
            return

        # Unbounded: plain dict
        if cache == "unbounded":
            self._artifacts = {}
            return

        # LRU or LFU: validate max_size, use default 1000 if None
        if cache in ("lru", "lfu"):
            size = max_size if max_size is not None else 1000
            if size < 1:
                raise ValueError("max_size must be at least 1")
            if size == math.inf or (isinstance(size, float) and math.isinf(size)):
                raise ValueError("max_size cannot be infinity")
            self._artifacts = _create_cache(size, cache)
            return

        raise ValueError(
            f"cache must be 'unbounded', 'lru', 'lfu', or a MutableMapping; got {cache!r}"
        )

    def _make_key(self, op_name: str, digest: str) -> str:
        """Create a composite key from op_name and digest."""
        return f"{op_name}:{digest}"

    def exists(self, op_name: str, digest: str) -> bool:
        """Check if an artifact exists."""
        key = self._make_key(op_name, digest)
        exists = key in self._artifacts
        if exists:
            self.stats.hits += 1
        else:
            self.stats.misses += 1
        return exists

    def get(self, op_name: str, digest: str) -> Any:
        """Retrieve an artifact by operation name and digest.

        Raises:
            KeyError: If artifact does not exist.
        """
        key = self._make_key(op_name, digest)
        if key not in self._artifacts:
            raise KeyError(
                f"Artifact with op_name '{op_name}' and digest '{digest}' not found"
            )

        # Return stored object directly (no deserialization needed)
        return self._artifacts[key]

    def put(self, op_name: str, digest: str, artifact: Any) -> None:
        """Store an artifact with the given operation name and digest."""
        # Validate artifact is cacheable
        if not is_cacheable(artifact):
            raise TypeError(
                f"Artifact is not cacheable: {type(artifact)}. "
                f"Use is_cacheable() to check values before storing."
            )

        # Store object directly (no serialization needed - relies on immutability contract)
        key = self._make_key(op_name, digest)
        self._artifacts[key] = artifact
        self.stats.puts += 1

    def clear(self) -> None:
        """Clear all artifacts (mainly for testing)."""
        self._artifacts.clear()
        self.reset_stats()
