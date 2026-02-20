"""End-to-end tests for context/external dependency support."""

from invariant import Executor, Node, OpRegistry, cel
from invariant.ops.stdlib import identity
from invariant.store.memory import MemoryStore


def test_context_external_dependencies():
    """Test that external dependencies provided via context work correctly."""
    registry = OpRegistry()
    registry.clear()  # Clear singleton state
    registry.register("stdlib:identity", identity)

    # Create a simple context with native int values
    context = {
        "root_width": 144,
        "root_height": 144,
    }

    graph = {
        "background": Node(
            op_name="stdlib:identity",
            params={"value": cel("root_width")},
            deps=["root_width"],
        ),
        "height": Node(
            op_name="stdlib:identity",
            params={"value": cel("root_height")},
            deps=["root_height"],
        ),
    }

    store = MemoryStore()
    executor = Executor(registry=registry, store=store)
    results = executor.execute(graph, context=context)

    # Verify results
    assert results["background"] == 144
    assert results["height"] == 144


def test_context_missing_dependency():
    """Test that missing context dependency raises an error."""
    registry = OpRegistry()
    registry.clear()  # Clear singleton state
    registry.register("stdlib:identity", identity)

    graph = {
        "node": Node(
            op_name="stdlib:identity",
            params={"value": 42},
            deps=["missing"],  # Not in graph or context
        ),
    }

    store = MemoryStore()
    executor = Executor(registry=registry, store=store)

    # Should raise ValueError because 'missing' is not in graph or context
    try:
        executor.execute(graph)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "missing" in str(e).lower() or "dependency" in str(e).lower()


def test_context_with_graph_nodes():
    """Test that context and graph nodes can be mixed."""
    registry = OpRegistry()
    registry.clear()  # Clear singleton state
    registry.register("stdlib:identity", identity)

    context = {
        "external": 100,
    }

    graph = {
        "internal": Node(
            op_name="stdlib:identity",
            params={"value": 50},
            deps=[],
        ),
        "combined": Node(
            op_name="stdlib:add",
            params={"a": cel("external"), "b": cel("internal")},
            deps=["external", "internal"],
        ),
    }

    # Need to register add op
    from invariant.ops.stdlib import add

    registry.register("stdlib:add", add)

    store = MemoryStore()
    executor = Executor(registry=registry, store=store)
    results = executor.execute(graph, context=context)

    # Verify combined result
    assert results["combined"] == 150  # 100 + 50
