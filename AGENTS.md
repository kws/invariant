# **AGENTS.md: Essential Information for AI Agents**

This document provides must-know information about the Invariant system. For comprehensive details, see [architecture.md](./architecture.md).

## **What is Invariant?**

Invariant is a Python-based deterministic execution engine for DAGs (directed acyclic graphs). It treats every operation as a pure function: `Op(Input) = Output`.

**Core Value:**
- **Aggressive Caching:** Artifacts are reused across runs if inputs match
- **Deduplication:** Identical operations execute only once
- **Reproducibility:** Bit-for-bit identical outputs across runs

## **Development Setup**

**This project uses uv for dependency management and testing.**

- **Run tests:** `uv run pytest tests/` or `uv run pytest tests/test_file.py::test_name`
- **Install dependencies:** `uv sync`
- **Run Python commands:** `uv run python ...`
- **DO NOT** use bare `python`, `pytest`, or `python -m pytest` — always use `uv run` first

## **Critical Constraints (MUST FOLLOW)**

### **1. Immutability Contract**
- Once an **Artifact** is generated, it is **frozen**
- Downstream nodes **cannot modify** upstream artifacts
- Must consume and produce a **new** artifact

### **2. Determinism Contract**
- An **Op** must rely **only** on data in its **Input Manifest**
- **FORBIDDEN:** Global state, `time.now()`, `random.random()` inside Ops
- Exception: These values can be passed as explicit inputs from graph root

### **3. Strict Numeric Policy**
- **FORBIDDEN:** Native `float` types in cacheable data
- **REASON:** IEEE 754 floats are non-deterministic across architectures
- **SOLUTION:** Use `decimal.Decimal` (canonicalized to string) or integer ratios

## **Core Terminology**

| Term | Definition | Key Point |
| :---- | :---- | :---- |
| **Node** | Vertex in DAG defining *what* to do | Contains op name, params (with ref/cel markers), upstream deps |
| **Op** | Plain Python function with typed parameters | Pure function: Op(Input) = Output. Executor maps params to args by name |
| **Manifest** | Fully resolved dictionary of params for a Node | Built from resolved params only (no dep injection) |
| **Artifact** | Immutable output produced by an Op | Frozen once created, must be cacheable |
| **Digest** | SHA-256 hash of a Manifest | Serves as cache key/identity |
| **ref(dep)** | Param marker for artifact passthrough | Resolves to artifact from dependency (native type or ICacheable domain type) |
| **cel(expr)** | Param marker for CEL expression | Evaluates expression, returns computed value |

## **Cacheable Type Universe**

All data passed between Nodes must be **cacheable** (validated by `is_cacheable()`):

**Supported native types:**
- `int`, `str`, `bool`, `None`
- `Decimal` (safe numerics — no `float`!)
- `dict[str, Cacheable]`, `list[Cacheable]`, `tuple[Cacheable, ...]`

**ICacheable Protocol** (for domain types like `Polynomial`):

Domain types that require custom serialization implement this protocol:

```python
class ICacheable(Protocol):
    def get_stable_hash(self) -> str:
        """Returns deterministic SHA-256 hash of object's structural state."""
        ...
    
    def to_stream(self, stream: BinaryIO) -> None:
        """Serializes object to binary stream for persistent storage."""
        ...
    
    @classmethod
    def from_stream(cls, stream: BinaryIO) -> 'ICacheable':
        """Hydrates object from binary stream."""
        ...
```

Native types are stored directly without wrapping. The store codec handles serialization of all cacheable types uniformly.

## **Execution Model: Two Phases**

For each node in topological order, the executor runs two phases. For the complete normative reference, see [docs/executor.md](./docs/executor.md).

### **Phase 1: Context Resolution (Graph → Manifest)**
1. Traverse DAG, resolve param markers (`ref()`, `cel()`, `${...}`) for each Node
2. `ref("dep")` → resolves to artifact from dependency (native type or ICacheable domain type)
3. `cel("expr")` → evaluates CEL expression against dependency artifacts
4. `"${expr}"` → evaluates CEL expression and interpolates into string
5. Recursively calculate hash for all resolved values (using `hash_value()` for native types, `get_stable_hash()` for ICacheable)
6. Assemble canonical dictionary (sorted keys) from resolved params only
7. Output: **Manifest** (resolved params) → hash becomes **Digest** (cache key)

**Key Design:** Dependencies are NOT injected into the manifest. They are only used to resolve param markers. The manifest is built entirely from resolved params.

### **Phase 2: Action Execution (Manifest → Artifact)**
1. **Cache Lookup:** Check `ArtifactStore.exists(op_name, Digest)`
   - If True: Return stored Artifact, **skip Op execution**
2. **Execution:** If False:
   - Inspect op function signature using `inspect.signature()`
   - Map manifest keys to function parameters by name (`**kwargs` dispatch)
   - Invoke `OpRegistry.get(op_name)(**kwargs)`
   - Validate return value is cacheable using `is_cacheable()`
   - Store value as-is (native types or ICacheable domain types)
3. **Persistence:** Serialize and save Artifact to `ArtifactStore` under (op_name, Digest) using the store codec

## **System Components**

- **OpRegistry:** Singleton mapping string identifiers → Python callables
- **GraphResolver:** Parses DAG definition, validates, detects cycles, topologically sorts
- **Executor:** Runtime engine managing Phase 1 → Phase 2 loop, failures, progress
- **ArtifactStore:** Storage abstraction (MemoryStore, DiskStore, CloudStore)

## **Parameter Markers**

Node params support three explicit mechanisms. For the complete normative reference, see [docs/expressions.md](./docs/expressions.md).

| Marker | Purpose | Example |
|:--|:--|:--|
| `ref("dep")` | Pass artifact directly to op | `params={"a": ref("p"), "b": ref("q")}` |
| `cel("expr")` | Evaluate CEL expression | `params={"width": cel("decimal(bg.width) * decimal('0.75')")}` |
| `"${expr}"` | String interpolation | `params={"message": "Width is ${bg.width}px"}` |
| literal | Static value | `params={"x": 5, "color": "#000"}` |

**Validation:** `ref()` markers are validated at Node creation time — every `ref("dep")` must reference a declared dependency in `deps`.

## **For More Information**

| Document | Description |
|:--|:--|
| [docs/expressions.md](./docs/expressions.md) | **Normative reference** for parameter markers (`ref`, `cel`, `${...}`) and the CEL expression language |
| [docs/executor.md](./docs/executor.md) | **Normative reference** for the two-phase execution model, caching, type unwrapping, and artifact storage |
| [docs/subgraphs.md](./docs/subgraphs.md) | SubGraphNode model, execution semantics, and reusable DAG fragments |
| [architecture.md](./architecture.md) | Design philosophy, protocol specifications, and reference test pipeline |
| [examples/README.md](./examples/README.md) | Runnable examples with walkthroughs, DAG diagrams, and run instructions |

