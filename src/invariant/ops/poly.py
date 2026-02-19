"""Polynomial operations for testing Invariant's DAG capabilities."""

from typing import Any

from invariant.protocol import ICacheable
from invariant.types import Integer, Polynomial


def poly_from_coefficients(manifest: dict[str, Any]) -> ICacheable:
    """Create a polynomial from a list of coefficients.

    Args:
        manifest: Must contain 'coefficients' key with a list of integers.

    Returns:
        Polynomial with the given coefficients (trailing zeros stripped).

    Raises:
        KeyError: If 'coefficients' key is missing.
        TypeError: If coefficients are not integers.
    """
    if "coefficients" not in manifest:
        raise KeyError("poly:from_coefficients op requires 'coefficients' in manifest")

    coefficients = manifest["coefficients"]
    if not isinstance(coefficients, list):
        raise TypeError(f"coefficients must be a list, got {type(coefficients)}")

    # Ensure all coefficients are integers
    int_coeffs = []
    for i, coeff in enumerate(coefficients):
        if isinstance(coeff, Integer):
            int_coeffs.append(coeff.value)
        elif isinstance(coeff, int):
            int_coeffs.append(coeff)
        else:
            raise TypeError(f"Coefficient at index {i} must be int, got {type(coeff)}")

    return Polynomial(int_coeffs)


def poly_add(manifest: dict[str, Any]) -> ICacheable:
    """Add two polynomials.

    Args:
        manifest: Must contain two Polynomial artifacts. These can come from:
                 - Explicit params 'a' and 'b'
                 - Dependencies (first two deps are used as 'a' and 'b')

    Returns:
        Polynomial representing the sum.

    Raises:
        ValueError: If two polynomials are not found in manifest.
    """
    a, b = _extract_two_polynomials(manifest, "poly:add")
    return _add_polynomials(a, b)


def poly_multiply(manifest: dict[str, Any]) -> ICacheable:
    """Multiply two polynomials (convolution of coefficient lists).

    Args:
        manifest: Must contain two Polynomial artifacts. These can come from:
                 - Explicit params 'a' and 'b'
                 - Dependencies (first two deps are used as 'a' and 'b')

    Returns:
        Polynomial representing the product.

    Raises:
        ValueError: If two polynomials are not found in manifest.
    """
    a, b = _extract_two_polynomials(manifest, "poly:multiply")
    return _multiply_polynomials(a, b)


def poly_scale(manifest: dict[str, Any]) -> ICacheable:
    """Scale a polynomial by a scalar.

    Args:
        manifest: Must contain:
                 - 'poly': Polynomial artifact
                 - 'scalar': Integer scalar value

    Returns:
        Polynomial with all coefficients multiplied by scalar.

    Raises:
        KeyError: If required keys are missing.
        TypeError: If types are incorrect.
    """
    if "poly" not in manifest and "scalar" not in manifest:
        # Try to extract from dependencies
        polynomials = [v for v in manifest.values() if isinstance(v, Polynomial)]
        integers = [v for v in manifest.values() if isinstance(v, Integer)]
        if len(polynomials) == 1 and len(integers) == 1:
            poly = polynomials[0]
            scalar = integers[0].value
        else:
            raise KeyError("poly:scale op requires 'poly' and 'scalar' in manifest")
    else:
        poly = manifest["poly"]
        scalar = manifest["scalar"]

    if not isinstance(poly, Polynomial):
        raise TypeError(f"poly must be Polynomial, got {type(poly)}")

    if isinstance(scalar, Integer):
        scalar = scalar.value
    elif not isinstance(scalar, int):
        raise TypeError(f"scalar must be int or Integer, got {type(scalar)}")

    # Multiply each coefficient by scalar
    new_coeffs = tuple(c * scalar for c in poly.coefficients)
    return Polynomial(new_coeffs)


def poly_derivative(manifest: dict[str, Any]) -> ICacheable:
    """Compute the derivative of a polynomial.

    The derivative of c[i] * x^i is c[i] * i * x^(i-1), which means
    we multiply each coefficient by its index and shift down one degree.

    Args:
        manifest: Must contain a Polynomial artifact. Can come from:
                 - Explicit param 'poly'
                 - Single dependency

    Returns:
        Polynomial representing the derivative.

    Raises:
        ValueError: If polynomial is not found in manifest.
    """
    poly = _extract_single_polynomial(manifest, "poly:derivative")

    # Derivative: c[i] * i becomes the coefficient of x^(i-1)
    # For i=0, the derivative is 0 (constant term disappears)
    if len(poly.coefficients) <= 1:
        # Constant or zero polynomial -> derivative is zero
        return Polynomial((0,))

    new_coeffs = []
    for i in range(1, len(poly.coefficients)):
        # Coefficient at index i becomes i * coeff[i] at index i-1
        new_coeffs.append(poly.coefficients[i] * i)

    return Polynomial(tuple(new_coeffs))


def poly_evaluate(manifest: dict[str, Any]) -> ICacheable:
    """Evaluate a polynomial at a point using Horner's method.

    Args:
        manifest: Must contain:
                 - 'poly': Polynomial artifact
                 - 'x': Integer value to evaluate at

    Returns:
        Integer result of evaluation.

    Raises:
        KeyError: If required keys are missing.
        TypeError: If types are incorrect.
    """
    # Try explicit params first
    if "poly" in manifest and "x" in manifest:
        poly = manifest["poly"]
        x = manifest["x"]
    else:
        # Try to extract from dependencies
        polynomials = [v for v in manifest.values() if isinstance(v, Polynomial)]
        integers = [v for v in manifest.values() if isinstance(v, Integer)]
        if len(polynomials) == 1 and len(integers) == 1:
            poly = polynomials[0]
            x = integers[0].value
        else:
            raise KeyError("poly:evaluate op requires 'poly' and 'x' in manifest")

    if not isinstance(poly, Polynomial):
        raise TypeError(f"poly must be Polynomial, got {type(poly)}")

    if isinstance(x, Integer):
        x = x.value
    elif not isinstance(x, int):
        raise TypeError(f"x must be int or Integer, got {type(x)}")

    # Horner's method: evaluate from highest degree down
    # For polynomial c[0] + c[1]*x + c[2]*x^2 + ... + c[n]*x^n
    # Start with result = c[n], then result = result * x + c[n-1], etc.
    result = 0
    for i in range(len(poly.coefficients) - 1, -1, -1):
        result = result * x + poly.coefficients[i]

    return Integer(result)


def _extract_two_polynomials(
    manifest: dict[str, Any], op_name: str
) -> tuple[Polynomial, Polynomial]:
    """Extract two Polynomial artifacts from manifest.

    Tries explicit params 'a' and 'b' first, then falls back to
    finding Polynomial values from dependencies.

    Args:
        manifest: The manifest dictionary.
        op_name: Operation name (for error messages).

    Returns:
        Tuple of two Polynomial objects.

    Raises:
        ValueError: If two polynomials are not found.
    """
    # Try explicit params first
    if "a" in manifest and "b" in manifest:
        a = manifest["a"]
        b = manifest["b"]
        if isinstance(a, Polynomial) and isinstance(b, Polynomial):
            return (a, b)

    # Fall back to finding Polynomial values in manifest
    polynomials = [v for v in manifest.values() if isinstance(v, Polynomial)]
    if len(polynomials) >= 2:
        return (polynomials[0], polynomials[1])
    elif len(polynomials) == 1:
        raise ValueError(
            f"{op_name} requires two Polynomial operands, found only one in manifest"
        )
    else:
        raise ValueError(
            f"{op_name} requires two Polynomial operands, found none in manifest"
        )


def _extract_single_polynomial(manifest: dict[str, Any], op_name: str) -> Polynomial:
    """Extract a single Polynomial artifact from manifest.

    Tries explicit param 'poly' first, then falls back to finding
    a Polynomial value from dependencies.

    Args:
        manifest: The manifest dictionary.
        op_name: Operation name (for error messages).

    Returns:
        Polynomial object.

    Raises:
        ValueError: If polynomial is not found.
    """
    # Try explicit param first
    if "poly" in manifest:
        poly = manifest["poly"]
        if isinstance(poly, Polynomial):
            return poly

    # Fall back to finding Polynomial value in manifest
    polynomials = [v for v in manifest.values() if isinstance(v, Polynomial)]
    if len(polynomials) >= 1:
        return polynomials[0]
    else:
        raise ValueError(
            f"{op_name} requires a Polynomial operand, found none in manifest"
        )


def _add_polynomials(a: Polynomial, b: Polynomial) -> Polynomial:
    """Add two polynomials (pairwise addition, zero-pad shorter polynomial).

    Args:
        a: First polynomial.
        b: Second polynomial.

    Returns:
        Sum of the two polynomials.
    """
    max_len = max(len(a.coefficients), len(b.coefficients))
    result_coeffs = []
    for i in range(max_len):
        coeff_a = a.coefficients[i] if i < len(a.coefficients) else 0
        coeff_b = b.coefficients[i] if i < len(b.coefficients) else 0
        result_coeffs.append(coeff_a + coeff_b)
    return Polynomial(tuple(result_coeffs))


def _multiply_polynomials(a: Polynomial, b: Polynomial) -> Polynomial:
    """Multiply two polynomials (convolution of coefficient lists).

    Args:
        a: First polynomial.
        b: Second polynomial.

    Returns:
        Product of the two polynomials.
    """
    # Result degree is len(a) + len(b) - 2 (0-indexed)
    result_len = len(a.coefficients) + len(b.coefficients) - 1
    result_coeffs = [0] * result_len

    # Convolution: result[i+j] += a[i] * b[j]
    for i, coeff_a in enumerate(a.coefficients):
        for j, coeff_b in enumerate(b.coefficients):
            result_coeffs[i + j] += coeff_a * coeff_b

    return Polynomial(tuple(result_coeffs))
