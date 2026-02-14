# **Architecture: Invariant (DWE)**

## **1\. Overview**

**Invariant** is a Python-based deterministic execution engine for directed acyclic graphs (DAGs). It is designed to orchestrate complex computational workflows—such as media transcoding, rendering, or scientific data processing—where the cost of re-computation is high.

### **1.1 Core Value Proposition**

Unlike task schedulers (e.g., Apache Airflow, Luigi) which focus on *when* to run tasks, Invariant focuses on *what* is being produced. It treats every operation as a pure function: Op(Input) \= Output.

By enforcing **hermeticity** (no hidden inputs) and **immutability** (read-only outputs), Invariant provides:

1. **Aggressive Caching:** Artifacts are reused across runs and even across different pipelines if their inputs match.  
2. **Deduplication:** Identical operations requested by different parts of the graph are executed only once.  
3. **Reproducibility:** A workflow run today produces bit-for-bit the same output as one run next year (assuming the underlying Op implementation is deterministic).

### **1.2 Influences & Similar Systems**

* **Google Bazel (Blaze):** Invariant adopts Bazel's concept of the "Action Graph" and "Artifact Cache." Just as Bazel caches build artifacts (.o files) based on the hash of source files and compiler flags, Invariant caches data artifacts based on the hash of input data and operation parameters.  
* **TensorFlow:** Invariant mirrors the "Computation Graph" model where nodes represent operations and edges represent the flow of immutable data tensors, separating the graph definition phase from the execution phase.  
* **Functional Programming:** The engine enforces a side-effect-free model where "mutation" is modeled as creating a new version of data.

## **2\. Core Philosophy & Constraints**

### **2.1 The "Immutability Contract"**

* **Principle:** Once an **Artifact** is generated, it is frozen.  
* **Constraint:** Downstream nodes cannot modify an upstream artifact in place. They must consume it and produce a *new* artifact.

### **2.2 The "Determinism Contract"**

* **Principle:** An **Op** must rely *only* on the data provided in its **Input Manifest**.  
* **Constraint:** Access to global state, system clocks (time.now()), or random number generators (random.random()) inside an Op is forbidden unless those values are passed in as explicit inputs from the graph's root.

### **2.3 The "Strict Numeric" Policy**

* **Problem:** IEEE 754 floating-point numbers are non-deterministic across architectures and serialization formats.  
* **Constraint:** Native float types are **forbidden** in the cacheable data protocol.  
* **Solution:** Use decimal.Decimal (canonicalized to string) or integer ratios for fractional data.

## **3\. Data Protocol & Component Naming**

We strictly normalize naming to ensure clarity across the system.

| Term | Definition | Analogous Concept |
| :---- | :---- | :---- |
| **Node** | A vertex in the DAG defining *what* to do. Contains op name, params, and references to upstream deps. | Build Target |
| **Op** | The underlying Python function implementing the logic. | Kernel / Function |
| **Manifest** | The fully resolved, static dictionary of inputs for a specific Node execution. | Call Frame / Props |
| **Artifact** | The immutable output produced by an Op. | Build Artifact / Tensor |
| **Digest** | The SHA-256 hash of a Manifest. Serves as the **Identity** of a potential Artifact. | Cache Key |

### **3.1 The ICacheable Protocol**

All data passed between Nodes must adhere to this protocol to ensure valid Manifest construction.

from typing import Protocol, BinaryIO

class ICacheable(Protocol):  
    def get\_stable\_hash(self) \-\> str:  
        """  
        Returns a deterministic SHA-256 hash of the object's structural state.  
        This represents the 'Identity' of the data.  
        """  
        ...

    def to\_stream(self, stream: BinaryIO) \-\> None:  
        """  
        Serializes the object to a binary stream for persistent storage.  
        """  
        ...

    @classmethod  
    def from\_stream(cls, stream: BinaryIO) \-\> 'ICacheable':  
        """  
        Hydrates the object from a binary stream.  
        """  
        ...

## **4\. Execution Architecture**

The execution flow is split into two distinct phases to maximize cache hits.

### **Phase 1: Context Resolution (Graph \-\> Manifest)**

The engine traverses the user-defined DAG. For each Node, it resolves inputs to create an **Input Manifest**.

* **Inputs:**  
  1. Static Parameters (from Node definition).  
  2. Upstream Artifacts (results from deps).  
* **Process:**  
  * The engine recursively calculates the get\_stable\_hash() for every item.  
  * It assembles a canonical dictionary (sorted keys) of these inputs.  
* **Output:** The **Manifest**. The hash of this Manifest becomes the **Digest** (Cache Key).

### **Phase 2: Action Execution (Manifest \-\> Artifact)**

* **Step 1: Cache Lookup**  
  * Engine checks ArtifactStore.exists(Digest).  
  * *If True:* Returns the stored Artifact. **Op is strictly skipped.**  
* **Step 2: Execution**  
  * *If False:* Engine invokes OpRegistry.get(op\_name)(manifest).  
* **Step 3: Persistence**  
  * The resulting Artifact is serialized and saved to ArtifactStore under Digest.

## **5\. System Components**

### **5.1 OpRegistry**

A singleton registry mapping string identifiers to executable Python callables.

* *Role:* Decouples the "string" name in the YAML/JSON definition from the actual Python code.

### **5.2 Graph Resolver**

Responsible for parsing the definition and ensuring a valid DAG.

* *Role:* Cycle detection, validation, and Topological Sorting.

### **5.3 Executor**

The runtime engine.

* *Role:* Iterates the sorted nodes, manages the "Phase 1 \-\> Phase 2" loop, handles failures, and reports progress.

### **5.4 Artifact Store**

The storage abstraction.

* *Implementations:*  
  * MemoryStore: fast, ephemeral (testing).  
  * DiskStore: local filesystem (.invariant/cache/).  
  * CloudStore: S3/GCS buckets for shared team caches.

## **6\. Development Stages**

1. **Core Protocols:** Implement ICacheable, stable recursive hashing, and Decimal support.  
2. **Engine Logic:** Build GraphResolver and Executor.  
3. **Storage:** Implement DiskStore.  
4. **Ops Standard Library:** Implement foundational Ops (dict manipulation, basic math) to prove the DAG.