"""ICacheable Protocol definition."""

from typing import BinaryIO, Protocol, runtime_checkable


@runtime_checkable
class ICacheable(Protocol):
    """Protocol for all cacheable data types.
    
    All data passed between Nodes must implement this protocol to ensure
    valid Manifest construction and artifact storage.
    """

    def get_stable_hash(self) -> str:
        """Returns a deterministic SHA-256 hash of the object's structural state.
        
        This represents the 'Identity' of the data. The hash must be:
        - Deterministic: Same inputs always produce same hash
        - Stable: Hash doesn't change across serialization/deserialization
        - Collision-resistant: Different inputs should produce different hashes
        
        Returns:
            A hexadecimal SHA-256 hash string (64 characters).
        """
        ...

    def to_stream(self, stream: BinaryIO) -> None:
        """Serializes the object to a binary stream for persistent storage.
        
        Args:
            stream: A binary I/O stream to write the serialized data to.
            
        The serialization format must be deterministic and allow for
        complete reconstruction via from_stream.
        """
        ...

    @classmethod
    def from_stream(cls, stream: BinaryIO) -> "ICacheable":
        """Hydrates the object from a binary stream.
        
        Args:
            stream: A binary I/O stream to read the serialized data from.
            
        Returns:
            An instance of the class with state restored from the stream.
            
        This must be the inverse operation of to_stream.
        """
        ...

