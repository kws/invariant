# Expressions Reference

This document is the normative reference for Invariant's parameter marker system and expression language. All three marker types — `ref()`, `cel()`, and `${...}` string interpolation — are defined here.

**Source of truth:** This document. If other documentation (AGENTS.md, README.md, architecture.md) conflicts with this reference, this document takes precedence.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Parameter Markers](#2-parameter-markers)
   - [ref() — Artifact Passthrough](#21-ref--artifact-passthrough)
   - [cel() — CEL Expression Evaluation](#22-cel--cel-expression-evaluation)
   - [${...} — String Interpolation](#23---string-interpolation)
   - [Literal Values](#24-literal-values)
3. [CEL Expression Language](#3-cel-expression-language)
   - [Variable Binding](#31-variable-binding)
   - [Field Access](#32-field-access)
   - [Integer Arithmetic](#33-integer-arithmetic)
   - [Decimal Arithmetic](#34-decimal-arithmetic)
   - [Built-in Functions](#35-built-in-functions)
   - [Standard CEL Operators](#36-standard-cel-operators)
4. [Type Conversion](#4-type-conversion)
   - [Artifact → CEL Binding](#41-artifact--cel-binding)
   - [CEL Result → Python](#42-cel-result--python)
5. [Nested Structures](#5-nested-structures)
6. [Execution Scope](#6-execution-scope)
7. [Error Cases](#7-error-cases)
8. [Examples](#8-examples)
9. [Implementation Flags](#9-implementation-flags)

---

## 1. Overview

Node parameters in Invariant are static values that may contain **markers** — special objects that are resolved at execution time during Phase 1 (Context Resolution). The resolution process transforms raw parameter values into a fully resolved **Manifest**.

```
Node params (with markers)  →  Phase 1 Resolution  →  Manifest (resolved values)
```

There are three marker types plus literal values:

| Marker | Purpose | Resolves to |
|:--|:--|:--|
| `ref("dep")` | Artifact passthrough | The ICacheable artifact object from dependency |
| `cel("expr")` | CEL expression evaluation | Computed value (int, str, Decimal, etc.) |
| `"text ${expr} text"` | String interpolation | Interpolated string |
| literal (`5`, `"#000"`) | Static value | Itself (no transformation) |

---

## 2. Parameter Markers

### 2.1 `ref()` — Artifact Passthrough

`ref(dep_name)` resolves to the **entire ICacheable artifact** produced by the named dependency. The artifact is passed through to the op's manifest without transformation.

**Import:** `from invariant import ref`

**Syntax:**

```python
ref("dependency_name")
```

**Behavior:**
- Resolves to the ICacheable object stored in `artifacts_by_node[dep_name]`
- The referenced dependency **must** be declared in the node's `deps` list
- Validated at Node creation time — a `ref()` referencing an undeclared dependency raises `ValueError` immediately

**Example — passing polynomial artifacts to an addition op:**

```python
Node(
    op_name="poly:add",
    params={"a": ref("p"), "b": ref("q")},
    deps=["p", "q"],
)
# Manifest after resolution: {"a": <Polynomial>, "b": <Polynomial>}
```

**Example — nested in a list (layers for compositing):**

```python
Node(
    op_name="gfx:composite",
    params={
        "layers": [
            {"image": ref("background"), "id": "bg"},
            {"image": ref("icon"), "pos": "align('bg', 'cc')"},
        ],
    },
    deps=["background", "icon"],
)
```

**Validation error — undeclared dependency:**

```python
# This raises ValueError at Node creation time:
Node(
    op_name="poly:add",
    params={"a": ref("p"), "b": ref("q")},
    deps=["p"],  # ERROR: "q" not declared
)
# ValueError: ref('q') in params references undeclared dependency.
```

### 2.2 `cel()` — CEL Expression Evaluation

`cel(expression)` evaluates a [CEL (Common Expression Language)](https://github.com/google/cel-spec) expression against the node's dependency artifacts and returns the computed value.

**Import:** `from invariant import cel`

**Syntax:**

```python
cel("expression")
```

**Behavior:**
- The expression string is compiled and evaluated using the CEL engine
- Dependency artifacts are exposed as CEL variables (see [Variable Binding](#31-variable-binding))
- Returns the evaluated result converted to a Python type
- Float results are **rejected** (see [Strict Numeric Policy](#34-decimal-arithmetic))

**Example — accessing a dependency's value:**

```python
Node(
    op_name="stdlib:from_integer",
    params={"value": cel("root_width.value")},
    deps=["root_width"],
)
# If root_width is Integer(144), manifest resolves to: {"value": 144}
```

**Example — decimal arithmetic:**

```python
Node(
    op_name="gfx:render_svg",
    params={"width": cel("decimal(background.width) * decimal('0.75')")},
    deps=["background"],
)
```

**Example — using min/max for canonicalization:**

```python
Node(
    op_name="stdlib:add",
    params={
        "a": cel("min(x.value, y.value)"),
        "b": cel("max(x.value, y.value)"),
    },
    deps=["x", "y"],
)
# Regardless of whether x=3,y=7 or x=7,y=3, manifest is always {"a": 3, "b": 7}
```

> **Note:** Unlike `ref()`, `cel()` markers are **not** validated at Node creation time for dependency references. A `cel()` expression referencing an undeclared dependency will only fail at execution time during Phase 1. See [Implementation Flag F-01](#f-01-cel-dependency-validation-timing).

### 2.3 `${...}` — String Interpolation

Strings containing `${expression}` delimiters evaluate the embedded CEL expression and substitute the result into the string.

**Syntax:**

```python
"text ${expression} more text"
```

**Behavior — two cases:**

1. **Whole-string expression** (`"${expr}"` with no surrounding text): Evaluates the expression and returns its **native type** (int, Decimal, etc.), not a string.
2. **Mixed text and expressions** (`"text ${expr} text"` or multiple `${...}`): Evaluates each expression, converts results to strings, and substitutes them into the text. Always returns a `str`.

**Example — whole-string expression (returns native type):**

```python
params = {"width": "${background.width}"}
deps = {"background": Integer(100)}
# Resolves to: {"width": 100}  (int, not str)
```

**Example — mixed text and expressions (returns string):**

```python
params = {"message": "Width is ${background.width}px"}
deps = {"background": Integer(100)}
# Resolves to: {"message": "Width is 100px"}  (str)
```

**Example — multiple expressions in one string:**

```python
params = {"label": "${x.value} + ${y.value} = ${x.value + y.value}"}
deps = {"x": Integer(3), "y": Integer(7)}
# Resolves to: {"label": "3 + 7 = 10"}
```

**Plain strings without `${...}` are passed through unchanged:**

```python
params = {"color": "#000000", "pos": "align('bg', 'cc')"}
# Resolves to: {"color": "#000000", "pos": "align('bg', 'cc')"}
```

### 2.4 Literal Values

Any value that is not `ref()`, `cel()`, or a string containing `${...}` is treated as a literal and passed through to the manifest unchanged.

```python
params = {
    "count": 5,            # int literal → 5
    "color": "#000",       # plain string → "#000"
    "flag": True,          # bool literal → True
    "items": [1, 2, 3],   # list literal → [1, 2, 3]
}
```

---

## 3. CEL Expression Language

Invariant uses [CEL (Common Expression Language)](https://github.com/google/cel-spec) for expression evaluation. CEL is a non-Turing-complete, side-effect-free expression language developed by Google.

**Why CEL:**
- **No side effects:** Expressions cannot perform I/O, mutate state, or access globals
- **Guaranteed termination:** No loops or recursion — every expression completes in bounded time
- **Deterministic:** Same inputs always produce the same output

These properties are intrinsic to the language, not constraints imposed on top of a general-purpose evaluator.

### 3.1 Variable Binding

When a `cel()` or `${...}` expression is evaluated, each dependency declared in the node's `deps` list is exposed as a CEL variable. The variable name is the dependency's node ID.

Artifacts are converted to CEL `MapType` objects, making field access work naturally:

```python
deps=["background", "icon_blob"]
# Inside expressions:
#   background       → MapType with artifact's fields
#   background.width  → the width field
#   icon_blob.data    → the data field
```

See [Artifact → CEL Binding](#41-artifact--cel-binding) for the full conversion rules.

### 3.2 Field Access

Artifact fields are accessed using dot notation:

```python
cel("background.width")     # Access the 'width' attribute
cel("background.value")     # Access the 'value' attribute
cel("x.value + y.value")    # Access .value on two artifacts
```

**Bare variable references** (e.g., `${x}` or `cel("x")`) resolve to the artifact's `.value` field if one exists. This is a convenience — `${x}` and `${x.value}` are equivalent for artifacts with a `.value` attribute.

### 3.3 Integer Arithmetic

Standard integer arithmetic is supported:

```python
cel("x.value + 1")          # Addition with literal
cel("x.value + y.value")    # Addition of two artifact values
cel("x.value * 2")          # Multiplication
cel("x.value - y.value")    # Subtraction
cel("1 + 2")                # Pure literal arithmetic (no dependencies needed)
```

All integer operations return `int` values.

### 3.4 Decimal Arithmetic

Per the **Strict Numeric Policy**, native `float` types are forbidden in cacheable data. Use the `decimal()` function for fractional arithmetic:

```python
cel('decimal("3.14")')                         # Decimal from string
cel('decimal("1.5") + decimal("2.5")')         # Decimal addition → Decimal("4.0")
cel('decimal(x.value)')                        # Integer to Decimal
cel('decimal("3.14") * 2')                     # Mixed Decimal/int multiplication
cel('decimal(background.width) * decimal("0.75")')  # Scale a dimension by 75%
```

**Rules:**
- Fractional literals **must** use `decimal("...")` with a **string** argument
- An expression whose final result is a `float` (CEL `double`) is **rejected** with a `ValueError`
- `decimal()` accepts: `int`, `str`, `Decimal`, `IntType`, `StringType`, or `MapType` with a `.value` field

### 3.5 Built-in Functions

Three custom functions are registered in addition to standard CEL:

| Function | Signature | Description |
|:--|:--|:--|
| `decimal(value)` | `(int \| str \| Decimal) → Decimal` | Constructs a `Decimal`. String form required for fractional values. |
| `min(a, b)` | `(comparable, comparable) → comparable` | Returns the smaller of two values. |
| `max(a, b)` | `(comparable, comparable) → comparable` | Returns the larger of two values. |

**`min()` and `max()` with artifacts:**

When called with artifact references (MapType), `min()` and `max()` extract the `.value` field for comparison but return the **original artifact**:

```python
cel("min(x, y)")    # Compares x.value vs y.value, returns the smaller artifact
cel("max(x, y)")    # Compares x.value vs y.value, returns the larger artifact
```

When called with scalar values, they return the scalar directly:

```python
cel("min(x.value, y.value)")    # Returns the smaller int value
cel("max(x.value, 10)")         # Returns the larger of x.value or 10
```

**Canonicalization pattern:** Use `min()`/`max()` to canonicalize operand order for commutative operations, ensuring cache hits regardless of argument ordering:

```python
# Both resolve to the same manifest {a: 3, b: 7}, producing the same digest
params_1 = {"a": cel("min(x, y)"), "b": cel("max(x, y)")}
params_2 = {"a": cel("min(y, x)"), "b": cel("max(y, x)")}
```

### 3.6 Standard CEL Operators

All standard CEL operators are available:

| Category | Operators |
|:--|:--|
| Arithmetic | `+`, `-`, `*`, `/`, `%` |
| Comparison | `==`, `!=`, `<`, `>`, `<=`, `>=` |
| Logical | `&&`, `\|\|`, `!` |
| Ternary | `condition ? a : b` |
| String functions | `size`, `contains`, `startsWith`, `endsWith`, `matches` |
| List/map operations | `in`, `size`, indexing |

---

## 4. Type Conversion

### 4.1 Artifact → CEL Binding

When an ICacheable artifact is bound as a CEL variable, it is converted to a `MapType` (CEL map). The conversion rules are:

| Artifact attribute type | CEL type |
|:--|:--|
| `int` | `IntType` |
| `str` | `StringType` |
| `bool` | `BoolType` |
| `Decimal` | `Decimal` (passed through as-is) |
| Other | `StringType(str(value))` |

**The `.value` attribute** (if present) is always included. All other **public, non-callable attributes** (not starting with `_`) are also exposed.

**Example:** An `Integer(42)` artifact is bound as:

```
MapType({
    "value": IntType(42)
})
```

### 4.2 CEL Result → Python

After expression evaluation, CEL types are converted back to Python:

| CEL type | Python type |
|:--|:--|
| `IntType` | `int` |
| `StringType` | `str` |
| `BoolType` | `bool` |
| `Decimal` | `Decimal` |
| `MapType` | If has `.value` key: extract and convert; otherwise: `dict` |
| `float` | **REJECTED** — raises `ValueError` |

---

## 5. Nested Structures

All three marker types can be nested inside `dict` and `list` structures. The resolver walks the structure recursively:

**Dict nesting:**

```python
params = {
    "config": {
        "width": cel("bg.value"),
        "color": "#000",
        "source": ref("icon_blob"),
    }
}
# Resolves each value independently within the nested dict
```

**List nesting:**

```python
params = {
    "layers": [
        {"image": ref("background"), "id": "bg"},
        {"image": ref("icon"), "pos": "align('bg', 'cc')"},
    ]
}
# Resolves ref() markers within each list element
```

**Mixed nesting:**

```python
params = {
    "values": ["${x.value}", "${y.value}"],
    "config": {"poly": ref("p"), "count": 5},
}
```

---

## 6. Execution Scope

When a `cel()` expression or `${...}` interpolation is evaluated, the following is available:

| Available | Description |
|:--|:--|
| **Dependency artifacts** | Each node ID declared in `deps` is available as a variable. Artifacts are exposed as CEL maps — field access (e.g., `background.width`) reads properties from the artifact. |
| **`decimal(value)`** | Constructs a Decimal from `int` or `string`. Fractional values **must** use string form (e.g., `decimal('0.75')`). |
| **`min(a, b)`** | Returns the minimum of two comparable values. |
| **`max(a, b)`** | Returns the maximum of two comparable values. |
| **Standard CEL operators** | Arithmetic, comparison, logical, ternary, string functions, list/map operations. |

The following is **not** available and will produce an error:

| Forbidden | Reason |
|:--|:--|
| **Undeclared dependencies** | Referencing a node ID not listed in `deps` is an error, even if that node exists in the graph. |
| **`double` (float) results** | An expression whose final result is a `float` is rejected at the manifest boundary. |
| **External state** | CEL cannot access the filesystem, network, system clock, or any state outside the expression scope. |

---

## 7. Error Cases

| Error | When | Exception |
|:--|:--|:--|
| `ref()` references undeclared dependency | Node creation time | `ValueError` |
| `ref()` references dependency not in artifacts | Phase 1 resolution | `ValueError` |
| `cel()` expression has invalid syntax | Phase 1 resolution | `ValueError` (wraps `CELParseError`) |
| `cel()` references undeclared variable | Phase 1 resolution | `ValueError` (wraps `CELEvalError`) |
| Expression returns `float` | Phase 1 resolution | `ValueError` |
| `${...}` in string has no matching `}` | Silent — treated as plain string | (no error) |

---

## 8. Examples

### 8.1 Basic Value Access

```python
from invariant import Node, cel, ref
from invariant.types import Integer

# Access a dependency's value attribute
Node(
    op_name="stdlib:from_integer",
    params={"value": cel("source.value")},
    deps=["source"],
)

# Equivalent using ${...} (whole-string expression returns native type)
Node(
    op_name="stdlib:from_integer",
    params={"value": "${source.value}"},
    deps=["source"],
)
```

### 8.2 Arithmetic on Dependencies

```python
# Scale a dimension by 75% using Decimal arithmetic
Node(
    op_name="gfx:render_svg",
    params={
        "width": cel("decimal(background.width) * decimal('0.75')"),
        "height": cel("decimal(background.height) * decimal('0.75')"),
        "svg": cel("icon_blob.data"),
    },
    deps=["background", "icon_blob"],
)
```

### 8.3 Commutative Canonicalization

```python
# Ensure add(x, y) and add(y, x) produce the same cache digest
Node(
    op_name="stdlib:add",
    params={
        "a": cel("min(x.value, y.value)"),
        "b": cel("max(x.value, y.value)"),
    },
    deps=["x", "y"],
)
```

### 8.4 String Interpolation

```python
# Build a descriptive message from artifact values
Node(
    op_name="log:info",
    params={"message": "Processing ${count.value} items at ${name.value}"},
    deps=["count", "name"],
)
```

### 8.5 Passing Whole Artifacts

```python
# Pass entire Polynomial artifacts to an addition op
Node(
    op_name="poly:add",
    params={"a": ref("p"), "b": ref("q")},
    deps=["p", "q"],
)
```

### 8.6 Complex Nested Structures

```python
# Composite operation with layers, mixing ref() and plain strings
Node(
    op_name="gfx:composite",
    params={
        "layers": [
            {"id": "bg", "image": ref("background")},
            {"image": ref("icon"), "pos": "align('bg', 'cc')"},
        ],
    },
    deps=["background", "icon"],
)
```

### 8.7 Decimal vs Float

```python
# CORRECT: Use decimal() for fractional values
params = {"scale": cel('decimal("0.75")')}   # → Decimal("0.75") ✓

# WRONG: Division that produces float is rejected
# params = {"scale": cel("3 / 4")}           # → ValueError (float result) ✗
```

---

## 9. Implementation Flags

The following items are **disagreements or ambiguities** between documentation and the current implementation. They are flagged here for resolution; no decision is made about whether documentation or implementation is correct.

---

### F-01: `cel()` Dependency Validation Timing

**Documentation says:** `ref()` markers are validated at Node creation time — every `ref("dep")` must reference a declared dependency in `deps`.

**Implementation confirms this for `ref()`**, but `cel()` markers are **not** validated at Node creation time. A `cel()` expression can reference dependency names that aren't in `deps`, and the error only surfaces at execution time during Phase 1.

**Impact:** Typos in `cel()` dependency names are not caught until execution. `ref()` catches them immediately.

**Source:** `node.py` `_validate_refs()` — only collects and validates `ref` instances, not `cel` instances.

---

### F-02: Context Values as Plain Dicts

**Documentation says** (architecture.md §7):
```python
root = {"width": 144, "height": 144}
results = executor.execute(graph, context={"root": root})
```

**Implementation requires** context values to be ICacheable. The executor calls `is_cacheable(value)` and then `to_cacheable(value)` on each context value. For plain dicts, `is_cacheable()` returns `True` (dicts with string keys and cacheable values are accepted), but `to_cacheable()` raises `NotImplementedError` because `DictArtifact` is not yet implemented.

**Impact:** The architecture.md example with `root` as a plain dict **does not work** with the current implementation. The e2e context tests work around this by using separate `Integer` values instead.

**Source:** `cacheable.py` `to_cacheable()` line 158 — `NotImplementedError` for container types.

---

### F-03: `poly:scale` Parameter Type

**Documentation says** (architecture.md §8.3): `poly:scale` takes `scalar: Integer`.

**Implementation:** `poly_scale(poly: Polynomial, scalar: int)` — takes native `int`, not `Integer`.

**Impact:** Minimal — the executor's type unwrapping (`_invoke_op`) would convert `Integer` → `int` when the function signature expects `int`. But the documented type annotation is inaccurate.

**Source:** `ops/poly.py` `poly_scale()` signature.

---

### F-04: OpRegistry Described as Singleton but Requires `clear()` in Tests

**Documentation says** (architecture.md §5.1): OpRegistry is a "singleton registry."

**Implementation:** OpRegistry uses `__new__` singleton pattern. Tests must call `registry.clear()` to reset state between tests, which is fragile and means the singleton pattern leaks state across test boundaries.

**Source:** `registry.py` `__new__` and `clear()`.

---

### F-05: Architecture Doc References "YAML/JSON Definition"

**Documentation says** (architecture.md §5.1): "Decouples the 'string' name in the YAML/JSON definition from the actual Python code."

**Implementation:** The system uses Python dict graph definitions exclusively. There is no YAML/JSON parser or loader.

**Impact:** Cosmetic — this appears to be aspirational language from the design doc. Not incorrect per se, but potentially misleading.

---

### F-06: `${expr}` Whole-String Return Type

**Documentation** does not explicitly state that `"${expr}"` returns the native type when the expression covers the entire string.

**Implementation:** When the `${...}` expression is the entire string content (after trimming), `_evaluate_expression()` returns the native CEL result (int, Decimal, etc.) rather than converting to string. For example, `"${x.value}"` where x is `Integer(100)` returns `100` (int), not `"100"` (string).

**Impact:** This is correct and desirable behavior, but should be explicitly documented. The current behavior means `"${expr}"` and `cel("expr")` are functionally equivalent when the expression covers the entire string.

**Source:** `expressions.py` `_evaluate_expression()` lines 201–204.

