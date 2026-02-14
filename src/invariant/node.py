"""Node class representing a vertex in the DAG."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Node:
    """A vertex in the DAG defining what operation to perform.
    
    Attributes:
        op_name: The name of the operation to execute (must be registered).
        params: Static parameters for this node (dict of parameter name -> value).
        deps: List of node IDs that this node depends on (upstream dependencies).
    """
    
    op_name: str
    params: dict[str, Any]
    deps: list[str]
    
    def __post_init__(self) -> None:
        """Validate node configuration."""
        if not self.op_name:
            raise ValueError("op_name cannot be empty")
        if not isinstance(self.params, dict):
            raise ValueError("params must be a dictionary")
        if not isinstance(self.deps, list):
            raise ValueError("deps must be a list")

