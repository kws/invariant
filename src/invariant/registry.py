"""OpRegistry for mapping operation names to callables."""

from typing import Any, Callable

from invariant.protocol import ICacheable


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
            self._ops: dict[str, Callable[[dict[str, Any]], ICacheable]] = {}
            OpRegistry._initialized = True
    
    def register(self, name: str, op: Callable[[dict[str, Any]], ICacheable]) -> None:
        """Register an operation.
        
        Args:
            name: The string identifier for the operation.
            op: The callable that implements the operation.
                Must accept a manifest (dict) and return an ICacheable.
                
        Raises:
            ValueError: If name is empty or already registered.
        """
        if not name:
            raise ValueError("Operation name cannot be empty")
        if name in self._ops:
            raise ValueError(f"Operation '{name}' is already registered")
        self._ops[name] = op
    
    def get(self, name: str) -> Callable[[dict[str, Any]], ICacheable]:
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

