"""Base class for ArtifactStore implementations."""

from abc import ABC, abstractmethod

from invariant.protocol import ICacheable


class ArtifactStore(ABC):
    """Abstract base class for artifact storage.

    Provides the interface for storing and retrieving immutable artifacts
    by their digest (SHA-256 hash).
    """

    @abstractmethod
    def exists(self, digest: str) -> bool:
        """Check if an artifact exists for the given digest.

        Args:
            digest: The SHA-256 hash (64 character hex string) of the artifact.

        Returns:
            True if artifact exists, False otherwise.
        """
        ...

    @abstractmethod
    def get(self, digest: str) -> ICacheable:
        """Retrieve an artifact by digest.

        Args:
            digest: The SHA-256 hash (64 character hex string) of the artifact.

        Returns:
            The deserialized ICacheable artifact.

        Raises:
            KeyError: If artifact does not exist.
        """
        ...

    @abstractmethod
    def put(self, digest: str, artifact: ICacheable) -> None:
        """Store an artifact with the given digest.

        Args:
            digest: The SHA-256 hash (64 character hex string) of the artifact.
            artifact: The ICacheable artifact to store.
        """
        ...
