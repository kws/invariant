"""NullStore: No-op artifact store. Every operation executes; nothing is cached."""

from typing import Any

from invariant.store.base import ArtifactStore


class NullStore(ArtifactStore):
    """Store that never caches. exists() always returns False; put() is a no-op.

    Use for execution correctness tests where cache behavior is irrelevant.
    Stats are not updated (remains no-op).
    """

    def exists(self, op_name: str, digest: str) -> bool:
        """Always return False; nothing is ever cached."""
        return False

    def get(self, op_name: str, digest: str) -> Any:
        """Raise KeyError. Should never be called since exists() always returns False."""
        raise KeyError(
            f"Artifact with op_name '{op_name}' and digest '{digest}' not found"
        )

    def put(self, op_name: str, digest: str, artifact: Any) -> None:
        """No-op; nothing is stored."""
        pass
