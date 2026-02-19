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

    def validate(
        self, graph: dict[str, Node], context_keys: set[str] | None = None
    ) -> None:
        """Validate a graph definition.

        Checks:
        - All node dependencies exist in the graph or in context
        - All referenced ops are registered (if registry provided)
        - No cycles exist

        Args:
            graph: Dictionary mapping node IDs to Node objects.
            context_keys: Optional set of external dependency keys (from context).
                         Dependencies not in the graph are allowed if they're in context.

        Raises:
            ValueError: If validation fails (missing deps, missing ops, cycles).
        """
        # Check all dependencies exist
        node_ids = set(graph.keys())
        context_keys = context_keys or set()
        for node_id, node in graph.items():
            for dep in node.deps:
                if dep not in node_ids and dep not in context_keys:
                    raise ValueError(
                        f"Node '{node_id}' has dependency '{dep}' that doesn't exist in graph "
                        f"or context. Available: graph={sorted(node_ids)}, "
                        f"context={sorted(context_keys)}"
                    )

        # Check all ops are registered (if registry provided)
        if self.registry:
            for node_id, node in graph.items():
                if not self.registry.has(node.op_name):
                    raise ValueError(
                        f"Node '{node_id}' references unregistered op '{node.op_name}'"
                    )

        # Check for cycles (excluding context dependencies)
        if self._has_cycle(graph, context_keys=context_keys):
            raise ValueError("Graph contains cycles")

    def _has_cycle(
        self, graph: dict[str, Node], context_keys: set[str] | None = None
    ) -> bool:
        """Detect cycles in the graph using DFS.

        Args:
            graph: Dictionary mapping node IDs to Node objects.
            context_keys: Optional set of external dependency keys (from context).
                         These are excluded from cycle detection.

        Returns:
            True if cycle exists, False otherwise.
        """
        node_ids = set(graph.keys())
        context_keys = context_keys or set()
        WHITE = 0  # Unvisited
        GRAY = 1  # Currently in DFS path
        BLACK = 2  # Fully processed

        color: dict[str, int] = {node_id: WHITE for node_id in node_ids}

        def dfs(node_id: str) -> bool:
            """DFS helper that returns True if cycle found."""
            if node_id not in node_ids:
                # This is a context dependency, not part of the graph - no cycle possible
                return False
            if color[node_id] == GRAY:
                # Back edge found - cycle detected
                return True
            if color[node_id] == BLACK:
                # Already processed
                return False

            color[node_id] = GRAY
            node = graph[node_id]
            for dep in node.deps:
                # Only check dependencies that are in the graph (not context)
                if dep in node_ids:
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

    def topological_sort(
        self, graph: dict[str, Node], context_keys: set[str] | None = None
    ) -> list[str]:
        """Topologically sort the graph using Kahn's algorithm.

        Args:
            graph: Dictionary mapping node IDs to Node objects.
            context_keys: Optional set of external dependency keys (from context).
                         These are excluded from topological sorting.

        Returns:
            List of node IDs in topological order (dependencies before dependents).

        Raises:
            ValueError: If graph contains cycles.
        """
        node_ids = set(graph.keys())
        context_keys = context_keys or set()

        # Build reverse dependency map: which nodes depend on each node
        # Only include dependencies that are in the graph (not context)
        dependents: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
        for node_id, node in graph.items():
            for dep in node.deps:
                # Only track dependencies that are in the graph
                if dep in node_ids:
                    dependents[dep].append(node_id)

        # Calculate in-degree for each node (number of graph dependencies it has)
        # Context dependencies don't count toward in-degree
        in_degree: dict[str, int] = {}
        for node_id, node in graph.items():
            # Count only graph dependencies (not context)
            graph_deps = [d for d in node.deps if d in node_ids]
            in_degree[node_id] = len(graph_deps)

        # Find all nodes with in-degree 0 (no graph dependencies)
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

    def resolve(
        self, graph: dict[str, Node], context_keys: set[str] | None = None
    ) -> list[str]:
        """Validate and topologically sort a graph.

        Convenience method that validates then sorts.

        Args:
            graph: Dictionary mapping node IDs to Node objects.
            context_keys: Optional set of external dependency keys (from context).

        Returns:
            List of node IDs in topological order.

        Raises:
            ValueError: If validation fails or cycles exist.
        """
        self.validate(graph, context_keys=context_keys)
        return self.topological_sort(graph, context_keys=context_keys)
