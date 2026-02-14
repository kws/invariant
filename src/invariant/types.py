"""Basic cacheable types implementing ICacheable protocol."""

from decimal import Decimal
from io import BytesIO
from typing import BinaryIO

from invariant.protocol import ICacheable


class String(ICacheable):
    """A cacheable string type."""

    def __init__(self, value: str) -> None:
        """Initialize with a string value.
        
        Args:
            value: The string value to wrap.
        """
        self.value = value

    def get_stable_hash(self) -> str:
        """Return SHA-256 hash of the string value."""
        import hashlib
        return hashlib.sha256(self.value.encode("utf-8")).hexdigest()

    def to_stream(self, stream: BinaryIO) -> None:
        """Serialize string to stream."""
        data = self.value.encode("utf-8")
        stream.write(len(data).to_bytes(8, byteorder="big"))
        stream.write(data)

    @classmethod
    def from_stream(cls, stream: BinaryIO) -> "String":
        """Deserialize string from stream."""
        length = int.from_bytes(stream.read(8), byteorder="big")
        data = stream.read(length)
        return cls(data.decode("utf-8"))

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if not isinstance(other, String):
            return False
        return self.value == other.value

    def __repr__(self) -> str:
        """String representation."""
        return f"String({self.value!r})"


class Integer(ICacheable):
    """A cacheable integer type."""

    def __init__(self, value: int) -> None:
        """Initialize with an integer value.
        
        Args:
            value: The integer value to wrap.
        """
        self.value = value

    def get_stable_hash(self) -> str:
        """Return SHA-256 hash of the integer value."""
        import hashlib
        return hashlib.sha256(str(self.value).encode("utf-8")).hexdigest()

    def to_stream(self, stream: BinaryIO) -> None:
        """Serialize integer to stream."""
        stream.write(self.value.to_bytes(8, byteorder="big", signed=True))

    @classmethod
    def from_stream(cls, stream: BinaryIO) -> "Integer":
        """Deserialize integer from stream."""
        value = int.from_bytes(stream.read(8), byteorder="big", signed=True)
        return cls(value)

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if not isinstance(other, Integer):
            return False
        return self.value == other.value

    def __repr__(self) -> str:
        """String representation."""
        return f"Integer({self.value})"


class DecimalValue(ICacheable):
    """A cacheable Decimal type.
    
    Decimal values are canonicalized to string representation for hashing
    to ensure determinism across architectures.
    """

    def __init__(self, value: Decimal | str | int | float) -> None:
        """Initialize with a Decimal value.
        
        Args:
            value: The value to convert to Decimal. Can be Decimal, string,
                  int, or float (though float is discouraged per architecture).
        """
        if isinstance(value, Decimal):
            self.value = value
        else:
            self.value = Decimal(str(value))

    def get_stable_hash(self) -> str:
        """Return SHA-256 hash of canonicalized Decimal string.
        
        The Decimal is canonicalized to string representation to ensure
        deterministic hashing across different architectures.
        """
        import hashlib
        # Canonicalize to string for deterministic hashing
        canonical = str(self.value)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_stream(self, stream: BinaryIO) -> None:
        """Serialize Decimal to stream."""
        # Store as canonical string representation
        data = str(self.value).encode("utf-8")
        stream.write(len(data).to_bytes(8, byteorder="big"))
        stream.write(data)

    @classmethod
    def from_stream(cls, stream: BinaryIO) -> "DecimalValue":
        """Deserialize Decimal from stream."""
        length = int.from_bytes(stream.read(8), byteorder="big")
        data = stream.read(length)
        return cls(Decimal(data.decode("utf-8")))

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if not isinstance(other, DecimalValue):
            return False
        return self.value == other.value

    def __repr__(self) -> str:
        """String representation."""
        return f"DecimalValue({self.value})"

