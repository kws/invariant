"""Standard operations library."""

from invariant.ops import poly, stdlib
from invariant.ops.stdlib import (
    add,
    dict_get,
    dict_merge,
    from_integer,
    identity,
    list_append,
    multiply,
)

__all__ = [
    "poly",
    "stdlib",
    "identity",
    "add",
    "multiply",
    "from_integer",
    "dict_get",
    "dict_merge",
    "list_append",
]
