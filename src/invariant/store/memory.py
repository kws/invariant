"""MemoryStore: In-memory artifact storage for testing."""

from typing import Any

from invariant.cacheable import is_cacheable
from invariant.store.base import ArtifactStore
from invariant.store.codec import deserialize, serialize


class MemoryStore(ArtifactStore):
    """In-memory artifact store using a dictionary.

    Fast and ephemeral - suitable for testing. Artifacts are lost when
    the store instance is destroyed.
    """

    def __init__(self) -> None:
        """Initialize an empty memory store."""
        self._artifacts: dict[str, bytes] = {}

    def _make_key(self, op_name: str, digest: str) -> str:
        """Create a composite key from op_name and digest."""
        return f"{op_name}:{digest}"

    def exists(self, op_name: str, digest: str) -> bool:
        """Check if an artifact exists."""
        key = self._make_key(op_name, digest)
        return key in self._artifacts

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

        # Deserialize from stored bytes
        data = self._artifacts[key]
        return deserialize(data)

    def put(self, op_name: str, digest: str, artifact: Any) -> None:
        """Store an artifact with the given operation name and digest."""
        # Validate artifact is cacheable
        if not is_cacheable(artifact):
            raise TypeError(
                f"Artifact is not cacheable: {type(artifact)}. "
                f"Use is_cacheable() to check values before storing."
            )

        # Serialize using codec
        serialized_data = serialize(artifact)

        key = self._make_key(op_name, digest)
        self._artifacts[key] = serialized_data

    def clear(self) -> None:
        """Clear all artifacts (mainly for testing)."""
        self._artifacts.clear()
