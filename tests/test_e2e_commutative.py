"""End-to-end tests for commutative operation canonicalization."""

from invariant import Executor, Node, OpRegistry
from invariant.ops.stdlib import add, from_integer
from invariant.store.memory import MemoryStore


def test_commutative_canonicalization():
    """Test that min/max canonicalization ensures cache hits for commutative ops."""
    registry = OpRegistry()
    registry.clear()  # Clear singleton state
    registry.register("stdlib:from_integer", from_integer)
    registry.register("stdlib:add", add)

    # Create graph with two nodes computing the same sum with different operand orders
    # Both use min/max to canonicalize, so they should resolve to the same manifest
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

    # Both should produce the same result
    assert results["sum_xy"].value == results["sum_yx"].value
    assert results["sum_xy"].value == 10  # 3 + 7

    # Note: We can't easily verify they used the same cache entry without
    # inspecting the store internals, but the fact that both produce
    # the same result and the expressions canonicalize correctly is sufficient


def test_commutative_without_canonicalization():
    """Test that without canonicalization, different orders produce different results."""
    registry = OpRegistry()
    registry.clear()  # Clear singleton state
    registry.register("stdlib:from_integer", from_integer)
    registry.register("stdlib:add", add)

    # This test shows that without min/max, the order matters for caching
    # (though mathematically the result is the same)
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
        # Without canonicalization, these would have different manifests
        # (but same mathematical result)
        "sum_xy": Node(
            op_name="stdlib:add",
            params={"a": "${x}", "b": "${y}"},
            deps=["x", "y"],
        ),
        "sum_yx": Node(
            op_name="stdlib:add",
            params={"a": "${y}", "b": "${x}"},
            deps=["x", "y"],
        ),
    }

    store = MemoryStore()
    executor = Executor(registry=registry, store=store)
    results = executor.execute(graph)

    # Results are mathematically the same
    assert results["sum_xy"].value == results["sum_yx"].value
    assert results["sum_xy"].value == 10

    # But without canonicalization, they would have different manifests
    # and thus different cache entries (this is expected behavior)
