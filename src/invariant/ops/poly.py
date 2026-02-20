"""Polynomial operations for testing Invariant's DAG capabilities."""

from typing import Any

from invariant.types import Polynomial


def poly_from_coefficients(coefficients: list[int]) -> Polynomial:
    """Create a polynomial from a list of coefficients.

    Args:
        coefficients: List of integer coefficients. Index i represents
                     the coefficient of x^i. Trailing zeros are automatically
                     stripped for canonical form.

    Returns:
        Polynomial with the given coefficients (trailing zeros stripped).

    Raises:
        TypeError: If coefficients are not integers.
    """
    # Ensure all coefficients are integers
    int_coeffs = []
    for i, coeff in enumerate(coefficients):
        if not isinstance(coeff, int):
            raise TypeError(f"Coefficient at index {i} must be int, got {type(coeff)}")
        int_coeffs.append(coeff)

    return Polynomial(int_coeffs)


def poly_add(a: Polynomial, b: Polynomial) -> Polynomial:
    """Add two polynomials.

    Args:
        a: First polynomial.
        b: Second polynomial.

    Returns:
        Polynomial representing the sum.
    """
    max_len = max(len(a.coefficients), len(b.coefficients))
    result_coeffs = []
    for i in range(max_len):
        coeff_a = a.coefficients[i] if i < len(a.coefficients) else 0
        coeff_b = b.coefficients[i] if i < len(b.coefficients) else 0
        result_coeffs.append(coeff_a + coeff_b)
    return Polynomial(tuple(result_coeffs))


def poly_multiply(a: Polynomial, b: Polynomial) -> Polynomial:
    """Multiply two polynomials (convolution of coefficient lists).

    Args:
        a: First polynomial.
        b: Second polynomial.

    Returns:
        Polynomial representing the product.
    """
    # Result degree is len(a) + len(b) - 2 (0-indexed)
    result_len = len(a.coefficients) + len(b.coefficients) - 1
    result_coeffs = [0] * result_len

    # Convolution: result[i+j] += a[i] * b[j]
    for i, coeff_a in enumerate(a.coefficients):
        for j, coeff_b in enumerate(b.coefficients):
            result_coeffs[i + j] += coeff_a * coeff_b

    return Polynomial(tuple(result_coeffs))


def poly_scale(poly: Polynomial, scalar: int) -> Polynomial:
    """Scale a polynomial by a scalar.

    Args:
        poly: Polynomial to scale.
        scalar: Integer scalar value.

    Returns:
        Polynomial with all coefficients multiplied by scalar.
    """
    # Multiply each coefficient by scalar
    new_coeffs = tuple(c * scalar for c in poly.coefficients)
    return Polynomial(new_coeffs)


def poly_derivative(poly: Polynomial) -> Polynomial:
    """Compute the derivative of a polynomial.

    The derivative of c[i] * x^i is c[i] * i * x^(i-1), which means
    we multiply each coefficient by its index and shift down one degree.

    Args:
        poly: Polynomial to differentiate.

    Returns:
        Polynomial representing the derivative.
    """
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


def poly_evaluate(poly: Polynomial, x: int) -> int:
    """Evaluate a polynomial at a point using Horner's method.

    Args:
        poly: Polynomial to evaluate.
        x: Integer value to evaluate at.

    Returns:
        Integer result of evaluation.
    """
    # Horner's method: evaluate from highest degree down
    # For polynomial c[0] + c[1]*x + c[2]*x^2 + ... + c[n]*x^n
    # Start with result = c[n], then result = result * x + c[n-1], etc.
    result = 0
    for i in range(len(poly.coefficients) - 1, -1, -1):
        result = result * x + poly.coefficients[i]

    return result


# Package of polynomial operations
OPS: dict[str, Any] = {
    "from_coefficients": poly_from_coefficients,
    "add": poly_add,
    "multiply": poly_multiply,
    "evaluate": poly_evaluate,
    "scale": poly_scale,
    "derivative": poly_derivative,
}
