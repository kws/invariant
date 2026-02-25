"""Pytest configuration and fixtures."""

import pytest

from invariant.registry import OpRegistry
from invariant.store.memory import MemoryStore
from invariant.store.null import NullStore


@pytest.fixture
def registry():
    """Create a fresh OpRegistry instance."""
    registry = OpRegistry()
    registry.clear()
    return registry


@pytest.fixture
def store():
    """Create a NullStore for execution correctness tests (no caching)."""
    return NullStore()


@pytest.fixture
def caching_store():
    """Create an unbounded MemoryStore for tests that verify cache behavior."""
    return MemoryStore(cache="unbounded")
