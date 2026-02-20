"""Base class for ArtifactStore implementations."""

from abc import ABC, abstractmethod
from typing import Any


class ArtifactStore(ABC):
    """Abstract base class for artifact storage.

    Provides the interface for storing and retrieving immutable artifacts
    by operation name and digest (SHA-256 hash). The composite key ensures
    that different operations with the same input manifest cache separately.
    """

    @abstractmethod
    def exists(self, op_name: str, digest: str) -> bool:
        """Check if an artifact exists for the given operation and digest.

        Args:
            op_name: The name of the operation that produced the artifact.
            digest: The SHA-256 hash (64 character hex string) of the manifest.

        Returns:
            True if artifact exists, False otherwise.
        """
        ...

    @abstractmethod
    def get(self, op_name: str, digest: str) -> Any:
        """Retrieve an artifact by operation name and digest.

        Args:
            op_name: The name of the operation that produced the artifact.
            digest: The SHA-256 hash (64 character hex string) of the manifest.

        Returns:
            The deserialized artifact (native type or ICacheable domain type).

        Raises:
            KeyError: If artifact does not exist.
        """
        ...

    @abstractmethod
    def put(self, op_name: str, digest: str, artifact: Any) -> None:
        """Store an artifact with the given operation name and digest.

        Args:
            op_name: The name of the operation that produced the artifact.
            digest: The SHA-256 hash (64 character hex string) of the manifest.
            artifact: The artifact to store (must be cacheable).
        """
        ...
