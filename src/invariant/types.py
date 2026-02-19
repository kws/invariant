"""Basic cacheable types implementing ICacheable protocol."""

import hashlib
from decimal import Decimal
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


class Polynomial(ICacheable):
    """A cacheable polynomial type.

    Represents a polynomial as a tuple of integer coefficients, where the index
    represents the degree (coefficient at index i is the coefficient of x^i).

    Canonical form: Trailing zeros are stripped to ensure a unique representation.
    For example, [1, 2, 0, 0] is canonicalized to [1, 2].
    """

    def __init__(self, coefficients: tuple[int, ...] | list[int]) -> None:
        """Initialize with coefficient list.

        Args:
            coefficients: List or tuple of integer coefficients. Index i represents
                         the coefficient of x^i. Trailing zeros are automatically
                         stripped for canonical form.
        """
        # Convert to tuple and strip trailing zeros for canonical form
        coeffs = tuple(coefficients)
        # Strip trailing zeros
        while len(coeffs) > 0 and coeffs[-1] == 0:
            coeffs = coeffs[:-1]
        # If all zeros, keep at least one zero
        if len(coeffs) == 0:
            coeffs = (0,)
        self.coefficients = coeffs

    def get_stable_hash(self) -> str:
        """Return SHA-256 hash of the canonical coefficient tuple."""
        # Hash the canonical coefficient tuple
        coeff_bytes = b",".join(str(c).encode("utf-8") for c in self.coefficients)
        return hashlib.sha256(coeff_bytes).hexdigest()

    def to_stream(self, stream: BinaryIO) -> None:
        """Serialize polynomial to stream.

        Format: length-prefixed sequence of 8-byte signed integers (big-endian).
        """
        # Write length (number of coefficients)
        stream.write(len(self.coefficients).to_bytes(8, byteorder="big", signed=False))
        # Write each coefficient as 8-byte signed big-endian integer
        for coeff in self.coefficients:
            stream.write(coeff.to_bytes(8, byteorder="big", signed=True))

    @classmethod
    def from_stream(cls, stream: BinaryIO) -> "Polynomial":
        """Deserialize polynomial from stream.

        Reads length-prefixed sequence of 8-byte signed integers and strips
        trailing zeros for canonical form.
        """
        # Read length
        length = int.from_bytes(stream.read(8), byteorder="big", signed=False)
        # Read coefficients
        coefficients = []
        for _ in range(length):
            coeff = int.from_bytes(stream.read(8), byteorder="big", signed=True)
            coefficients.append(coeff)
        # Create polynomial (constructor will strip trailing zeros)
        return cls(tuple(coefficients))

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if not isinstance(other, Polynomial):
            return False
        return self.coefficients == other.coefficients

    def __repr__(self) -> str:
        """String representation."""
        return f"Polynomial({list(self.coefficients)})"
