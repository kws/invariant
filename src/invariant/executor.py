"""Executor: The runtime engine for executing DAGs."""

from typing import TYPE_CHECKING, Any

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

    def execute(self, graph: dict[str, "Node"]) -> dict[str, ICacheable]:
        """Execute a graph and return artifacts for each node.

        Args:
            graph: Dictionary mapping node IDs to Node objects.

        Returns:
            Dictionary mapping node IDs to their resulting artifacts.

        Raises:
            ValueError: If graph validation fails or execution errors occur.
        """
        # Validate and sort graph
        sorted_nodes = self.resolver.resolve(graph)

        # Track artifacts by node ID and by digest (for deduplication)
        artifacts_by_node: dict[str, ICacheable] = {}
        artifacts_by_digest: dict[str, ICacheable] = {}

        # Execute nodes in topological order
        for node_id in sorted_nodes:
            node = graph[node_id]

            # Phase 1: Build manifest
            manifest = self._build_manifest(node, node_id, graph, artifacts_by_node)
            digest = hash_manifest(manifest)

            # Phase 2: Execute or retrieve from cache
            if digest in artifacts_by_digest:
                # Deduplication: reuse existing artifact
                artifact = artifacts_by_digest[digest]
            elif self.store.exists(digest):
                # Cache hit: retrieve from store
                artifact = self.store.get(digest)
                artifacts_by_digest[digest] = artifact
            else:
                # Cache miss: execute operation
                op = self.registry.get(node.op_name)
                artifact = op(manifest)

                # Persist to store
                self.store.put(digest, artifact)
                artifacts_by_digest[digest] = artifact

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
        # By convention, upstream artifacts are referenced by their node ID
        # in the params, or we add them as dependencies
        # The architecture says "Upstream Artifacts (results from deps)"
        # So we should add artifacts from dependencies to the manifest.
        # But how? The architecture doesn't specify the exact format.
        # Let me assume that dependencies are added to the manifest
        # with their node ID as the key, or we merge their outputs.

        # Actually, looking at the architecture more carefully:
        # "Inputs: 1. Static Parameters (from Node definition). 2. Upstream Artifacts (results from deps)."
        # So the manifest should contain both params and upstream artifacts.
        # But how are they combined? Let me assume that upstream artifacts
        # are added to the manifest, possibly with their node ID as key,
        # or merged into the params.

        # For now, I'll add upstream artifacts to the manifest using
        # the dependency node ID as the key. This allows ops to access
        # upstream results by node ID.
        for dep_id in node.deps:
            if dep_id not in artifacts_by_node:
                raise ValueError(
                    f"Node '{node_id}' depends on '{dep_id}' but artifact not found. "
                    f"This should not happen if graph is topologically sorted."
                )
            # Add artifact to manifest using dependency ID as key
            manifest[dep_id] = artifacts_by_node[dep_id]

        return manifest
