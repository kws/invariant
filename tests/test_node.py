"""Tests for Node class."""

import pytest

from invariant.node import Node


class TestNode:
    """Tests for Node dataclass."""

    def test_creation(self):
        """Test basic node creation."""
        node = Node(op_name="test_op", params={"a": 1}, deps=[])
        assert node.op_name == "test_op"
        assert node.params == {"a": 1}
        assert node.deps == []

    def test_immutability(self):
        """Test that node is immutable (frozen dataclass)."""
        node = Node(op_name="test", params={}, deps=[])
        with pytest.raises(Exception):  # dataclass.FrozenInstanceError
            node.op_name = "new_name"

    def test_with_dependencies(self):
        """Test node with dependencies."""
        node = Node(op_name="test_op", params={"x": 1}, deps=["node1", "node2"])
        assert node.deps == ["node1", "node2"]

    def test_empty_op_name_raises(self):
        """Test that empty op_name raises ValueError."""
        with pytest.raises(ValueError, match="op_name cannot be empty"):
            Node(op_name="", params={}, deps=[])

    def test_invalid_params_type(self):
        """Test that non-dict params raises ValueError."""
        with pytest.raises(ValueError, match="params must be a dictionary"):
            Node(op_name="test", params="not a dict", deps=[])

    def test_invalid_deps_type(self):
        """Test that non-list deps raises ValueError."""
        with pytest.raises(ValueError, match="deps must be a list"):
            Node(op_name="test", params={}, deps="not a list")
