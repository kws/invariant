"""Example: Commutative operation canonicalization.

This example demonstrates how to use min() and max() CEL functions to
canonicalize operand order for commutative operations, ensuring cache hits
regardless of how dependencies are declared or referenced.

From section 8.7 of the architecture specification.
"""

import argparse

from invariant import Executor, Node, OpRegistry, cel
from invariant.ops.stdlib import add, identity
from invariant.store.memory import MemoryStore


def main():
    parser = argparse.ArgumentParser(
        description="Demonstrate commutative operation canonicalization"
    )
    parser.add_argument(
        "--x",
        type=int,
        default=7,
        help="First value for addition (default: 7)",
    )
    parser.add_argument(
        "--y",
        type=int,
        default=3,
        help="Second value for addition (default: 3)",
    )
    args = parser.parse_args()

    # Register operations
    registry = OpRegistry()
    registry.register("stdlib:identity", identity)
    registry.register("stdlib:add", add)

    # Define the graph
    graph = {
        "x": Node(
            op_name="stdlib:identity",
            params={"value": args.x},
            deps=[],
        ),
        "y": Node(
            op_name="stdlib:identity",
            params={"value": args.y},
            deps=[],
        ),
        # First node: explicitly uses x, y order
        "sum_xy": Node(
            op_name="stdlib:add",
            params={"a": cel("min(x, y)"), "b": cel("max(x, y)")},
            deps=["x", "y"],
        ),
        # Second node: uses y, x order in expressions — same result!
        "sum_yx": Node(
            op_name="stdlib:add",
            params={"a": cel("min(y, x)"), "b": cel("max(y, x)")},
            deps=["x", "y"],
        ),
    }

    store = MemoryStore()
    executor = Executor(registry=registry, store=store)
    results = executor.execute(graph)

    # Both nodes resolve to the same manifest (min, max order)
    # Same digest -> single execution, cache hit for the second node
    min_val = min(args.x, args.y)
    max_val = max(args.x, args.y)
    print(
        f"✓ Both sum_xy and sum_yx resolve to manifest {{a: {min_val}, b: {max_val}}}"
    )
    print(f"  sum_xy result: {results['sum_xy']}")
    print(f"  sum_yx result: {results['sum_yx']}")
    print(f"  Results are equal: {results['sum_xy'] == results['sum_yx']}")

    print("\nCanonicalization pattern:")
    print("  - Use min() and max() in CEL expressions to ensure deterministic ordering")
    print(
        "  - Ensures cache hits for commutative operations regardless of operand order"
    )
    print("  - Both nodes produce the same manifest hash, triggering deduplication")


if __name__ == "__main__":
    main()
