"""Invariant: A deterministic execution engine for DAGs."""

from invariant.executor import Executor
from invariant.node import Node
from invariant.registry import OpRegistry

__version__ = "0.1.0"

__all__ = ["Executor", "Node", "OpRegistry", "__version__"]
