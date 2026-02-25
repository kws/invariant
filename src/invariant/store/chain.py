"""ChainStore: Composite artifact store chaining MemoryStore and DiskStore."""

from typing import Any

from invariant.store.base import ArtifactStore
from invariant.store.disk import DiskStore
from invariant.store.memory import MemoryStore


class ChainStore(ArtifactStore):
    """Composite artifact store that chains MemoryStore (L1) and DiskStore (L2).

    Provides a two-tier caching strategy:
    - L1 (MemoryStore): Fast, session-scoped cache checked first
    - L2 (DiskStore): Persistent filesystem cache checked if L1 misses

    On L2 hit, the artifact is promoted to L1 for faster subsequent access.
    On put, artifacts are written to both L1 and L2.
    """

    def __init__(
        self,
        l1: MemoryStore | None = None,
        l2: DiskStore | None = None,
    ) -> None:
        """Initialize ChainStore.

        Args:
            l1: MemoryStore instance for L1 cache. If None, creates a new one.
            l2: DiskStore instance for L2 cache. If None, creates a new one.
        """
        super().__init__()
        self.l1 = l1 or MemoryStore(cache="lru")
        self.l2 = l2 or DiskStore()

    def exists(self, op_name: str, digest: str) -> bool:
        """Check if an artifact exists in L1 or L2.

        Args:
            op_name: The name of the operation that produced the artifact.
            digest: The SHA-256 hash (64 character hex string) of the manifest.

        Returns:
            True if artifact exists in either store, False otherwise.
        """
        # Check L1 first (fast path)
        if self.l1.exists(op_name, digest):
            self.stats.hits += 1
            return True
        # Check L2 (slower, but persistent)
        if self.l2.exists(op_name, digest):
            self.stats.hits += 1
            return True
        self.stats.misses += 1
        return False

    def get(self, op_name: str, digest: str) -> Any:
        """Retrieve an artifact from L1 or L2.

        If found in L2 but not L1, promotes the artifact to L1 for faster
        subsequent access.

        Args:
            op_name: The name of the operation that produced the artifact.
            digest: The SHA-256 hash (64 character hex string) of the manifest.

        Returns:
            The deserialized artifact (native type or ICacheable domain type).

        Raises:
            KeyError: If artifact does not exist in either store.
        """
        # Try L1 first (fast path)
        if self.l1.exists(op_name, digest):
            return self.l1.get(op_name, digest)

        # Try L2 (slower, but persistent)
        if self.l2.exists(op_name, digest):
            # Promote to L1 for faster subsequent access
            artifact = self.l2.get(op_name, digest)
            self.l1.put(op_name, digest, artifact)
            return artifact

        # Not found in either store
        raise KeyError(
            f"Artifact with op_name '{op_name}' and digest '{digest}' not found in L1 or L2"
        )

    def put(self, op_name: str, digest: str, artifact: Any) -> None:
        """Store an artifact in both L1 and L2.

        Args:
            op_name: The name of the operation that produced the artifact.
            digest: The SHA-256 hash (64 character hex string) of the manifest.
            artifact: The artifact to store (must be cacheable).
        """
        # Write to both stores
        self.l1.put(op_name, digest, artifact)
        self.l2.put(op_name, digest, artifact)
        self.stats.puts += 1
