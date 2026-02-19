"""Example: Commutative operation canonicalization.

This example demonstrates how to use min() and max() CEL functions to
canonicalize operand order for commutative operations, ensuring cache hits
regardless of how dependencies are declared or referenced.

From section 8.7 of the architecture specification.
"""

from invariant import Executor, Node, OpRegistry
from invariant.ops.stdlib import add, from_integer
from invariant.store.memory import MemoryStore

# Register operations
registry = OpRegistry()
registry.register("stdlib:from_integer", from_integer)
registry.register("stdlib:add", add)

# Define the graph
graph = {
    "x": Node(
        op_name="stdlib:from_integer",
        params={"value": 7},
        deps=[],
    ),
    "y": Node(
        op_name="stdlib:from_integer",
        params={"value": 3},
        deps=[],
    ),
    # First node: explicitly uses x, y order
    "sum_xy": Node(
        op_name="stdlib:add",
        params={"a": "${min(x, y)}", "b": "${max(x, y)}"},
        deps=["x", "y"],
    ),
    # Second node: uses y, x order in expressions — same result!
    "sum_yx": Node(
        op_name="stdlib:add",
        params={"a": "${min(y, x)}", "b": "${max(y, x)}"},
        deps=["x", "y"],
    ),
}

store = MemoryStore()
executor = Executor(registry=registry, store=store)
results = executor.execute(graph)

# Both nodes resolve to the same manifest {a: 3, b: 7}
# Same digest -> single execution, cache hit for the second node
print("✓ Both sum_xy and sum_yx resolve to manifest {a: 3, b: 7}")
print(f"  sum_xy result: {results['sum_xy'].value}")
print(f"  sum_yx result: {results['sum_yx'].value}")
print(f"  Results are equal: {results['sum_xy'].value == results['sum_yx'].value}")

print("\nCanonicalization pattern:")
print("  - Use min() and max() in CEL expressions to ensure deterministic ordering")
print("  - Ensures cache hits for commutative operations regardless of operand order")
print("  - Both nodes produce the same manifest hash, triggering deduplication")
