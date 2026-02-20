"""Tests for CEL expression evaluation."""

from decimal import Decimal

import pytest

from invariant import cel, ref
from invariant.expressions import resolve_params
from invariant.types import Polynomial


class TestVariableReferences:
    """Tests for variable references in expressions."""

    def test_simple_variable_reference(self):
        """Test ${x} resolves to artifact value."""
        params = {"width": "${x}"}
        deps = {"x": 100}
        result = resolve_params(params, deps)
        assert result["width"] == 100

    def test_string_artifact(self):
        """Test variable reference with string artifact."""
        params = {"name": "${x}"}
        deps = {"x": "hello"}
        result = resolve_params(params, deps)
        assert result["name"] == "hello"

    def test_undeclared_variable(self):
        """Test that undeclared variables raise ValueError."""
        params = {"width": "${x}"}
        deps = {}
        with pytest.raises(ValueError, match="Failed to evaluate CEL expression"):
            resolve_params(params, deps)


class TestIntegerArithmetic:
    """Tests for integer arithmetic expressions."""

    def test_addition(self):
        """Test ${x + y} adds two integers."""
        params = {"sum": "${x + y}"}
        deps = {"x": 3, "y": 7}
        result = resolve_params(params, deps)
        assert result["sum"] == 10

    def test_addition_with_literal(self):
        """Test ${x + 1} adds integer and literal."""
        params = {"result": "${x + 1}"}
        deps = {"x": 5}
        result = resolve_params(params, deps)
        assert result["result"] == 6

    def test_multiplication(self):
        """Test ${x * 2} multiplies integers."""
        params = {"result": "${x * 2}"}
        deps = {"x": 7}
        result = resolve_params(params, deps)
        assert result["result"] == 14

    def test_subtraction(self):
        """Test ${x - y} subtracts integers."""
        params = {"diff": "${x - y}"}
        deps = {"x": 10, "y": 3}
        result = resolve_params(params, deps)
        assert result["diff"] == 7

    def test_literal_only_arithmetic(self):
        """Test arithmetic with only literals (no dependencies)."""
        params = {"result": "${1 + 2}"}
        deps = {}
        result = resolve_params(params, deps)
        assert result["result"] == 3


class TestDecimalArithmetic:
    """Tests for decimal arithmetic (avoiding floats)."""

    def test_decimal_from_string(self):
        """Test ${decimal("3.14")} creates Decimal from string."""
        params = {"pi": '${decimal("3.14")}'}
        deps = {}
        result = resolve_params(params, deps)
        assert isinstance(result["pi"], Decimal)
        assert result["pi"] == Decimal("3.14")

    def test_decimal_addition(self):
        """Test ${decimal("1.5") + decimal("2.5")} adds Decimals."""
        params = {"sum": '${decimal("1.5") + decimal("2.5")}'}
        deps = {}
        result = resolve_params(params, deps)
        assert isinstance(result["sum"], Decimal)
        assert result["sum"] == Decimal("4.0")

    def test_decimal_from_integer(self):
        """Test ${decimal(x)} converts integer to Decimal."""
        params = {"result": "${decimal(x)}"}
        deps = {"x": 42}
        result = resolve_params(params, deps)
        assert isinstance(result["result"], Decimal)
        assert result["result"] == Decimal("42")

    def test_decimal_multiplication(self):
        """Test ${decimal("3.14") * 2} multiplies Decimal."""
        params = {"result": '${decimal("3.14") * 2}'}
        deps = {}
        result = resolve_params(params, deps)
        assert isinstance(result["result"], Decimal)
        assert result["result"] == Decimal("6.28")

    def test_decimal_prevents_float(self):
        """Test that decimal() is required for fractional values."""
        # This test verifies that we can't accidentally create floats
        # The expression system should reject float results
        params = {"result": '${decimal("3.14")}'}
        deps = {}
        result = resolve_params(params, deps)
        assert not isinstance(result["result"], float)
        assert isinstance(result["result"], Decimal)


class TestStringInterpolation:
    """Tests for string interpolation with mixed text and expressions."""

    def test_simple_interpolation(self):
        """Test "prefix_${x}_suffix" interpolates value."""
        params = {"message": "Width is ${x}px"}
        deps = {"x": 200}
        result = resolve_params(params, deps)
        assert result["message"] == "Width is 200px"

    def test_multiple_interpolations(self):
        """Test string with multiple expressions."""
        params = {"message": "${x} + ${y} = ${x + y}"}
        deps = {"x": 3, "y": 7}
        result = resolve_params(params, deps)
        assert result["message"] == "3 + 7 = 10"

    def test_string_artifact_interpolation(self):
        """Test interpolation with string artifact."""
        params = {"greeting": "Hello, ${name}!"}
        deps = {"name": "world"}
        result = resolve_params(params, deps)
        assert result["greeting"] == "Hello, world!"

    def test_decimal_in_string(self):
        """Test decimal values in string interpolation."""
        params = {"message": 'Pi is approximately ${decimal("3.14")}'}
        deps = {}
        result = resolve_params(params, deps)
        assert "3.14" in result["message"]


class TestBuiltInFunctions:
    """Tests for built-in functions: min, max, decimal."""

    def test_min_with_values(self):
        """Test ${min(x, y)} returns smaller value."""
        params = {"result": "${min(x, y)}"}
        deps = {"x": 7, "y": 3}
        result = resolve_params(params, deps)
        assert result["result"] == 3

    def test_max_with_values(self):
        """Test ${max(x, y)} returns larger value."""
        params = {"result": "${max(x, y)}"}
        deps = {"x": 7, "y": 3}
        result = resolve_params(params, deps)
        assert result["result"] == 7

    def test_min_with_artifacts(self):
        """Test ${min(x, y)} with artifact references."""
        params = {"a": "${min(x, y)}", "b": "${max(x, y)}"}
        deps = {"x": 7, "y": 3}
        result = resolve_params(params, deps)
        # min/max with artifacts should return the value
        assert result["a"] == 3
        assert result["b"] == 7

    def test_min_max_canonicalization(self):
        """Test that min/max canonicalizes commutative operations."""
        # Same expression with different order should produce same result
        params1 = {"a": "${min(x, y)}", "b": "${max(x, y)}"}
        params2 = {"a": "${min(y, x)}", "b": "${max(y, x)}"}
        deps = {"x": 7, "y": 3}
        result1 = resolve_params(params1, deps)
        result2 = resolve_params(params2, deps)
        assert result1["a"] == result2["a"] == 3
        assert result1["b"] == result2["b"] == 7

    def test_decimal_function(self):
        """Test decimal() function with various inputs."""
        # From string
        params1 = {"result": '${decimal("3.14")}'}
        result1 = resolve_params(params1, {})
        assert isinstance(result1["result"], Decimal)
        assert result1["result"] == Decimal("3.14")

        # From integer artifact
        params2 = {"result": "${decimal(x)}"}
        result2 = resolve_params(params2, {"x": 42})
        assert isinstance(result2["result"], Decimal)
        assert result2["result"] == Decimal("42")


class TestErrorCases:
    """Tests for error handling."""

    def test_invalid_expression_syntax(self):
        """Test that invalid expression syntax raises ValueError."""
        params = {"result": "${invalid syntax!!}"}
        deps = {}
        with pytest.raises(
            ValueError, match="Failed to (parse|evaluate) CEL expression"
        ):
            resolve_params(params, deps)

    def test_undeclared_dependency(self):
        """Test that undeclared dependency raises ValueError."""
        params = {"result": "${nonexistent}"}
        deps = {}
        with pytest.raises(ValueError, match="Failed to evaluate CEL expression"):
            resolve_params(params, deps)

    def test_nested_dict_expressions(self):
        """Test expressions in nested dictionaries."""
        params = {
            "config": {
                "width": "${x}",
                "height": "${y}",
            }
        }
        deps = {"x": 100, "y": 200}
        result = resolve_params(params, deps)
        assert result["config"]["width"] == 100
        assert result["config"]["height"] == 200

    def test_list_expressions(self):
        """Test expressions in lists."""
        params = {"values": ["${x}", "${y}"]}
        deps = {"x": 1, "y": 2}
        result = resolve_params(params, deps)
        assert result["values"] == [1, 2]


class TestComplexExpressions:
    """Tests for complex expression combinations."""

    def test_arithmetic_with_functions(self):
        """Test combining arithmetic and functions."""
        params = {"result": "${min(x, y) + max(x, y)}"}
        deps = {"x": 3, "y": 7}
        result = resolve_params(params, deps)
        assert result["result"] == 10  # min(3,7) + max(3,7) = 3 + 7 = 10

    def test_decimal_arithmetic_chain(self):
        """Test chained decimal arithmetic."""
        params = {"result": '${decimal("1.5") + decimal("2.5") + decimal("3.0")}'}
        deps = {}
        result = resolve_params(params, deps)
        assert isinstance(result["result"], Decimal)
        assert result["result"] == Decimal("7.0")

    def test_mixed_types_in_expression(self):
        """Test expressions with mixed artifact types."""
        params = {"message": "Count: ${count}, Name: ${name}"}
        deps = {"count": 42, "name": "test"}
        result = resolve_params(params, deps)
        assert result["message"] == "Count: 42, Name: test"


class TestRefMarker:
    """Tests for ref() marker - artifact passthrough."""

    def test_ref_returns_artifact(self):
        """Test that ref() returns the ICacheable artifact directly."""
        params = {"poly": ref("p")}
        poly_artifact = Polynomial((1, 2, 1))
        deps = {"p": poly_artifact}
        result = resolve_params(params, deps)
        assert result["poly"] is poly_artifact
        assert isinstance(result["poly"], Polynomial)

    def test_ref_with_integer(self):
        """Test ref() with integer artifact."""
        params = {"value": ref("x")}
        deps = {"x": 42}
        result = resolve_params(params, deps)
        assert isinstance(result["value"], int)
        assert result["value"] == 42

    def test_ref_undeclared_dependency(self):
        """Test that ref() with undeclared dependency raises ValueError."""
        params = {"value": ref("missing")}
        deps = {}
        with pytest.raises(ValueError, match="undeclared dependency"):
            resolve_params(params, deps)

    def test_ref_nested_in_dict(self):
        """Test ref() marker nested in dictionary."""
        params = {"config": {"poly": ref("p"), "count": 5}}
        poly_artifact = Polynomial((1, 2, 1))
        deps = {"p": poly_artifact}
        result = resolve_params(params, deps)
        assert result["config"]["poly"] is poly_artifact
        assert result["config"]["count"] == 5

    def test_ref_nested_in_list(self):
        """Test ref() marker nested in list."""
        params = {"polys": [ref("p"), ref("q")]}
        p_artifact = Polynomial((1, 2))
        q_artifact = Polynomial((3, 4))
        deps = {"p": p_artifact, "q": q_artifact}
        result = resolve_params(params, deps)
        assert result["polys"][0] is p_artifact
        assert result["polys"][1] is q_artifact


class TestCelMarker:
    """Tests for cel() marker - CEL expression evaluation."""

    def test_cel_simple_expression(self):
        """Test cel() with simple arithmetic expression."""
        params = {"sum": cel("x + y")}
        deps = {"x": 3, "y": 7}
        result = resolve_params(params, deps)
        assert result["sum"] == 10

    def test_cel_field_access(self):
        """Test cel() accessing artifact value."""
        params = {"width": cel("background")}
        deps = {"background": 100}
        result = resolve_params(params, deps)
        assert result["width"] == 100

    def test_cel_decimal_arithmetic(self):
        """Test cel() with decimal arithmetic."""
        params = {"result": cel('decimal("3.14") + decimal("2.86")')}
        deps = {}
        result = resolve_params(params, deps)
        assert isinstance(result["result"], Decimal)
        assert result["result"] == Decimal("6.00")

    def test_cel_min_max(self):
        """Test cel() with min/max functions."""
        params = {
            "min_val": cel("min(x, y)"),
            "max_val": cel("max(x, y)"),
        }
        deps = {"x": 7, "y": 3}
        result = resolve_params(params, deps)
        assert result["min_val"] == 3
        assert result["max_val"] == 7

    def test_cel_undeclared_dependency(self):
        """Test that cel() with undeclared dependency raises ValueError."""
        params = {"value": cel("missing")}
        deps = {}
        with pytest.raises(ValueError, match="Failed to evaluate CEL expression"):
            resolve_params(params, deps)

    def test_cel_nested_in_dict(self):
        """Test cel() marker nested in dictionary."""
        params = {"config": {"width": cel("bg"), "height": 200}}
        deps = {"bg": 100}
        result = resolve_params(params, deps)
        assert result["config"]["width"] == 100
        assert result["config"]["height"] == 200

    def test_cel_vs_string_interpolation(self):
        """Test that cel() and ${...} string interpolation both work."""
        params = {
            "computed": cel("x + y"),
            "message": "Sum is ${x + y}",
        }
        deps = {"x": 3, "y": 7}
        result = resolve_params(params, deps)
        assert result["computed"] == 10
        assert result["message"] == "Sum is 10"
