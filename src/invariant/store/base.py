"""Base class for ArtifactStore implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheStats:
    """Cache statistics tracking hits, misses, and puts."""

    hits: int = 0  # exists() returned True
    misses: int = 0  # exists() returned False
    puts: int = 0  # put() was called


class ArtifactStore(ABC):
    """Abstract base class for artifact storage.

    Provides the interface for storing and retrieving immutable artifacts
    by operation name and digest (SHA-256 hash). The composite key ensures
    that different operations with the same input manifest cache separately.
    """

    def __init__(self) -> None:
        """Initialize the store with cache statistics."""
        self.stats = CacheStats()

    def reset_stats(self) -> None:
        """Reset cache statistics to zero."""
        self.stats = CacheStats()

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
