"""Example: Polynomial distributive law verification pipeline.

This example demonstrates Invariant's core capabilities using polynomial arithmetic
to verify the algebraic identity: (p + q) * r == p*r + q*r

From section 8.5 of the architecture specification.
"""

from invariant import Executor, Node, OpRegistry
from invariant.ops.poly import (
    poly_add,
    poly_derivative,
    poly_evaluate,
    poly_from_coefficients,
    poly_multiply,
)
from invariant.store.memory import MemoryStore
from invariant.types import Integer

# Register polynomial operations
registry = OpRegistry()
registry.register("poly:from_coefficients", poly_from_coefficients)
registry.register("poly:add", poly_add)
registry.register("poly:multiply", poly_multiply)
registry.register("poly:evaluate", poly_evaluate)
registry.register("poly:derivative", poly_derivative)

# Define the graph
graph = {
    # Create polynomials from coefficient lists
    "p": Node(
        op_name="poly:from_coefficients",
        params={"coefficients": [1, 2, 1]},  # x^2 + 2x + 1
        deps=[],
    ),
    "q": Node(
        op_name="poly:from_coefficients",
        params={"coefficients": [3, 0, -1]},  # -x^2 + 3
        deps=[],
    ),
    "r": Node(
        op_name="poly:from_coefficients",
        params={"coefficients": [1, 1]},  # x + 1
        deps=[],
    ),
    # Left branch: (p + q) * r
    "p_plus_q": Node(
        op_name="poly:add",
        params={},
        deps=["p", "q"],
    ),
    "lhs": Node(
        op_name="poly:multiply",
        params={},
        deps=["p_plus_q", "r"],
    ),
    # Right branch: p*r + q*r
    "pr": Node(
        op_name="poly:multiply",
        params={},
        deps=["p", "r"],
    ),
    "qr": Node(
        op_name="poly:multiply",
        params={},
        deps=["q", "r"],
    ),
    "rhs": Node(
        op_name="poly:add",
        params={},
        deps=["pr", "qr"],
    ),
    # Evaluate both sides at x=5
    "eval_lhs": Node(
        op_name="poly:evaluate",
        params={"x": Integer(5)},
        deps=["lhs"],
    ),
    "eval_rhs": Node(
        op_name="poly:evaluate",
        params={"x": Integer(5)},
        deps=["rhs"],
    ),
    # Bonus: derivative chain
    "d1": Node(
        op_name="poly:derivative",
        params={},
        deps=["lhs"],
    ),
    "d2": Node(
        op_name="poly:derivative",
        params={},
        deps=["d1"],
    ),
    "eval_d2": Node(
        op_name="poly:evaluate",
        params={"x": Integer(5)},
        deps=["d2"],
    ),
}

store = MemoryStore()
executor = Executor(registry=registry, store=store)
results = executor.execute(graph)

# Verify distributive law: (p + q) * r == p*r + q*r
assert results["lhs"].coefficients == results["rhs"].coefficients
print("✓ Distributive law verified: (p + q) * r == p*r + q*r")
print(f"  LHS coefficients: {list(results['lhs'].coefficients)}")
print(f"  RHS coefficients: {list(results['rhs'].coefficients)}")

# Verify numeric equality at x=5
assert results["eval_lhs"].value == results["eval_rhs"].value
print(
    f"✓ Numeric equality at x=5: {results['eval_lhs'].value} == {results['eval_rhs'].value}"
)

# Verify derivative chain
assert isinstance(results["eval_d2"], Integer)
print(f"✓ Second derivative evaluated at x=5: {results['eval_d2'].value}")

print("\nPipeline features exercised:")
print("  - Chain: p -> p_plus_q -> lhs -> eval_lhs")
print("  - Branch (fan-out): r feeds lhs, pr, and qr")
print("  - Merge (fan-in): rhs = poly:add(pr, qr)")
print("  - Deep chains: lhs -> d1 -> d2 -> eval_d2")
print("  - Re-entrant patterns: d1 and eval_lhs both depend on lhs")
