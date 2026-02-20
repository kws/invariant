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
from invariant import Executor, Node, OpRegistry, cel, ref
from invariant.ops import stdlib
from invariant.store.memory import MemoryStore

# Create registry and register operations
registry = OpRegistry()
registry.register_package("stdlib", stdlib)

# Create a simple graph: x -> y -> sum
graph = {
    "x": Node(
        op_name="stdlib:from_integer",
        params={"value": 5},
        deps=[]
    ),
    "y": Node(
        op_name="stdlib:from_integer",
        params={"value": 3},
        deps=[]
    ),
    "sum": Node(
        op_name="stdlib:add",
        params={"a": ref("x"), "b": ref("y")},  # ref() passes artifacts directly
        deps=["x", "y"]
    ),
    "doubled": Node(
        op_name="stdlib:multiply",
        params={"a": cel("sum.value"), "b": 2},  # cel() evaluates expression
        deps=["sum"]
    ),
}

# Execute the graph
store = MemoryStore()
executor = Executor(registry=registry, store=store)
results = executor.execute(graph)

print(results["sum"].value)    # 8
print(results["doubled"].value)  # 16
```

## Architecture

Invariant separates graph definition from execution in two phases:

1. **Phase 1: Context Resolution** - Builds input manifests for each node
2. **Phase 2: Action Execution** - Executes operations or retrieves from cache

### Documentation

| Document | Description |
|:--|:--|
| [docs/architecture.md](docs/architecture.md) | System overview, design philosophy, and reference test pipeline |
| [docs/expressions.md](docs/expressions.md) | **Normative reference** for `ref()`, `cel()`, `${...}` parameter markers and the CEL expression language |
| [docs/executor.md](docs/executor.md) | **Normative reference** for the two-phase execution model, caching, and artifact storage |
| [examples/README.md](examples/README.md) | Runnable examples with walkthroughs, DAG diagrams, and run instructions |
| [AGENTS.md](AGENTS.md) | Quick-start guide for AI agents working with this codebase |

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

