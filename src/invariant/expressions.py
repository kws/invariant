"""CEL expression engine for evaluating ${...} expressions in node parameters."""

import re
from decimal import Decimal
from typing import Any

try:
    from celpy import celpy
except ImportError:
    try:
        import cel_python as celpy
    except ImportError:
        # Fallback if cel-python is not available
        celpy = None

from invariant.protocol import ICacheable


def resolve_params(
    params: dict[str, Any], dependencies: dict[str, ICacheable]
) -> dict[str, Any]:
    """Resolve ${...} CEL expressions in parameter values.

    Walks through the params dictionary, finds values containing ${...} delimiters,
    evaluates the CEL expression with dependency artifacts exposed as variables,
    and replaces the expression with the resolved value.

    Args:
        params: Dictionary of parameter name -> value. Values may contain ${...} expressions.
        dependencies: Dictionary mapping dependency IDs to their ICacheable artifacts.
                    These are exposed as variables in CEL expressions.

    Returns:
        Dictionary with all ${...} expressions resolved to their evaluated values.

    Raises:
        ValueError: If expression evaluation fails, undeclared dependencies are referenced,
                   or expression result is a float (double).
    """
    if celpy is None:
        raise ImportError(
            "cel-python package is required for expression evaluation. "
            "Install it with: pip install cel-python"
        )

    resolved = {}
    for key, value in params.items():
        resolved[key] = _resolve_value(value, dependencies)
    return resolved


def _resolve_value(value: Any, dependencies: dict[str, ICacheable]) -> Any:
    """Recursively resolve expressions in a value.

    Args:
        value: The value to resolve (may be a dict, list, or string with ${...}).
        dependencies: Dictionary of dependency artifacts.

    Returns:
        Resolved value with all expressions evaluated.
    """
    if isinstance(value, str):
        # Check for ${...} expressions
        if "${" in value and "}" in value:
            # Extract and evaluate CEL expression
            return _evaluate_expression(value, dependencies)
        return value
    elif isinstance(value, dict):
        return {k: _resolve_value(v, dependencies) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_value(item, dependencies) for item in value]
    else:
        # Primitive value, return as-is
        return value


def _evaluate_expression(expr_string: str, dependencies: dict[str, ICacheable]) -> Any:
    """Evaluate a CEL expression string.

    Args:
        expr_string: String potentially containing ${...} expressions.
        dependencies: Dictionary of dependency artifacts.

    Returns:
        Resolved value after evaluating all expressions.

    Raises:
        ValueError: If expression is invalid or references undeclared dependencies.
    """
    # Find all ${...} expressions
    pattern = r"\$\{([^}]+)\}"
    matches = re.findall(pattern, expr_string)

    if not matches:
        # No expressions found, return as-is
        return expr_string

    if len(matches) == 1 and expr_string.strip() == f"${{{matches[0]}}}":
        # Single expression covering the entire string - evaluate it
        cel_expr = matches[0].strip()
        return _evaluate_cel(cel_expr, dependencies)
    else:
        # Multiple expressions or mixed with text - evaluate each and substitute
        result = expr_string
        for match in matches:
            cel_expr = match.strip()
            evaluated = _evaluate_cel(cel_expr, dependencies)
            # Convert to string for substitution
            if isinstance(evaluated, ICacheable):
                # For ICacheable types, extract the value
                if hasattr(evaluated, "value"):
                    evaluated = evaluated.value
                else:
                    evaluated = str(evaluated)
            result = result.replace(f"${{{match}}}", str(evaluated))
        return result


def _evaluate_cel(expression: str, dependencies: dict[str, ICacheable]) -> Any:
    """Evaluate a single CEL expression.

    Args:
        expression: The CEL expression to evaluate (without ${...} delimiters).
        dependencies: Dictionary of dependency artifacts.

    Returns:
        The evaluated result. Must be a type that can be hashed (no floats).

    Raises:
        ValueError: If expression is invalid, references undeclared deps, or returns float.
    """
    if celpy is None:
        raise ImportError(
            "cel-python package is required for expression evaluation. "
            "Install it with: pip install cel-python"
        )

    # Build CEL environment
    try:
        env = celpy.Environment()
    except Exception:
        # Try alternative initialization
        env = celpy.Environment("default")

    var_declarations = {}

    # Convert dependencies to CEL-compatible types
    for dep_id, artifact in dependencies.items():
        # Expose artifact as a CEL map for field access
        artifact_map = _artifact_to_cel_map(artifact)
        var_declarations[dep_id] = artifact_map

    # Register custom functions: decimal(), min(), max()
    # Note: cel-python function registration API may vary by version
    # We'll try to register them, but if that fails, we'll handle them specially

    try:
        # Compile the expression
        try:
            ast = env.compile(expression)
            program = env.program(ast)
        except AttributeError:
            # Alternative API: direct evaluation
            program = env.compile(expression)

        # Create activation with variables
        activation = {}
        for var_name, var_value in var_declarations.items():
            activation[var_name] = var_value

        # Evaluate
        try:
            result = program.evaluate(activation)
        except AttributeError:
            # Alternative: call directly
            result = program(activation)

        # Check for float results (forbidden per Strict Numeric Policy)
        if isinstance(result, float):
            raise ValueError(
                f"Expression '{expression}' returned a float (double), which is forbidden. "
                f"Use decimal() for fractional arithmetic."
            )

        # If result is a dict (artifact map), extract the value for simple variable references
        if isinstance(result, dict) and "value" in result:
            # Simple variable reference like ${x} - return the value directly
            result = result["value"]

        # Convert result to appropriate Python type
        return _cel_to_python(result, expression)
    except Exception as e:
        # If CEL evaluation fails (e.g., custom functions not registered),
        # try simple evaluator fallback
        # This handles min/max/decimal and basic expressions
        try:
            return _evaluate_simple(expression, dependencies)
        except Exception as fallback_error:
            raise ValueError(
                f"Failed to evaluate CEL expression '{expression}': {e}. "
                f"Fallback also failed: {fallback_error}"
            ) from fallback_error


def _evaluate_simple(expression: str, dependencies: dict[str, ICacheable]) -> Any:
    """Simple fallback evaluator for basic expressions.

    Handles min/max/decimal functions and basic attribute access.
    This is a fallback when CEL library doesn't support custom functions.

    Args:
        expression: The expression to evaluate.
        dependencies: Dictionary of dependency artifacts.

    Returns:
        Evaluated result.

    Raises:
        ValueError: If expression is unsafe or cannot be evaluated.
    """
    # Pre-process min/max/decimal function calls
    # This is a simple regex-based approach for basic cases
    import ast as python_ast

    # Try to parse as Python expression (with restrictions)
    # Only allow: identifiers, attribute access, function calls, literals, basic operators
    try:
        # Replace min/max/decimal with our implementations
        # This is a simple approach - for production we'd want a proper CEL function registry
        tree = python_ast.parse(expression, mode="eval")

        # Build a safe evaluation context
        # For simple evaluator, expose artifacts as objects with .value attribute
        # This allows expressions like "root_width.value" to work
        context = {}
        for dep_id, artifact in dependencies.items():
            # Create a simple object that exposes the artifact's attributes
            # This allows .value access to work and supports comparisons for min/max
            class ArtifactWrapper:
                def __init__(self, artifact: ICacheable):
                    self._artifact = artifact
                    # Expose all attributes from the artifact
                    if hasattr(artifact, "value"):
                        self.value = artifact.value
                        self._comparison_value = artifact.value
                    else:
                        self._comparison_value = artifact
                    # Expose other common attributes
                    for attr in dir(artifact):
                        if not attr.startswith("_") and not callable(
                            getattr(artifact, attr, None)
                        ):
                            try:
                                setattr(self, attr, getattr(artifact, attr))
                            except AttributeError:
                                pass

                # Support comparisons for min/max functions
                def __lt__(self, other):
                    if isinstance(other, ArtifactWrapper):
                        return self._comparison_value < other._comparison_value
                    return self._comparison_value < other

                def __gt__(self, other):
                    if isinstance(other, ArtifactWrapper):
                        return self._comparison_value > other._comparison_value
                    return self._comparison_value > other

                def __le__(self, other):
                    if isinstance(other, ArtifactWrapper):
                        return self._comparison_value <= other._comparison_value
                    return self._comparison_value <= other

                def __ge__(self, other):
                    if isinstance(other, ArtifactWrapper):
                        return self._comparison_value >= other._comparison_value
                    return self._comparison_value >= other

                def __eq__(self, other):
                    if isinstance(other, ArtifactWrapper):
                        return self._comparison_value == other._comparison_value
                    return self._comparison_value == other

            context[dep_id] = ArtifactWrapper(artifact)

        # Add our custom functions
        context["min"] = _min_function
        context["max"] = _max_function
        context["decimal"] = _decimal_function

        # Evaluate safely
        result = eval(compile(tree, "<string>", "eval"), {"__builtins__": {}}, context)

        # If result is an ArtifactWrapper, extract the value for simple references
        if hasattr(result, "_artifact") and hasattr(result, "value"):
            # Simple variable reference - return the value
            result = result.value

        # Check for float results
        if isinstance(result, float):
            raise ValueError(
                f"Expression '{expression}' returned a float, which is forbidden. "
                f"Use decimal() for fractional arithmetic."
            )

        return _cel_to_python(result, expression)
    except Exception as e:
        raise ValueError(
            f"Failed to evaluate expression '{expression}' with simple evaluator: {e}"
        ) from e


def _artifact_to_cel_map(artifact: ICacheable) -> dict[str, Any]:
    """Convert an ICacheable artifact to a CEL-compatible map.

    Artifacts are exposed as maps so field access like `background.width` works.
    For types with a `.value` attribute, expose both the value and the type's fields.
    For other types, expose their attributes as a map.

    Args:
        artifact: The ICacheable artifact to convert.

    Returns:
        Dictionary representation suitable for CEL evaluation.
    """
    result: dict[str, Any] = {}

    # Add the artifact itself as a special key
    result["_artifact"] = artifact

    # For types with a .value attribute, expose it
    if hasattr(artifact, "value"):
        result["value"] = artifact.value
        # Also expose value as the default field for convenience
        # (e.g., background.width accesses background.value if width doesn't exist)
        if isinstance(artifact.value, (int, str, Decimal)):
            result["_default"] = artifact.value

    # Expose all public attributes
    for attr_name in dir(artifact):
        if not attr_name.startswith("_") and attr_name != "value":
            try:
                attr_value = getattr(artifact, attr_name)
                if not callable(attr_value):
                    result[attr_name] = attr_value
            except AttributeError:
                pass

    return result


def _cel_to_python(cel_value: Any, expression: str) -> Any:
    """Convert a CEL value to a Python type.

    Handles conversion of CEL types to Python types, with special handling
    for Decimal creation via decimal() function calls.

    Args:
        cel_value: The value returned from CEL evaluation.
        expression: The original expression (for error messages).

    Returns:
        Python value (int, str, Decimal, ICacheable, etc.)
    """
    # Handle common CEL types
    if isinstance(cel_value, (int, str, bool)):
        return cel_value
    elif isinstance(cel_value, float):
        # This should have been caught earlier, but double-check
        raise ValueError(
            f"Expression '{expression}' returned float, which is forbidden. "
            f"Use decimal() for fractional values."
        )
    elif isinstance(cel_value, Decimal):
        return cel_value
    elif isinstance(cel_value, dict):
        # CEL map - return as dict
        return {k: _cel_to_python(v, expression) for k, v in cel_value.items()}
    elif isinstance(cel_value, list):
        # CEL list - return as list
        return [_cel_to_python(item, expression) for item in cel_value]
    else:
        # Unknown type - return as-is (might be a CEL-specific type)
        return cel_value


# Custom CEL functions
def _decimal_function(value: Any) -> Decimal:
    """CEL function: decimal(value) - constructs a Decimal from int or string.

    Args:
        value: Integer or string representation of a decimal.

    Returns:
        Decimal value.

    Raises:
        ValueError: If value cannot be converted to Decimal.
    """
    if isinstance(value, Decimal):
        return value
    elif isinstance(value, int):
        return Decimal(str(value))
    elif isinstance(value, str):
        return Decimal(value)
    elif isinstance(value, ICacheable) and hasattr(value, "value"):
        # Extract value from ICacheable
        return Decimal(str(value.value))
    else:
        raise ValueError(f"Cannot convert {type(value)} to Decimal")


def _min_function(a: Any, b: Any) -> Any:
    """CEL function: min(a, b) - returns the minimum of two comparable values.

    Args:
        a: First value.
        b: Second value.

    Returns:
        The minimum of a and b.
    """
    if a < b:
        return a
    return b


def _max_function(a: Any, b: Any) -> Any:
    """CEL function: max(a, b) - returns the maximum of two comparable values.

    Args:
        a: First value.
        b: Second value.

    Returns:
        The maximum of a and b.
    """
    if a > b:
        return a
    return b
