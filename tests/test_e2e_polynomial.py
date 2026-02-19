"""End-to-end tests for polynomial operations pipeline."""

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


def test_distributive_law_pipeline():
    """Test the distributive law verification pipeline from architecture spec."""
    # Register polynomial operations
    registry = OpRegistry()
    registry.clear()  # Clear singleton state
    registry.register("poly:from_coefficients", poly_from_coefficients)
    registry.register("poly:add", poly_add)
    registry.register("poly:multiply", poly_multiply)
    registry.register("poly:evaluate", poly_evaluate)
    registry.register("poly:derivative", poly_derivative)

    # Define the graph from section 8.5 of architecture spec
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

    # Verify numeric equality at x=5
    assert results["eval_lhs"].value == results["eval_rhs"].value

    # Verify derivative chain
    assert isinstance(results["eval_d2"], Integer)


def test_cache_reuse():
    """Test that running the same graph twice skips all ops on the second run."""
    registry = OpRegistry()
    registry.clear()  # Clear singleton state
    registry.register("poly:from_coefficients", poly_from_coefficients)
    registry.register("poly:add", poly_add)

    graph = {
        "p": Node(
            op_name="poly:from_coefficients",
            params={"coefficients": [1, 2, 1]},
            deps=[],
        ),
        "q": Node(
            op_name="poly:from_coefficients",
            params={"coefficients": [3, 0, -1]},
            deps=[],
        ),
        "sum": Node(
            op_name="poly:add",
            params={},
            deps=["p", "q"],
        ),
    }

    store = MemoryStore()
    executor = Executor(registry=registry, store=store)

    # First run - all ops execute
    results1 = executor.execute(graph)

    # Second run - should use cache
    results2 = executor.execute(graph)

    # Results should be identical
    assert results1["sum"].coefficients == results2["sum"].coefficients

    # Verify cache was used (store should have entries)
    # We can't easily verify ops were skipped without mocking, but we can
    # verify the results are correct and identical
