"""Executor: The runtime engine for executing DAGs."""

import inspect
from typing import TYPE_CHECKING, Any

from invariant.cacheable import is_cacheable
from invariant.expressions import resolve_params
from invariant.graph import GraphResolver
from invariant.hashing import hash_manifest

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
    ) -> dict[str, Any]:
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

        # Track artifacts by node ID
        artifacts_by_node: dict[str, Any] = {}

        # Inject context values into artifacts_by_node before execution
        # This makes external dependencies available to any node that declares them in deps
        for key, value in context.items():
            # Context values must be cacheable
            if not is_cacheable(value):
                raise ValueError(
                    f"Context value for '{key}' is not cacheable, got {type(value)}"
                )
            # Store native types as-is (no wrapping)
            artifacts_by_node[key] = value

        # Execute nodes in topological order
        for node_id in sorted_nodes:
            node = graph[node_id]

            # Phase 1: Build manifest
            manifest = self._build_manifest(node, node_id, graph, artifacts_by_node)
            digest = hash_manifest(manifest)

            # Phase 2: Execute or retrieve from cache
            if self.store.exists(node.op_name, digest):
                # Cache hit: retrieve from store
                artifact = self.store.get(node.op_name, digest)
            else:
                # Cache miss: execute operation
                op = self.registry.get(node.op_name)
                artifact = self._invoke_op(op, node.op_name, manifest)

                # Persist to store
                self.store.put(node.op_name, digest, artifact)

            artifacts_by_node[node_id] = artifact

        return artifacts_by_node

    def _build_manifest(
        self,
        node: "Node",
        node_id: str,
        graph: dict[str, "Node"],
        artifacts_by_node: dict[str, Any],
    ) -> dict[str, Any]:
        """Build the input manifest for a node (Phase 1).

        The manifest is built entirely from resolved params. Dependencies are NOT
        injected into the manifest directly - they are only available for ref()/cel()
        resolution within params.

        Args:
            node: The node to build manifest for.
            node_id: The ID of the node.
            graph: The full graph (for reference).
            artifacts_by_node: Already computed artifacts for upstream nodes.

        Returns:
            The manifest dictionary mapping parameter names to resolved values.
        """
        # Collect dependency artifacts for ref()/cel() resolution
        dependencies: dict[str, Any] = {}
        for dep_id in node.deps:
            if dep_id not in artifacts_by_node:
                raise ValueError(
                    f"Node '{node_id}' depends on '{dep_id}' but artifact not found. "
                    f"This should not happen if graph is topologically sorted or "
                    f"if '{dep_id}' is provided in context."
                )
            dependencies[dep_id] = artifacts_by_node[dep_id]

        # Manifest = resolved params only. No dependency injection.
        # ref() and cel() markers in params are resolved using dependencies.
        return resolve_params(node.params, dependencies)

    def _invoke_op(self, op: Any, op_name: str, manifest: dict[str, Any]) -> Any:
        """Invoke an operation with kwargs dispatch and return validation.

        Args:
            op: The callable operation to invoke.
            op_name: The name of the operation (for error messages).
            manifest: The manifest dictionary mapping parameter names to values.

        Returns:
            The operation result (native type or ICacheable domain type).

        Raises:
            ValueError: If required parameters are missing.
            TypeError: If return value is not cacheable.
        """
        # Inspect function signature to map manifest keys to function parameters
        sig = inspect.signature(op)
        kwargs: dict[str, Any] = {}

        # Map manifest keys to function parameters by name
        for name, param in sig.parameters.items():
            if name in manifest:
                value = manifest[name]
                kwargs[name] = value
            elif param.default is not inspect.Parameter.empty:
                # Parameter has a default value, skip it
                pass
            elif param.kind == inspect.Parameter.VAR_KEYWORD:
                # Function accepts **kwargs, will handle below
                pass
            else:
                # Required parameter missing
                raise ValueError(f"Op '{op_name}': missing required parameter '{name}'")

        # If function has **kwargs, pass remaining manifest keys
        has_var_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        if has_var_kwargs:
            for key, val in manifest.items():
                if key not in kwargs:
                    kwargs[key] = val

        # Invoke the operation
        result = op(**kwargs)

        # Validate return value is cacheable
        if not is_cacheable(result):
            raise TypeError(
                f"Op '{op_name}' returned {type(result).__name__}, "
                f"which is not a cacheable type"
            )

        # Return as-is (no wrapping needed)
        return result
