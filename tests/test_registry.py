"""Tests for OpRegistry."""

import pytest

from invariant.protocol import ICacheable
from invariant.registry import OpRegistry
from invariant.types import String


def test_singleton():
    """Test that OpRegistry is a singleton."""
    r1 = OpRegistry()
    r2 = OpRegistry()
    assert r1 is r2


def test_register_and_get(registry):
    """Test registering and getting an operation."""

    def test_op(manifest: dict) -> ICacheable:
        return String("result")

    registry.register("test_op", test_op)
    assert registry.has("test_op")
    retrieved = registry.get("test_op")
    assert retrieved is test_op


def test_register_empty_name(registry):
    """Test that registering with empty name raises ValueError."""

    def test_op(manifest: dict) -> ICacheable:
        return String("result")

    with pytest.raises(ValueError, match="cannot be empty"):
        registry.register("", test_op)


def test_register_duplicate(registry):
    """Test that registering duplicate name raises ValueError."""

    def test_op(manifest: dict) -> ICacheable:
        return String("result")

    registry.register("test_op", test_op)
    with pytest.raises(ValueError, match="already registered"):
        registry.register("test_op", test_op)


def test_get_unregistered(registry):
    """Test that getting unregistered op raises KeyError."""
    with pytest.raises(KeyError, match="not registered"):
        registry.get("unknown_op")


def test_has(registry):
    """Test has method."""

    def test_op(manifest: dict) -> ICacheable:
        return String("result")

    assert not registry.has("test_op")
    registry.register("test_op", test_op)
    assert registry.has("test_op")


def test_clear(registry):
    """Test clear method."""

    def test_op(manifest: dict) -> ICacheable:
        return String("result")

    registry.register("test_op", test_op)
    assert registry.has("test_op")
    registry.clear()
    assert not registry.has("test_op")
