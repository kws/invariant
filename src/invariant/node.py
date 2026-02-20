"""Node class representing a vertex in the DAG."""

from dataclasses import dataclass
from typing import Any

from invariant.params import ref


@dataclass(frozen=True)
class Node:
    """A vertex in the DAG defining what operation to perform.

    Attributes:
        op_name: The name of the operation to execute (must be registered).
        params: Static parameters for this node (dict of parameter name -> value).
                May contain ref() and cel() markers, and ${...} string interpolation.
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

        # Validate that all ref() markers reference declared dependencies
        self._validate_refs()

    def _validate_refs(self) -> None:
        """Validate that all ref() markers in params reference declared dependencies."""
        deps_set = set(self.deps)
        refs = self._collect_refs(self.params)

        for ref_marker in refs:
            if ref_marker.dep not in deps_set:
                raise ValueError(
                    f"ref('{ref_marker.dep}') in params references undeclared dependency. "
                    f"Declared deps: {self.deps}. "
                    f"Add '{ref_marker.dep}' to deps list."
                )

    def _collect_refs(self, value: Any) -> list[ref]:
        """Recursively collect all ref() markers from a value."""
        refs: list[ref] = []
        if isinstance(value, ref):
            refs.append(value)
        elif isinstance(value, dict):
            for v in value.values():
                refs.extend(self._collect_refs(v))
        elif isinstance(value, list):
            for item in value:
                refs.extend(self._collect_refs(item))
        return refs
