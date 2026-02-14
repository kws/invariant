"""GraphResolver for parsing, validating, and sorting DAGs."""

from collections import deque
from typing import TYPE_CHECKING

from invariant.node import Node

if TYPE_CHECKING:
    from invariant.registry import OpRegistry


class GraphResolver:
    """Responsible for parsing graph definitions and ensuring valid DAGs.

    Handles:
    - Cycle detection
    - Validation (missing dependencies, missing ops)
    - Topological sorting
    """

    def __init__(self, registry: "OpRegistry | None" = None) -> None:
        """Initialize GraphResolver.

        Args:
            registry: Optional OpRegistry for validating that ops exist.
                     If None, op validation is skipped.
        """
        self.registry = registry

    def validate(self, graph: dict[str, Node]) -> None:
        """Validate a graph definition.

        Checks:
        - All node dependencies exist in the graph
        - All referenced ops are registered (if registry provided)
        - No cycles exist

        Args:
            graph: Dictionary mapping node IDs to Node objects.

        Raises:
            ValueError: If validation fails (missing deps, missing ops, cycles).
        """
        # Check all dependencies exist
        node_ids = set(graph.keys())
        for node_id, node in graph.items():
            for dep in node.deps:
                if dep not in node_ids:
                    raise ValueError(
                        f"Node '{node_id}' has dependency '{dep}' that doesn't exist in graph"
                    )

        # Check all ops are registered (if registry provided)
        if self.registry:
            for node_id, node in graph.items():
                if not self.registry.has(node.op_name):
                    raise ValueError(
                        f"Node '{node_id}' references unregistered op '{node.op_name}'"
                    )

        # Check for cycles
        if self._has_cycle(graph):
            raise ValueError("Graph contains cycles")

    def _has_cycle(self, graph: dict[str, Node]) -> bool:
        """Detect cycles in the graph using DFS.

        Args:
            graph: Dictionary mapping node IDs to Node objects.

        Returns:
            True if cycle exists, False otherwise.
        """
        node_ids = set(graph.keys())
        WHITE = 0  # Unvisited
        GRAY = 1  # Currently in DFS path
        BLACK = 2  # Fully processed

        color: dict[str, int] = {node_id: WHITE for node_id in node_ids}

        def dfs(node_id: str) -> bool:
            """DFS helper that returns True if cycle found."""
            if color[node_id] == GRAY:
                # Back edge found - cycle detected
                return True
            if color[node_id] == BLACK:
                # Already processed
                return False

            color[node_id] = GRAY
            node = graph[node_id]
            for dep in node.deps:
                if dfs(dep):
                    return True

            color[node_id] = BLACK
            return False

        # Check all nodes (handles disconnected components)
        for node_id in node_ids:
            if color[node_id] == WHITE:
                if dfs(node_id):
                    return True

        return False

    def topological_sort(self, graph: dict[str, Node]) -> list[str]:
        """Topologically sort the graph using Kahn's algorithm.

        Args:
            graph: Dictionary mapping node IDs to Node objects.

        Returns:
            List of node IDs in topological order (dependencies before dependents).

        Raises:
            ValueError: If graph contains cycles.
        """
        node_ids = set(graph.keys())

        # Build reverse dependency map: which nodes depend on each node
        dependents: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
        for node_id, node in graph.items():
            for dep in node.deps:
                dependents[dep].append(node_id)

        # Calculate in-degree for each node (number of dependencies it has)
        in_degree: dict[str, int] = {}
        for node_id, node in graph.items():
            in_degree[node_id] = len(node.deps)

        # Find all nodes with in-degree 0 (no dependencies)
        queue = deque([node_id for node_id in node_ids if in_degree[node_id] == 0])
        result: list[str] = []

        while queue:
            node_id = queue.popleft()
            result.append(node_id)

            # Reduce in-degree of nodes that depend on this node
            for dependent in dependents[node_id]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # If we didn't process all nodes, there's a cycle
        if len(result) != len(node_ids):
            raise ValueError("Graph contains cycles (topological sort impossible)")

        return result

    def resolve(self, graph: dict[str, Node]) -> list[str]:
        """Validate and topologically sort a graph.

        Convenience method that validates then sorts.

        Args:
            graph: Dictionary mapping node IDs to Node objects.

        Returns:
            List of node IDs in topological order.

        Raises:
            ValueError: If validation fails or cycles exist.
        """
        self.validate(graph)
        return self.topological_sort(graph)
