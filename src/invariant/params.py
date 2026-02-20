"""Parameter markers for explicit dependency and expression references.

This module provides two marker types for node parameters:
- ref(dep): References an upstream dependency artifact directly
- cel(expr): Evaluates a CEL expression against dependency artifacts
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ref:
    """Reference to an upstream dependency artifact.

    When used in node params, resolves to the ICacheable object from the
    specified dependency. The dependency must be declared in the node's deps list.

    Example:
        Node(
            op_name="poly:add",
            params={"a": ref("p"), "b": ref("q")},
            deps=["p", "q"],
        )
    """

    dep: str


@dataclass(frozen=True)
class cel:
    """CEL expression to evaluate against dependency artifacts.

    When used in node params, evaluates the CEL expression with dependency
    artifacts exposed as variables. Returns the computed value (int, str,
    Decimal, etc.).

    Example:
        Node(
            op_name="gfx:render_svg",
            params={"width": cel("decimal(background.width) * decimal('0.75')")},
            deps=["background"],
        )
    """

    expr: str
