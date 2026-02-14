"""Pytest configuration and fixtures."""

import pytest

from invariant.registry import OpRegistry
from invariant.store.memory import MemoryStore


@pytest.fixture
def registry():
    """Create a fresh OpRegistry instance."""
    registry = OpRegistry()
    registry.clear()
    return registry


@pytest.fixture
def store():
    """Create a fresh MemoryStore instance."""
    return MemoryStore()

