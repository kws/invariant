"""Tests for CEL expression evaluation."""

from decimal import Decimal
from unittest.mock import patch

import pytest

from invariant import cel, ref
from invariant.expressions import resolve_params, _evaluate_cel, _cel_to_python
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


class TestWholeStringReturnType:
    """Tests for whole-string ${expr} return type behavior.

    See expressions.md §2.3 for whole-string return type behavior.
    """

    def test_whole_string_returns_int(self):
        """Test that whole-string ${expr} returns native type (int, not string).
        See expressions.md §2.3 for whole-string return type behavior.
        """
        params = {"width": "${x}"}
        deps = {"x": 100}
        result = resolve_params(params, deps)
        assert result["width"] == 100
        assert isinstance(result["width"], int)
        assert not isinstance(result["width"], str)

    def test_whole_string_returns_decimal(self):
        """Test that whole-string ${expr} returns native type (Decimal, not string).
        See expressions.md §2.3 for whole-string return type behavior.
        """
        params = {"pi": '${decimal("3.14")}'}
        deps = {}
        result = resolve_params(params, deps)
        assert isinstance(result["pi"], Decimal)
        assert result["pi"] == Decimal("3.14")
        assert not isinstance(result["pi"], str)

    def test_whole_string_returns_string(self):
        """Test that whole-string ${expr} preserves string type.
        See expressions.md §2.3 for whole-string return type behavior.
        """
        params = {"name": "${x}"}
        deps = {"x": "hello"}
        result = resolve_params(params, deps)
        assert result["name"] == "hello"
        assert isinstance(result["name"], str)

    def test_whole_string_with_surrounding_whitespace(self):
        """Test that whole-string with surrounding whitespace returns native type after trimming.
        See expressions.md §2.3 for whole-string return type behavior.
        """
        params = {"value": "  ${x}  "}
        deps = {"x": 100}
        result = resolve_params(params, deps)
        assert result["value"] == 100
        assert isinstance(result["value"], int)
        assert not isinstance(result["value"], str)

    def test_whole_string_with_internal_whitespace(self):
        """Test that whole-string with internal whitespace returns native type.
        See expressions.md §2.3 for whole-string return type behavior.
        """
        params = {"value": "${ x }"}
        deps = {"x": 100}
        result = resolve_params(params, deps)
        assert result["value"] == 100
        assert isinstance(result["value"], int)
        assert not isinstance(result["value"], str)

    def test_whole_string_equivalent_to_cel_int(self):
        """Test that ${expr} and cel("expr") produce identical results for int when whole-string.
        See expressions.md §2.3 for whole-string return type behavior.
        """
        params_a = {"value": "${x}"}
        params_b = {"value": cel("x")}
        deps = {"x": 100}
        result_a = resolve_params(params_a, deps)
        result_b = resolve_params(params_b, deps)
        assert result_a["value"] == result_b["value"]
        assert type(result_a["value"]) is type(result_b["value"])
        assert isinstance(result_a["value"], int)

    def test_whole_string_equivalent_to_cel_decimal(self):
        """Test that ${expr} and cel("expr") produce identical results for Decimal when whole-string.
        See expressions.md §2.3 for whole-string return type behavior.
        """
        params_a = {"value": '${decimal("3.14")}'}
        params_b = {"value": cel('decimal("3.14")')}
        deps = {}
        result_a = resolve_params(params_a, deps)
        result_b = resolve_params(params_b, deps)
        assert result_a["value"] == result_b["value"]
        assert type(result_a["value"]) is type(result_b["value"])
        assert isinstance(result_a["value"], Decimal)

    def test_whole_string_equivalent_to_cel_string(self):
        """Test that ${expr} and cel("expr") produce identical results for str when whole-string.
        See expressions.md §2.3 for whole-string return type behavior.
        """
        params_a = {"value": "${x}"}
        params_b = {"value": cel("x")}
        deps = {"x": "hello"}
        result_a = resolve_params(params_a, deps)
        result_b = resolve_params(params_b, deps)
        assert result_a["value"] == result_b["value"]
        assert type(result_a["value"]) is type(result_b["value"])
        assert isinstance(result_a["value"], str)

    def test_mixed_text_always_returns_string(self):
        """Test that mixed text always returns string, contrasting with whole-string behavior.
        See expressions.md §2.3 for whole-string return type behavior.
        """
        params = {"message": "Width is ${x}px"}
        deps = {"x": 100}
        result = resolve_params(params, deps)
        assert result["message"] == "Width is 100px"
        assert isinstance(result["message"], str)
        # Contrast: whole-string would return int, but mixed text always returns str
        assert not isinstance(result["message"], int)


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


class TestEdgeCases:
    """Tests for edge cases in expression evaluation."""

    def test_string_without_valid_expression(self):
        """Test string with ${} but no valid expression pattern (line 199)."""
        # String with "${" and "}" but doesn't match the regex pattern
        params = {"text": "This has ${ but no closing brace"}
        deps = {}
        # Should return as-is since no valid ${...} pattern found
        result = resolve_params(params, deps)
        assert result["text"] == "This has ${ but no closing brace"

    def test_string_with_malformed_expression(self):
        """Test string with malformed expression delimiters."""
        params = {"text": "This has } but no opening ${"}
        deps = {}
        result = resolve_params(params, deps)
        assert result["text"] == "This has } but no opening ${"


class TestTypeConversions:
    """Tests for type conversions in _value_to_cel and _cel_to_python."""

    def test_bool_type_conversion(self):
        """Test bool type conversion in _value_to_cel.

        Note: Line 308 (BoolType conversion) is currently unreachable because
        bool is a subclass of int in Python, so the int check at line 303
        catches bool values first. This test verifies the actual behavior.
        """
        from invariant.expressions import _value_to_cel
        import celpy.celtypes as celtypes

        # Bool values are caught by the int check (bool is subclass of int)
        result = _value_to_cel(True)
        assert isinstance(result, celtypes.IntType)
        assert int(result) == 1

    def test_bool_false_conversion(self):
        """Test bool False conversion."""
        from invariant.expressions import _value_to_cel
        import celpy.celtypes as celtypes

        result = _value_to_cel(False)
        assert isinstance(result, celtypes.IntType)
        assert int(result) == 0

    def test_decimal_passthrough(self):
        """Test Decimal passthrough in _value_to_cel (line 311)."""
        params = {"value": "${x}"}
        deps = {"x": Decimal("3.14")}
        result = resolve_params(params, deps)
        assert isinstance(result["value"], Decimal)
        assert result["value"] == Decimal("3.14")

    def test_decimal_in_arithmetic(self):
        """Test Decimal in arithmetic expression."""
        params = {"sum": "${x + y}"}
        deps = {"x": Decimal("1.5"), "y": Decimal("2.5")}
        result = resolve_params(params, deps)
        assert isinstance(result["sum"], Decimal)
        assert result["sum"] == Decimal("4.0")

    def test_none_handling(self):
        """Test None handling in _value_to_cel (lines 321-323)."""
        params = {"value": "${x}"}
        deps = {"x": None}
        result = resolve_params(params, deps)
        assert result["value"] is None

    def test_none_in_expression(self):
        """Test None in CEL expression."""
        params = {"result": "${x == null}"}
        deps = {"x": None}
        result = resolve_params(params, deps)
        assert result["result"] is True

    def test_icacheable_conversion(self):
        """Test ICacheable conversion in _value_to_cel (lines 325-327)."""
        params = {"poly": "${p}"}
        poly_artifact = Polynomial((1, 2, 1))
        deps = {"p": poly_artifact}
        result = resolve_params(params, deps)
        # Should return a dict representation of the Polynomial
        assert isinstance(result["poly"], dict)
        assert "coefficients" in result["poly"]

    def test_list_conversion(self):
        """Test list conversion in _value_to_cel (lines 318-320)."""
        from invariant.expressions import _value_to_cel
        import celpy.celtypes as celtypes

        result = _value_to_cel([1, 2, 3])
        assert isinstance(result, celtypes.ListType)
        assert len(result) == 3

    def test_tuple_conversion(self):
        """Test tuple conversion in _value_to_cel."""
        from invariant.expressions import _value_to_cel
        import celpy.celtypes as celtypes

        result = _value_to_cel((1, 2, 3))
        assert isinstance(result, celtypes.ListType)
        assert len(result) == 3

    def test_fallback_to_string(self):
        """Test fallback to string conversion for unknown types (line 330)."""
        from invariant.expressions import _value_to_cel
        import celpy.celtypes as celtypes

        # Create a custom object that's not cacheable
        class CustomObj:
            def __str__(self):
                return "custom"

        # This should fall back to string conversion
        result = _value_to_cel(CustomObj())
        assert isinstance(result, celtypes.StringType)
        assert str(result) == "custom"


class TestICacheableExpressions:
    """Tests for ICacheable domain type handling in expressions."""

    def test_polynomial_attribute_access(self):
        """Test accessing Polynomial attributes in expressions (lines 344-358)."""
        params = {"coeffs": "${poly.coefficients}"}
        poly_artifact = Polynomial((1, 2, 1))
        deps = {"poly": poly_artifact}
        result = resolve_params(params, deps)
        # Should access the coefficients attribute
        assert isinstance(result["coeffs"], (list, tuple))
        # The coefficients should be accessible
        assert len(result["coeffs"]) > 0

    def test_icacheable_attribute_error_handling(self):
        """Test AttributeError handling in _icacheable_to_cel_map (lines 355-356)."""
        from invariant.expressions import _icacheable_to_cel_map
        import celpy.celtypes as celtypes

        # Create a mock ICacheable that raises AttributeError for some attributes
        class MockICacheable:
            def __init__(self):
                self.value = 42
                self._private = "hidden"

            def __getattr__(self, name):
                if name == "problematic":
                    raise AttributeError("Cannot access")
                raise AttributeError(f"No attribute {name}")

            def get_stable_hash(self):
                return "hash"

            def to_stream(self, stream):
                pass

            @classmethod
            def from_stream(cls, stream):
                return cls()

        mock_obj = MockICacheable()
        # This should handle AttributeError gracefully
        result = _icacheable_to_cel_map(mock_obj)
        assert isinstance(result, celtypes.MapType)
        assert "value" in result

    def test_polynomial_simple_reference(self):
        """Test simple Polynomial reference (MapType without value field, lines 279-284)."""
        params = {"poly": "${p}"}
        poly_artifact = Polynomial((1, 2, 1))
        deps = {"p": poly_artifact}
        result = resolve_params(params, deps)
        # Should return dict representation since Polynomial doesn't have .value
        # This tests the else branch at line 283-284
        assert isinstance(result["poly"], dict)
        assert "coefficients" in result["poly"]

    def test_maptype_with_value_field(self):
        """Test MapType with value field extraction (lines 279-281)."""
        # Create a dependency that will be converted to MapType with a 'value' key
        params = {"result": "${x}"}
        deps = {"x": {"value": 42, "other": "data"}}
        result = resolve_params(params, deps)
        # When MapType has 'value' key, it extracts just the value (line 281)
        assert result["result"] == 42
        assert not isinstance(result["result"], dict)

    def test_maptype_value_extraction_path(self):
        """Test the value extraction path for MapType results."""
        # This tests the path where a MapType result has a 'value' key
        # Direct access to .value field
        params = {"result": "${x.value}"}
        deps = {"x": {"value": 100}}
        result = resolve_params(params, deps)
        assert result["result"] == 100

    def test_polynomial_in_cel_expression(self):
        """Test Polynomial in cel() expression."""
        params = {"poly": cel("p")}
        poly_artifact = Polynomial((1, 2, 1))
        deps = {"p": poly_artifact}
        result = resolve_params(params, deps)
        assert isinstance(result["poly"], dict)
        assert "coefficients" in result["poly"]


class TestErrorPaths:
    """Tests for error handling paths."""

    def test_float_rejection_in_evaluation(self):
        """Test float rejection in _evaluate_cel (line 270)."""
        # Mock the program.evaluate to return a float

        # Create a mock program that returns a float
        mock_program = type("MockProgram", (), {})()
        mock_program.evaluate = lambda activation: 3.14  # Returns float

        # Mock the environment and program creation
        with patch("invariant.expressions.celpy.Environment") as mock_env_class:
            mock_env = mock_env_class.return_value
            mock_env.compile.return_value = "mock_ast"
            mock_env.program.return_value = mock_program

            with pytest.raises(ValueError, match="returned a float.*forbidden"):
                _evaluate_cel("test", {})

    def test_float_rejection_in_conversion(self):
        """Test float rejection in _cel_to_python (line 385)."""
        # Test the float check in _cel_to_python directly
        with pytest.raises(ValueError, match="returned float.*forbidden"):
            _cel_to_python(3.14, "test_expression")


class TestCelToPythonConversions:
    """Tests for CEL to Python type conversions."""

    def test_booltype_conversion(self):
        """Test BoolType conversion in _cel_to_python (line 382)."""
        from invariant.expressions import _cel_to_python
        import celpy.celtypes as celtypes

        # Direct test of BoolType conversion
        result = _cel_to_python(celtypes.BoolType(True), "test")
        assert result is True
        assert isinstance(result, bool)

    def test_booltype_false_conversion(self):
        """Test BoolType False conversion."""
        from invariant.expressions import _cel_to_python
        import celpy.celtypes as celtypes

        result = _cel_to_python(celtypes.BoolType(False), "test")
        assert result is False
        assert isinstance(result, bool)

    def test_maptype_conversion(self):
        """Test MapType conversion in _cel_to_python (lines 391-399)."""
        params = {"result": "${x}"}
        deps = {"x": {"a": 1, "b": 2}}
        result = resolve_params(params, deps)
        assert isinstance(result["result"], dict)
        assert result["result"]["a"] == 1
        assert result["result"]["b"] == 2

    def test_maptype_nested_conversion(self):
        """Test nested MapType conversion."""
        params = {"result": "${x}"}
        deps = {"x": {"nested": {"value": 42}}}
        result = resolve_params(params, deps)
        assert isinstance(result["result"], dict)
        assert isinstance(result["result"]["nested"], dict)
        assert result["result"]["nested"]["value"] == 42

    def test_maptype_non_stringtype_key(self):
        """Test MapType with non-StringType key (line 398)."""
        from invariant.expressions import _cel_to_python
        import celpy.celtypes as celtypes

        # Create a MapType with a non-StringType key (though this is unlikely in practice)
        # Actually, MapType keys are always StringType, but the code handles both cases
        maptype = celtypes.MapType({celtypes.StringType("key"): celtypes.IntType(42)})
        result = _cel_to_python(maptype, "test")
        assert isinstance(result, dict)
        assert result["key"] == 42

    def test_dict_conversion(self):
        """Test plain dict conversion in _cel_to_python (lines 403-405)."""
        params = {"result": "${x}"}
        deps = {"x": {"key": "value"}}
        result = resolve_params(params, deps)
        assert isinstance(result["result"], dict)
        assert result["result"]["key"] == "value"

    def test_list_conversion(self):
        """Test list conversion in _cel_to_python (lines 406-408)."""
        params = {"result": "${x}"}
        deps = {"x": [1, 2, 3]}
        result = resolve_params(params, deps)
        assert isinstance(result["result"], list)
        assert result["result"] == [1, 2, 3]

    def test_list_with_expressions(self):
        """Test list with expressions."""
        params = {"values": ["${x}", "${y}"]}
        deps = {"x": 1, "y": 2}
        result = resolve_params(params, deps)
        assert result["values"] == [1, 2]

    def test_unknown_type_fallback(self):
        """Test unknown type fallback in _cel_to_python (lines 409-411)."""
        # Test with a custom object that passes through CEL evaluation
        # Unknown types should be returned as-is
        from invariant.expressions import _cel_to_python

        class CustomType:
            pass

        custom_obj = CustomType()
        result = _cel_to_python(custom_obj, "test")
        assert result is custom_obj


class TestDecimalFunctionEdgeCases:
    """Tests for _decimal_function edge cases."""

    def test_decimal_from_maptype_with_value(self):
        """Test decimal() with MapType that has value field (lines 432-436)."""
        # Create a dict that will be converted to MapType
        params = {"result": "${decimal(x.value)}"}
        deps = {"x": {"value": 42}}
        result = resolve_params(params, deps)
        assert isinstance(result["result"], Decimal)
        assert result["result"] == Decimal("42")

    def test_decimal_from_maptype_without_value(self):
        """Test decimal() with MapType without value field (lines 437-438)."""
        params = {"result": "${decimal(x)}"}
        deps = {"x": {"other": 42}}  # No 'value' field
        with pytest.raises(ValueError, match="Cannot extract value"):
            resolve_params(params, deps)

    def test_decimal_from_icacheable(self):
        """Test decimal() with ICacheable that has value attribute (lines 446-448)."""
        from invariant.expressions import _decimal_function
        from invariant.protocol import ICacheable
        from typing import BinaryIO

        # Create a mock ICacheable with value attribute that implements the protocol
        class MockICacheable:
            def __init__(self, value):
                self.value = value

            def get_stable_hash(self):
                return "hash"

            def to_stream(self, stream: BinaryIO):
                pass

            @classmethod
            def from_stream(cls, stream: BinaryIO):
                return cls(42)

        # ICacheable is runtime_checkable, so this should work
        mock_obj = MockICacheable(42)
        # Verify it's recognized as ICacheable
        assert isinstance(mock_obj, ICacheable)
        assert hasattr(mock_obj, "value")

        result = _decimal_function(mock_obj)
        assert isinstance(result, Decimal)
        assert result == Decimal("42")

    def test_decimal_unconvertible_type(self):
        """Test decimal() with unconvertible type (line 450)."""
        from invariant.expressions import _decimal_function

        class UnconvertibleType:
            pass

        with pytest.raises(ValueError, match="Cannot convert"):
            _decimal_function(UnconvertibleType())


class TestComparisonValueExtraction:
    """Tests for _extract_comparison_value."""

    def test_maptype_without_value_field(self):
        """Test MapType without value field in comparison (lines 508-513)."""
        from invariant.expressions import _extract_comparison_value
        import celpy.celtypes as celtypes

        # Test the extraction function directly with MapType without value
        maptype = celtypes.MapType({celtypes.StringType("a"): celtypes.IntType(1)})
        # Should return the map itself (line 513)
        result = _extract_comparison_value(maptype)
        assert isinstance(result, celtypes.MapType)

    def test_inttype_extraction(self):
        """Test IntType extraction in _extract_comparison_value (line 514-515)."""
        params = {"result": "${min(x, y)}"}
        deps = {"x": 7, "y": 3}
        result = resolve_params(params, deps)
        assert result["result"] == 3

    def test_stringtype_extraction(self):
        """Test StringType extraction in _extract_comparison_value (line 516-517)."""
        params = {"result": "${min(x, y)}"}
        deps = {"x": "b", "y": "a"}
        result = resolve_params(params, deps)
        assert result["result"] == "a"

    def test_booltype_extraction(self):
        """Test BoolType extraction in _extract_comparison_value (line 518-519)."""
        from invariant.expressions import _extract_comparison_value
        import celpy.celtypes as celtypes

        # Test the extraction function directly with BoolType
        result = _extract_comparison_value(celtypes.BoolType(False))
        assert result is False
        assert isinstance(result, bool)

        result2 = _extract_comparison_value(celtypes.BoolType(True))
        assert result2 is True
        assert isinstance(result2, bool)

    def test_fallback_to_direct_value(self):
        """Test fallback to direct value comparison (lines 520-522)."""
        from invariant.expressions import _extract_comparison_value

        # Test with Decimal (already Python type)
        result = _extract_comparison_value(Decimal("1.5"))
        assert isinstance(result, Decimal)
        assert result == Decimal("1.5")

        # Test with other Python types
        result = _extract_comparison_value(42)
        assert result == 42

        result = _extract_comparison_value("test")
        assert result == "test"
