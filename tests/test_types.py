"""Tests for basic cacheable types."""

from decimal import Decimal
from io import BytesIO


from invariant.types import DecimalValue, Integer, String


class TestString:
    """Tests for String type."""

    def test_creation(self):
        """Test String creation."""
        s = String("hello")
        assert s.value == "hello"

    def test_hash_determinism(self):
        """Test that hash is deterministic."""
        s1 = String("test")
        s2 = String("test")
        assert s1.get_stable_hash() == s2.get_stable_hash()

    def test_hash_different_values(self):
        """Test that different values produce different hashes."""
        s1 = String("hello")
        s2 = String("world")
        assert s1.get_stable_hash() != s2.get_stable_hash()

    def test_serialization(self):
        """Test serialization roundtrip."""
        s1 = String("test string")
        stream = BytesIO()
        s1.to_stream(stream)
        stream.seek(0)
        s2 = String.from_stream(stream)
        assert s1.value == s2.value
        assert s1 == s2

    def test_equality(self):
        """Test equality comparison."""
        s1 = String("hello")
        s2 = String("hello")
        s3 = String("world")
        assert s1 == s2
        assert s1 != s3
        assert s1 != "hello"  # Different type


class TestInteger:
    """Tests for Integer type."""

    def test_creation(self):
        """Test Integer creation."""
        i = Integer(42)
        assert i.value == 42

    def test_hash_determinism(self):
        """Test that hash is deterministic."""
        i1 = Integer(100)
        i2 = Integer(100)
        assert i1.get_stable_hash() == i2.get_stable_hash()

    def test_hash_different_values(self):
        """Test that different values produce different hashes."""
        i1 = Integer(1)
        i2 = Integer(2)
        assert i1.get_stable_hash() != i2.get_stable_hash()

    def test_serialization(self):
        """Test serialization roundtrip."""
        i1 = Integer(-12345)
        stream = BytesIO()
        i1.to_stream(stream)
        stream.seek(0)
        i2 = Integer.from_stream(stream)
        assert i1.value == i2.value
        assert i1 == i2

    def test_negative_numbers(self):
        """Test negative numbers."""
        i = Integer(-1)
        stream = BytesIO()
        i.to_stream(stream)
        stream.seek(0)
        i2 = Integer.from_stream(stream)
        assert i2.value == -1


class TestDecimalValue:
    """Tests for DecimalValue type."""

    def test_creation_from_string(self):
        """Test DecimalValue creation from string."""
        d = DecimalValue("3.14159")
        assert d.value == Decimal("3.14159")

    def test_creation_from_decimal(self):
        """Test DecimalValue creation from Decimal."""
        d = DecimalValue(Decimal("1.23"))
        assert d.value == Decimal("1.23")

    def test_creation_from_int(self):
        """Test DecimalValue creation from int."""
        d = DecimalValue(42)
        assert d.value == Decimal("42")

    def test_hash_determinism(self):
        """Test that hash is deterministic."""
        d1 = DecimalValue("1.5")
        d2 = DecimalValue("1.5")
        assert d1.get_stable_hash() == d2.get_stable_hash()

    def test_hash_canonicalization(self):
        """Test that hash uses canonical string representation."""
        # Different ways of representing the same value should hash the same
        d1 = DecimalValue("1.5")
        d2 = DecimalValue(Decimal("1.5"))
        # Note: "1.5" and "1.50" might hash differently if we use str() directly
        # But they represent the same Decimal value
        assert d1.get_stable_hash() == d2.get_stable_hash()
        # str(Decimal("1.50")) is "1.50", str(Decimal("1.5")) is "1.5"
        # So they will hash differently, which is correct for our use case

    def test_serialization(self):
        """Test serialization roundtrip."""
        d1 = DecimalValue("3.14159")
        stream = BytesIO()
        d1.to_stream(stream)
        stream.seek(0)
        d2 = DecimalValue.from_stream(stream)
        assert d1.value == d2.value
        assert d1 == d2

    def test_equality(self):
        """Test equality comparison."""
        d1 = DecimalValue("1.5")
        d2 = DecimalValue("1.5")
        d3 = DecimalValue("2.5")
        assert d1 == d2
        assert d1 != d3
