"""OpRegistry for mapping operation names to callables."""

import types
from importlib.metadata import entry_points
from typing import Any, Callable

# Type alias for op packages: dict mapping short names to op callables
OpPackage = dict[str, Callable[..., Any]]


class OpRegistry:
    """Singleton registry mapping string identifiers to executable Python callables.

    Decouples the "string" name in the graph definition from the actual Python code.
    """

    _instance: "OpRegistry | None" = None
    _initialized: bool = False

    def __new__(cls) -> "OpRegistry":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the registry (only once)."""
        if not OpRegistry._initialized:
            self._ops: dict[str, Callable[..., Any]] = {}
            OpRegistry._initialized = True

    def register(self, name: str, op: Callable[..., Any]) -> None:
        """Register an operation.

        Args:
            name: The string identifier for the operation.
            op: The callable that implements the operation.
                Should be a plain Python function with typed parameters.

        Raises:
            ValueError: If name is empty or already registered.
        """
        if not name:
            raise ValueError("Operation name cannot be empty")
        if name in self._ops:
            raise ValueError(f"Operation '{name}' is already registered")
        self._ops[name] = op

    def get(self, name: str) -> Callable[..., Any]:
        """Get an operation by name.

        Args:
            name: The string identifier for the operation.

        Returns:
            The callable that implements the operation.

        Raises:
            KeyError: If operation is not registered.
        """
        if name not in self._ops:
            raise KeyError(f"Operation '{name}' is not registered")
        return self._ops[name]

    def has(self, name: str) -> bool:
        """Check if an operation is registered.

        Args:
            name: The string identifier for the operation.

        Returns:
            True if registered, False otherwise.
        """
        return name in self._ops

    def clear(self) -> None:
        """Clear all registered operations (mainly for testing)."""
        self._ops.clear()

    def register_package(self, prefix: str, ops: OpPackage | Any) -> None:
        """Register all ops from a package under a common prefix.

        Args:
            prefix: The namespace prefix (e.g. "poly").
            ops: Either a dict mapping short names to callables (OpPackage),
                 or a Python module that has an OPS dict attribute.

        Raises:
            ValueError: If prefix is empty, ops is invalid, or any operation
                name is already registered.
            AttributeError: If ops is a module but doesn't have an OPS attribute.
        """
        if not prefix:
            raise ValueError("Package prefix cannot be empty")

        # Extract the ops dict from the input
        ops_dict: OpPackage
        if isinstance(ops, dict):
            ops_dict = ops
        elif isinstance(ops, types.ModuleType):
            # It's a module - check for OPS attribute
            if not hasattr(ops, "OPS"):
                raise AttributeError(
                    f"Module {ops.__name__} does not have an OPS attribute"
                )
            ops_dict = ops.OPS
            if not isinstance(ops_dict, dict):
                raise ValueError(f"OPS attribute must be a dict, got {type(ops_dict)}")
        elif hasattr(ops, "OPS"):
            # Object with OPS attribute (not a module)
            ops_dict = ops.OPS
            if not isinstance(ops_dict, dict):
                raise ValueError(f"OPS attribute must be a dict, got {type(ops_dict)}")
        else:
            raise ValueError(
                f"ops must be a dict or module with OPS attribute, got {type(ops)}"
            )

        # Register each op with the prefix
        for name, op in ops_dict.items():
            full_name = f"{prefix}:{name}"
            self.register(full_name, op)

    def auto_discover(self) -> None:
        """Discover and register op packages from entry points.

        Scans the 'invariant.ops' entry point group. Each entry point
        should resolve to either:
          - A dict[str, Callable] (the OPS dict directly)
          - A callable that returns such a dict

        The entry point name becomes the package prefix.

        Raises:
            ValueError: If any operation name is already registered (via register_package).
        """
        eps = entry_points(group="invariant.ops")

        for ep in eps:
            try:
                # Load the entry point
                loaded = ep.load()

                # Extract the ops dict
                ops_dict: OpPackage
                if isinstance(loaded, dict):
                    ops_dict = loaded
                elif callable(loaded):
                    # Callable that returns the dict
                    result = loaded()
                    if not isinstance(result, dict):
                        continue  # Skip invalid entry points
                    ops_dict = result
                else:
                    continue  # Skip invalid entry points

                # Register the package using the entry point name as prefix
                self.register_package(ep.name, ops_dict)
            except Exception:
                # Skip invalid entry points silently
                continue
