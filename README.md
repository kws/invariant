# Invariant

A Python-based deterministic execution engine for directed acyclic graphs (DAGs). Invariant treats every operation as a pure function, providing aggressive caching, deduplication, and bit-for-bit reproducibility.

## Features

- **Aggressive Caching**: Artifacts are reused across runs if inputs match
- **Deduplication**: Identical operations execute only once
- **Reproducibility**: Bit-for-bit identical outputs across runs
- **Immutability**: Artifacts are frozen once created
- **Determinism**: Operations rely only on explicit inputs

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd invariant

# Install dependencies
poetry install
```

## Quick Start

```python
from invariant import Executor, Node, OpRegistry
from invariant.ops import stdlib
from invariant.store.memory import MemoryStore
from invariant.types import Integer, String

# Create registry and register operations
registry = OpRegistry()
registry.register_package("stdlib", stdlib)

# Create a simple graph: a -> b
graph = {
    "a": Node(
        op_name="stdlib:identity",
        params={"value": String("hello")},
        deps=[]
    ),
    "b": Node(
        op_name="stdlib:add",
        params={"a": Integer(1), "b": Integer(2)},
        deps=["a"]
    ),
}

# Execute the graph
store = MemoryStore()
executor = Executor(registry=registry, store=store)
results = executor.execute(graph)

print(results["a"].value)  # "hello"
print(results["b"].value)  # 3
```

## Architecture

Invariant separates graph definition from execution in two phases:

1. **Phase 1: Context Resolution** - Builds input manifests for each node
2. **Phase 2: Action Execution** - Executes operations or retrieves from cache

For detailed architecture documentation, see [docs/architecture.md](docs/architecture.md).

For AI agents working with this codebase, see [AGENTS.md](AGENTS.md).

## Development

```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=src --cov-report=html

# Run linting
poetry run ruff check src/ tests/

# Format code
poetry run ruff format src/ tests/
```

## License

MIT License - see [LICENSE](LICENSE) for details.

