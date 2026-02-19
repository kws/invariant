"""Executor: The runtime engine for executing DAGs."""

from typing import TYPE_CHECKING, Any

from invariant.expressions import resolve_params
from invariant.graph import GraphResolver
from invariant.hashing import hash_manifest
from invariant.protocol import ICacheable

if TYPE_CHECKING:
    from invariant.node import Node
    from invariant.registry import OpRegistry
    from invariant.store.base import ArtifactStore


class Executor:
    """Runtime engine for executing DAGs.

    Manages the two-phase execution:
    - Phase 1: Context Resolution (Graph -> Manifest)
    - Phase 2: Action Execution (Manifest -> Artifact)
    """

    def __init__(
        self,
        registry: "OpRegistry",
        store: "ArtifactStore",
        resolver: "GraphResolver | None" = None,
    ) -> None:
        """Initialize Executor.

        Args:
            registry: OpRegistry for looking up operations.
            store: ArtifactStore for caching artifacts.
            resolver: Optional GraphResolver. If None, creates one with registry.
        """
        self.registry = registry
        self.store = store
        self.resolver = resolver or GraphResolver(registry)

    def execute(
        self, graph: dict[str, "Node"], context: dict[str, Any] | None = None
    ) -> dict[str, ICacheable]:
        """Execute a graph and return artifacts for each node.

        Args:
            graph: Dictionary mapping node IDs to Node objects.
            context: Optional dictionary of external dependencies (values not in graph).
                    These are injected as artifacts available to any node that declares
                    them in deps.

        Returns:
            Dictionary mapping node IDs to their resulting artifacts.

        Raises:
            ValueError: If graph validation fails or execution errors occur.
        """
        # Validate and sort graph (pass context for validation)
        context = context or {}
        sorted_nodes = self.resolver.resolve(graph, context_keys=set(context.keys()))

        # Track artifacts by node ID and by (op_name, digest) (for deduplication)
        artifacts_by_node: dict[str, ICacheable] = {}
        artifacts_by_digest: dict[tuple[str, str], ICacheable] = {}

        # Inject context values into artifacts_by_node before execution
        # This makes external dependencies available to any node that declares them in deps
        for key, value in context.items():
            # Context values must be ICacheable
            if not isinstance(value, ICacheable):
                raise ValueError(
                    f"Context value for '{key}' must be ICacheable, got {type(value)}"
                )
            artifacts_by_node[key] = value

        # Execute nodes in topological order
        for node_id in sorted_nodes:
            node = graph[node_id]

            # Phase 1: Build manifest
            manifest = self._build_manifest(node, node_id, graph, artifacts_by_node)
            digest = hash_manifest(manifest)

            # Phase 2: Execute or retrieve from cache
            # Use composite key (op_name, digest) for cache lookup
            cache_key = (node.op_name, digest)
            if cache_key in artifacts_by_digest:
                # Deduplication: reuse existing artifact
                artifact = artifacts_by_digest[cache_key]
            elif self.store.exists(node.op_name, digest):
                # Cache hit: retrieve from store
                artifact = self.store.get(node.op_name, digest)
                artifacts_by_digest[cache_key] = artifact
            else:
                # Cache miss: execute operation
                op = self.registry.get(node.op_name)
                artifact = op(manifest)

                # Persist to store
                self.store.put(node.op_name, digest, artifact)
                artifacts_by_digest[cache_key] = artifact

            artifacts_by_node[node_id] = artifact

        return artifacts_by_node

    def _build_manifest(
        self,
        node: "Node",
        node_id: str,
        graph: dict[str, "Node"],
        artifacts_by_node: dict[str, ICacheable],
    ) -> dict[str, Any]:
        """Build the input manifest for a node (Phase 1).

        Args:
            node: The node to build manifest for.
            node_id: The ID of the node.
            graph: The full graph (for reference).
            artifacts_by_node: Already computed artifacts for upstream nodes.

        Returns:
            The manifest dictionary mapping input names to values.
        """
        manifest: dict[str, any] = {}

        # Add static parameters
        manifest.update(node.params)

        # Add upstream artifacts
        # Upstream artifacts are added to the manifest using their dependency ID as the key.
        # This allows ops to access upstream results by node ID, and also allows
        # CEL expressions to reference them (e.g., ${background.width}).
        dependencies: dict[str, ICacheable] = {}
        for dep_id in node.deps:
            if dep_id not in artifacts_by_node:
                raise ValueError(
                    f"Node '{node_id}' depends on '{dep_id}' but artifact not found. "
                    f"This should not happen if graph is topologically sorted or "
                    f"if '{dep_id}' is provided in context."
                )
            # Add artifact to dependencies dict for expression resolution
            dependencies[dep_id] = artifacts_by_node[dep_id]
            # Also add to manifest directly (for ops that access by key)
            manifest[dep_id] = artifacts_by_node[dep_id]

        # Resolve ${...} CEL expressions in params
        # This replaces expressions like ${root.width} with their evaluated values
        resolved_params = resolve_params(node.params, dependencies)

        # Update manifest with resolved params (overriding any raw expressions)
        manifest.update(resolved_params)

        return manifest
