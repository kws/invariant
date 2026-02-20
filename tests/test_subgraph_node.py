"""Tests for SubGraphNode class."""

import pytest

from invariant.node import Node, SubGraphNode
from invariant.params import ref


class TestSubGraphNode:
    """Tests for SubGraphNode dataclass."""

    def test_creation(self):
        """Test basic SubGraphNode creation with valid graph and output."""
        inner_a = Node(op_name="op1", params={}, deps=[])
        inner_b = Node(op_name="op2", params={}, deps=["a"])
        graph = {"a": inner_a, "b": inner_b}
        sub = SubGraphNode(params={}, deps=[], graph=graph, output="b")
        assert sub.params == {}
        assert sub.deps == []
        assert sub.graph is graph
        assert sub.output == "b"

    def test_immutability(self):
        """Test that SubGraphNode is immutable (frozen dataclass)."""
        graph = {"a": Node(op_name="op1", params={}, deps=[])}
        sub = SubGraphNode(params={}, deps=[], graph=graph, output="a")
        with pytest.raises(Exception):
            sub.output = "b"

    def test_output_not_in_graph_raises(self):
        """Test that output not in graph raises ValueError."""
        graph = {"a": Node(op_name="op1", params={}, deps=[])}
        with pytest.raises(ValueError, match="output.*must be a key in graph"):
            SubGraphNode(params={}, deps=[], graph=graph, output="missing")

    def test_invalid_params_type(self):
        """Test that non-dict params raises ValueError."""
        graph = {"a": Node(op_name="op1", params={}, deps=[])}
        with pytest.raises(ValueError, match="params must be a dictionary"):
            SubGraphNode(params="not a dict", deps=[], graph=graph, output="a")

    def test_invalid_deps_type(self):
        """Test that non-list deps raises ValueError."""
        graph = {"a": Node(op_name="op1", params={}, deps=[])}
        with pytest.raises(ValueError, match="deps must be a list"):
            SubGraphNode(params={}, deps="not a list", graph=graph, output="a")

    def test_ref_valid_when_dep_declared(self):
        """Test that ref('x') in params with deps=['x'] is valid."""
        graph = {"a": Node(op_name="op1", params={}, deps=[])}
        sub = SubGraphNode(
            params={"value": ref("x")},
            deps=["x"],
            graph=graph,
            output="a",
        )
        assert sub.deps == ["x"]
        assert sub.params["value"] == ref("x")

    def test_ref_undeclared_raises(self):
        """Test that ref('y') with deps ['x'] raises ValueError."""
        graph = {"a": Node(op_name="op1", params={}, deps=[])}
        with pytest.raises(ValueError, match="ref.*undeclared dependency"):
            SubGraphNode(
                params={"value": ref("y")},
                deps=["x"],
                graph=graph,
                output="a",
            )

    def test_invalid_graph_type(self):
        """Test that non-dict graph raises ValueError."""
        with pytest.raises(ValueError, match="graph must be a dictionary"):
            SubGraphNode(
                params={},
                deps=[],
                graph="not a dict",
                output="a",
            )
