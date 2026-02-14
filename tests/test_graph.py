"""Tests for GraphResolver."""

import pytest

from invariant.graph import GraphResolver
from invariant.node import Node


class TestGraphResolver:
    """Tests for GraphResolver."""

    def test_validate_simple_graph(self):
        """Test validation of a simple valid graph."""
        resolver = GraphResolver()
        graph = {
            "a": Node(op_name="op1", params={}, deps=[]),
            "b": Node(op_name="op2", params={}, deps=["a"]),
        }
        resolver.validate(graph)  # Should not raise

    def test_validate_missing_dependency(self):
        """Test that missing dependency raises ValueError."""
        resolver = GraphResolver()
        graph = {
            "a": Node(op_name="op1", params={}, deps=["missing"]),
        }
        with pytest.raises(ValueError, match="dependency.*doesn't exist"):
            resolver.validate(graph)

    def test_validate_with_registry(self, registry):
        """Test validation with OpRegistry."""
        registry.register("op1", lambda m: None)
        resolver = GraphResolver(registry)
        graph = {
            "a": Node(op_name="op1", params={}, deps=[]),
        }
        resolver.validate(graph)  # Should not raise

    def test_validate_unregistered_op(self, registry):
        """Test that unregistered op raises ValueError."""
        resolver = GraphResolver(registry)
        graph = {
            "a": Node(op_name="unknown_op", params={}, deps=[]),
        }
        with pytest.raises(ValueError, match="unregistered op"):
            resolver.validate(graph)

    def test_has_cycle_detection(self):
        """Test cycle detection."""
        resolver = GraphResolver()
        # Simple cycle: a -> b -> a
        graph = {
            "a": Node(op_name="op1", params={}, deps=["b"]),
            "b": Node(op_name="op2", params={}, deps=["a"]),
        }
        assert resolver._has_cycle(graph)

    def test_has_cycle_self_loop(self):
        """Test self-loop detection."""
        resolver = GraphResolver()
        graph = {
            "a": Node(op_name="op1", params={}, deps=["a"]),
        }
        assert resolver._has_cycle(graph)

    def test_has_cycle_long_cycle(self):
        """Test detection of longer cycles."""
        resolver = GraphResolver()
        # a -> b -> c -> a
        graph = {
            "a": Node(op_name="op1", params={}, deps=["c"]),
            "b": Node(op_name="op2", params={}, deps=["a"]),
            "c": Node(op_name="op3", params={}, deps=["b"]),
        }
        assert resolver._has_cycle(graph)

    def test_has_cycle_no_cycle(self):
        """Test that acyclic graph returns False."""
        resolver = GraphResolver()
        graph = {
            "a": Node(op_name="op1", params={}, deps=[]),
            "b": Node(op_name="op2", params={}, deps=["a"]),
            "c": Node(op_name="op3", params={}, deps=["a"]),
        }
        assert not resolver._has_cycle(graph)

    def test_validate_raises_on_cycle(self):
        """Test that validate raises on cycle."""
        resolver = GraphResolver()
        graph = {
            "a": Node(op_name="op1", params={}, deps=["b"]),
            "b": Node(op_name="op2", params={}, deps=["a"]),
        }
        with pytest.raises(ValueError, match="contains cycles"):
            resolver.validate(graph)

    def test_topological_sort_simple(self):
        """Test topological sort of simple graph."""
        resolver = GraphResolver()
        graph = {
            "a": Node(op_name="op1", params={}, deps=[]),
            "b": Node(op_name="op2", params={}, deps=["a"]),
        }
        result = resolver.topological_sort(graph)
        assert result == ["a", "b"] or result == ["b", "a"]
        # Actually, dependencies come first, so "a" should come before "b"
        assert result.index("a") < result.index("b")

    def test_topological_sort_diamond(self):
        """Test topological sort of diamond dependency pattern."""
        resolver = GraphResolver()
        #     a
        #    / \
        #   b   c
        #    \ /
        #     d
        graph = {
            "a": Node(op_name="op1", params={}, deps=[]),
            "b": Node(op_name="op2", params={}, deps=["a"]),
            "c": Node(op_name="op3", params={}, deps=["a"]),
            "d": Node(op_name="op4", params={}, deps=["b", "c"]),
        }
        result = resolver.topological_sort(graph)
        assert "a" in result
        assert "b" in result
        assert "c" in result
        assert "d" in result
        assert len(result) == 4
        # a must come before b and c
        assert result.index("a") < result.index("b")
        assert result.index("a") < result.index("c")
        # b and c must come before d
        assert result.index("b") < result.index("d")
        assert result.index("c") < result.index("d")

    def test_topological_sort_raises_on_cycle(self):
        """Test that topological sort raises on cycle."""
        resolver = GraphResolver()
        graph = {
            "a": Node(op_name="op1", params={}, deps=["b"]),
            "b": Node(op_name="op2", params={}, deps=["a"]),
        }
        with pytest.raises(ValueError, match="contains cycles"):
            resolver.topological_sort(graph)

    def test_resolve(self):
        """Test resolve method (validate + sort)."""
        resolver = GraphResolver()
        graph = {
            "a": Node(op_name="op1", params={}, deps=[]),
            "b": Node(op_name="op2", params={}, deps=["a"]),
        }
        result = resolver.resolve(graph)
        assert result == ["a", "b"]

    def test_resolve_raises_on_cycle(self):
        """Test that resolve raises on cycle."""
        resolver = GraphResolver()
        graph = {
            "a": Node(op_name="op1", params={}, deps=["b"]),
            "b": Node(op_name="op2", params={}, deps=["a"]),
        }
        with pytest.raises(ValueError):
            resolver.resolve(graph)

    def test_disconnected_components(self):
        """Test graph with disconnected components."""
        resolver = GraphResolver()
        graph = {
            "a": Node(op_name="op1", params={}, deps=[]),
            "b": Node(op_name="op2", params={}, deps=[]),
        }
        result = resolver.topological_sort(graph)
        assert set(result) == {"a", "b"}
        assert len(result) == 2
