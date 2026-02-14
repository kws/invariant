# **AGENTS.md: Essential Information for AI Agents**

This document provides must-know information about the Invariant system. For comprehensive details, see [architecture.md](./architecture.md).

## **What is Invariant?**

Invariant is a Python-based deterministic execution engine for DAGs (directed acyclic graphs). It treats every operation as a pure function: `Op(Input) = Output`.

**Core Value:**
- **Aggressive Caching:** Artifacts are reused across runs if inputs match
- **Deduplication:** Identical operations execute only once
- **Reproducibility:** Bit-for-bit identical outputs across runs

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
| **Node** | Vertex in DAG defining *what* to do | Contains op name, params, upstream deps |
| **Op** | Python function implementing the logic | Pure function: Op(Input) = Output |
| **Manifest** | Fully resolved dictionary of inputs for a Node | Static, canonicalized |
| **Artifact** | Immutable output produced by an Op | Frozen once created |
| **Digest** | SHA-256 hash of a Manifest | Serves as cache key/identity |

## **ICacheable Protocol**

All data passed between Nodes **must** implement this protocol:

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

## **Execution Model: Two Phases**

### **Phase 1: Context Resolution (Graph → Manifest)**
1. Traverse DAG, resolve inputs for each Node
2. Recursively calculate `get_stable_hash()` for all inputs
3. Assemble canonical dictionary (sorted keys)
4. Output: **Manifest** → hash becomes **Digest** (cache key)

### **Phase 2: Action Execution (Manifest → Artifact)**
1. **Cache Lookup:** Check `ArtifactStore.exists(Digest)`
   - If True: Return stored Artifact, **skip Op execution**
2. **Execution:** If False, invoke `OpRegistry.get(op_name)(manifest)`
3. **Persistence:** Serialize and save Artifact to `ArtifactStore` under Digest

## **System Components**

- **OpRegistry:** Singleton mapping string identifiers → Python callables
- **GraphResolver:** Parses DAG definition, validates, detects cycles, topologically sorts
- **Executor:** Runtime engine managing Phase 1 → Phase 2 loop, failures, progress
- **ArtifactStore:** Storage abstraction (MemoryStore, DiskStore, CloudStore)

## **For More Information**

See [architecture.md](./architecture.md) for:
- Detailed design philosophy and influences
- Complete protocol specifications
- Development roadmap
- Extended examples and use cases

