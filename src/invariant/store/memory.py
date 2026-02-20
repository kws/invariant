"""MemoryStore: In-memory artifact storage for testing."""

from typing import Any

from invariant.cacheable import is_cacheable
from invariant.store.base import ArtifactStore


class MemoryStore(ArtifactStore):
    """In-memory artifact store using a dictionary.

    Fast and ephemeral - suitable for testing. Artifacts are lost when
    the store instance is destroyed.
    """

    def __init__(self) -> None:
        """Initialize an empty memory store."""
        super().__init__()
        self._artifacts: dict[str, Any] = {}

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
