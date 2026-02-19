"""Tests for OpRegistry."""

import types

import pytest

from invariant.protocol import ICacheable
from invariant.registry import OpPackage, OpRegistry
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


def test_register_package_with_dict(registry):
    """Test register_package with a dict."""

    def op1(manifest: dict) -> ICacheable:
        return String("op1")

    def op2(manifest: dict) -> ICacheable:
        return String("op2")

    ops: OpPackage = {
        "op1": op1,
        "op2": op2,
    }

    registry.register_package("test", ops)
    assert registry.has("test:op1")
    assert registry.has("test:op2")
    assert registry.get("test:op1") is op1
    assert registry.get("test:op2") is op2


def test_register_package_with_module(registry):
    """Test register_package with a module that has OPS attribute."""

    def op1(manifest: dict) -> ICacheable:
        return String("op1")

    def op2(manifest: dict) -> ICacheable:
        return String("op2")

    ops: OpPackage = {
        "op1": op1,
        "op2": op2,
    }

    # Create a mock module with OPS attribute
    module = types.ModuleType("test_module")
    module.OPS = ops

    registry.register_package("test", module)
    assert registry.has("test:op1")
    assert registry.has("test:op2")
    assert registry.get("test:op1") is op1
    assert registry.get("test:op2") is op2


def test_register_package_empty_prefix(registry):
    """Test that register_package raises ValueError for empty prefix."""

    ops: OpPackage = {"op1": lambda m: String("result")}

    with pytest.raises(ValueError, match="cannot be empty"):
        registry.register_package("", ops)


def test_register_package_invalid_ops_type(registry):
    """Test that register_package raises ValueError for invalid ops type."""

    with pytest.raises(ValueError, match="must be a dict or module"):
        registry.register_package("test", "not a dict or module")


def test_register_package_module_without_ops(registry):
    """Test that register_package raises AttributeError for module without OPS."""

    module = types.ModuleType("test_module")
    # No OPS attribute

    with pytest.raises(AttributeError):
        registry.register_package("test", module)


def test_register_package_module_with_invalid_ops(registry):
    """Test that register_package raises ValueError if OPS is not a dict."""

    module = types.ModuleType("test_module")
    module.OPS = "not a dict"

    with pytest.raises(ValueError, match="OPS attribute must be a dict"):
        registry.register_package("test", module)


def test_register_package_duplicate_name(registry):
    """Test that register_package raises ValueError for duplicate op names."""

    def op1(manifest: dict) -> ICacheable:
        return String("op1")

    ops: OpPackage = {"op1": op1}

    registry.register_package("test", ops)
    # Try to register the same op name again
    with pytest.raises(ValueError, match="already registered"):
        registry.register("test:op1", op1)


def test_auto_discover(registry):
    """Test auto_discover finds and registers op packages from entry points."""

    # auto_discover should find the poly and stdlib packages
    registry.auto_discover()

    # Check that poly ops are registered
    assert registry.has("poly:from_coefficients")
    assert registry.has("poly:add")
    assert registry.has("poly:multiply")
    assert registry.has("poly:evaluate")
    assert registry.has("poly:derivative")

    # Check that stdlib ops are registered
    assert registry.has("stdlib:identity")
    assert registry.has("stdlib:add")
    assert registry.has("stdlib:multiply")
    assert registry.has("stdlib:from_integer")


def test_auto_discover_idempotent(registry):
    """Test that auto_discover can be called multiple times safely."""

    registry.auto_discover()
    # Should not raise errors on second call
    registry.auto_discover()

    # Operations should still be registered
    assert registry.has("poly:from_coefficients")
    assert registry.has("stdlib:identity")
