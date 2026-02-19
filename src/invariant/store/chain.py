"""ChainStore: Composite artifact store chaining MemoryStore and DiskStore."""

from invariant.protocol import ICacheable
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
        self.l1 = l1 or MemoryStore()
        self.l2 = l2 or DiskStore()

    def exists(self, digest: str) -> bool:
        """Check if an artifact exists in L1 or L2.

        Args:
            digest: The SHA-256 hash (64 character hex string) of the artifact.

        Returns:
            True if artifact exists in either store, False otherwise.
        """
        # Check L1 first (fast path)
        if self.l1.exists(digest):
            return True
        # Check L2 (slower, but persistent)
        return self.l2.exists(digest)

    def get(self, digest: str) -> ICacheable:
        """Retrieve an artifact from L1 or L2.

        If found in L2 but not L1, promotes the artifact to L1 for faster
        subsequent access.

        Args:
            digest: The SHA-256 hash (64 character hex string) of the artifact.

        Returns:
            The deserialized ICacheable artifact.

        Raises:
            KeyError: If artifact does not exist in either store.
        """
        # Try L1 first (fast path)
        if self.l1.exists(digest):
            return self.l1.get(digest)

        # Try L2 (slower, but persistent)
        if self.l2.exists(digest):
            # Promote to L1 for faster subsequent access
            artifact = self.l2.get(digest)
            self.l1.put(digest, artifact)
            return artifact

        # Not found in either store
        raise KeyError(f"Artifact with digest '{digest}' not found in L1 or L2")

    def put(self, digest: str, artifact: ICacheable) -> None:
        """Store an artifact in both L1 and L2.

        Args:
            digest: The SHA-256 hash (64 character hex string) of the artifact.
            artifact: The ICacheable artifact to store.
        """
        # Write to both stores
        self.l1.put(digest, artifact)
        self.l2.put(digest, artifact)
