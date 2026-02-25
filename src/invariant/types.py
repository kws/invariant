"""Domain types implementing ICacheable protocol.

Native types (int, str, Decimal, dict, list) are supported directly without wrappers.
Only domain types that require custom serialization implement ICacheable.
"""

import hashlib
from typing import BinaryIO

from invariant.protocol import ICacheable


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

    def to_json_value(self) -> dict:
        """Return JSON-serializable dict for graph serialization (IJsonRepresentable)."""
        return {"coefficients": list(self.coefficients)}

    @classmethod
    def from_json_value(cls, obj: dict) -> "Polynomial":
        """Reconstruct from JSON dict (IJsonRepresentable)."""
        if "coefficients" not in obj:
            raise ValueError("Polynomial from_json_value requires 'coefficients' key")
        return cls(obj["coefficients"])
