"""Graph serialization: JSON wire format for Invariant graphs.

Encodes graphs (Node, SubGraphNode) and params (ref, cel, Decimal, tuple,
ICacheable) for storage and transmission. Distinct from artifact serialization
in store/codec.py.
"""

import base64
import importlib
import json
from decimal import Decimal
from io import BytesIO
from typing import Any

from invariant.graph import Graph
from invariant.node import Node, SubGraphNode
from invariant.params import cel, ref
from invariant.protocol import ICacheable

SUPPORTED_VERSIONS = {1}
FORMAT_ID = "invariant-graph"

RESERVED_KEYS = frozenset(
    {"$ref", "$cel", "$decimal", "$tuple", "$literal", "$icacheable"}
)


def _encode_param_value(value: Any) -> Any:
    """Recursively encode a parameter value to JSON-serializable form."""
    # ref marker
    if isinstance(value, ref):
        return {"$ref": value.dep}

    # cel marker
    if isinstance(value, cel):
        return {"$cel": value.expr}

    # Decimal
    if isinstance(value, Decimal):
        return {"$decimal": str(value)}

    # tuple
    if isinstance(value, tuple):
        return {"$tuple": [_encode_param_value(item) for item in value]}

    # ICacheable
    if isinstance(value, ICacheable):
        type_name = f"{value.__class__.__module__}.{value.__class__.__name__}"
        if hasattr(value, "to_json_value") and callable(
            getattr(value, "to_json_value")
        ):
            return {"$icacheable": {"type": type_name, "value": value.to_json_value()}}
        stream = BytesIO()
        value.to_stream(stream)
        payload_b64 = base64.b64encode(stream.getvalue()).decode("ascii")
        return {"$icacheable": {"type": type_name, "payload_b64": payload_b64}}

    # dict
    if isinstance(value, dict):
        encoded = {k: _encode_param_value(v) for k, v in value.items()}
        # Collision: plain dict that would decode as marker -> wrap in $literal
        if len(encoded) == 1:
            (single_key,) = encoded.keys()
            if single_key in RESERVED_KEYS:
                return {"$literal": encoded}
        return encoded

    # list
    if isinstance(value, list):
        return [_encode_param_value(item) for item in value]

    # Primitives: None, bool, int, str
    return value


def _decode_param_value(obj: Any, literal_mode: bool = False) -> Any:
    """Recursively decode a JSON value to Python parameter value."""
    # In literal mode, never treat dicts as markers
    if literal_mode:
        if isinstance(obj, dict):
            return {
                k: _decode_param_value(v, literal_mode=True) for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [_decode_param_value(item, literal_mode=True) for item in obj]
        return obj

    # Single-key dict with reserved key -> marker or escape
    if isinstance(obj, dict):
        if len(obj) == 1:
            (key, val) = next(iter(obj.items()))
            if key == "$ref":
                return ref(val)
            if key == "$cel":
                return cel(val)
            if key == "$decimal":
                return Decimal(val)
            if key == "$tuple":
                return tuple(_decode_param_value(item) for item in val)
            if key == "$literal":
                return _decode_param_value(val, literal_mode=True)
            if key == "$icacheable":
                return _decode_icacheable(val)
        # Multi-key or non-reserved: recursive decode
        return {k: _decode_param_value(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_decode_param_value(item) for item in obj]

    return obj


def _decode_icacheable(obj: dict) -> Any:
    """Decode $icacheable object to ICacheable instance."""
    if not isinstance(obj, dict):
        raise ValueError("$icacheable value must be an object")
    type_name = obj.get("type")
    if not type_name or not isinstance(type_name, str):
        raise ValueError("$icacheable must have non-empty string 'type'")
    if "payload_b64" in obj and "value" in obj:
        raise ValueError(
            "$icacheable must have exactly one of 'payload_b64' or 'value'"
        )
    if "payload_b64" not in obj and "value" not in obj:
        raise ValueError("$icacheable must have 'payload_b64' or 'value'")

    module_path, class_name = type_name.rsplit(".", 1)
    try:
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ValueError(
            f"$icacheable type '{type_name}' could not be imported: {e}"
        ) from e

    if "value" in obj:
        if not hasattr(cls, "from_json_value"):
            raise ValueError(
                f"$icacheable type '{type_name}' has 'value' but no from_json_value method"
            )
        return cls.from_json_value(obj["value"])

    # payload_b64
    try:
        payload = base64.b64decode(obj["payload_b64"])
    except Exception as e:
        raise ValueError(f"$icacheable payload_b64 is invalid base64: {e}") from e
    stream = BytesIO(payload)
    try:
        return cls.from_stream(stream)
    except Exception as e:
        raise ValueError(
            f"$icacheable from_stream failed for '{type_name}': {e}"
        ) from e


def _encode_params(params: dict[str, Any]) -> dict[str, Any]:
    """Encode params dict with sorted keys for determinism."""
    return dict(sorted((k, _encode_param_value(v)) for k, v in params.items()))


def _decode_params(obj: dict) -> dict[str, Any]:
    """Decode params dict."""
    return {k: _decode_param_value(v) for k, v in obj.items()}


def _encode_vertex(vertex: Node | SubGraphNode) -> dict:
    """Encode a single vertex (Node or SubGraphNode) to JSON object."""
    if isinstance(vertex, Node):
        return {
            "kind": "node",
            "op_name": vertex.op_name,
            "params": _encode_params(vertex.params),
            "deps": sorted(vertex.deps),
        }
    # SubGraphNode
    return {
        "kind": "subgraph",
        "params": _encode_params(vertex.params),
        "deps": sorted(vertex.deps),
        "graph": _encode_graph(vertex.graph),
        "output": vertex.output,
    }


def _decode_vertex(
    obj: dict, legacy_kind_inference: bool = False
) -> Node | SubGraphNode:
    """Decode a JSON object to Node or SubGraphNode. Validates before construction."""
    if not isinstance(obj, dict):
        raise ValueError("Vertex must be an object")

    kind = obj.get("kind")
    if kind is None and legacy_kind_inference:
        if "op_name" in obj and "graph" not in obj:
            kind = "node"
        elif "graph" in obj and "output" in obj:
            kind = "subgraph"
        else:
            raise ValueError(
                "Vertex has no 'kind' and cannot infer from op_name/graph/output"
            )
    if kind is None:
        raise ValueError("Vertex must have 'kind'")
    if kind not in ("node", "subgraph"):
        raise ValueError(f"Vertex has unsupported kind: {kind!r}")

    if kind == "node":
        _validate_node(obj, expected_kind=kind)
        return Node(
            op_name=obj["op_name"].strip(),
            params=_decode_params(obj["params"]),
            deps=list(obj["deps"]),
        )
    if kind == "subgraph":
        _validate_subgraph(obj, legacy_kind_inference)
        return SubGraphNode(
            params=_decode_params(obj["params"]),
            deps=list(obj["deps"]),
            graph=_decode_graph(obj["graph"], legacy_kind_inference),
            output=obj["output"],
        )
    raise ValueError(f"Vertex has unsupported kind: {kind!r}")


def _validate_node(obj: dict, expected_kind: str | None = None) -> None:
    """Validate node object before construction."""
    kind = expected_kind if expected_kind is not None else obj.get("kind")
    if kind != "node":
        raise ValueError("Node must have kind 'node'")
    op_name = obj.get("op_name")
    if not isinstance(op_name, str):
        raise ValueError("Node must have string 'op_name'")
    if not op_name.strip():
        raise ValueError("Node op_name cannot be empty")
    if "params" not in obj or not isinstance(obj["params"], dict):
        raise ValueError("Node must have 'params' object")
    if "deps" not in obj or not isinstance(obj["deps"], list):
        raise ValueError("Node must have 'deps' array")
    for i, dep in enumerate(obj["deps"]):
        if not isinstance(dep, str):
            raise ValueError(f"Node deps[{i}] must be string, got {type(dep).__name__}")


def _validate_subgraph(obj: dict, legacy_kind_inference: bool = False) -> None:
    """Validate subgraph object before construction."""
    kind = obj.get("kind")
    if not legacy_kind_inference and kind != "subgraph":
        raise ValueError("SubGraphNode must have kind 'subgraph'")
    if "params" not in obj or not isinstance(obj["params"], dict):
        raise ValueError("SubGraphNode must have 'params' object")
    if "deps" not in obj or not isinstance(obj["deps"], list):
        raise ValueError("SubGraphNode must have 'deps' array")
    for i, dep in enumerate(obj["deps"]):
        if not isinstance(dep, str):
            raise ValueError(
                f"SubGraphNode deps[{i}] must be string, got {type(dep).__name__}"
            )
    if "graph" not in obj or not isinstance(obj["graph"], dict):
        raise ValueError("SubGraphNode must have 'graph' object")
    output = obj.get("output")
    if not isinstance(output, str):
        raise ValueError("SubGraphNode must have string 'output'")
    if output not in obj["graph"]:
        raise ValueError(
            f"SubGraphNode output '{output}' must be key in graph. "
            f"Graph keys: {list(obj['graph'].keys())}"
        )
    for node_id, vertex_obj in obj["graph"].items():
        _validate_vertex_for_kind(vertex_obj, node_id, legacy_kind_inference)


def _validate_vertex_for_kind(
    vertex_obj: Any, node_id: str, legacy_kind_inference: bool = False
) -> None:
    """Validate a vertex object has valid kind and structure."""
    if not isinstance(vertex_obj, dict):
        raise ValueError(f"Vertex '{node_id}' must be an object")
    kind = vertex_obj.get("kind")
    if kind is None and legacy_kind_inference:
        if "op_name" in vertex_obj and "graph" not in vertex_obj:
            kind = "node"
        elif "graph" in vertex_obj and "output" in vertex_obj:
            kind = "subgraph"
        else:
            raise ValueError(
                f"Vertex '{node_id}' has no 'kind' and cannot infer from op_name/graph/output"
            )
    if kind == "node":
        _validate_node(vertex_obj, expected_kind="node")
    elif kind == "subgraph":
        _validate_subgraph(vertex_obj, legacy_kind_inference)
    else:
        raise ValueError(f"Vertex '{node_id}' has unsupported kind: {kind!r}")


def _encode_graph(graph: Graph) -> dict:
    """Encode graph to JSON object with sorted keys."""
    return dict(sorted((k, _encode_vertex(v)) for k, v in graph.items()))


def _decode_graph(obj: dict, legacy_kind_inference: bool = False) -> Graph:
    """Decode graph from JSON object."""
    if not isinstance(obj, dict):
        raise ValueError("Graph must be an object")
    result: Graph = {}
    for node_id, vertex_obj in obj.items():
        result[node_id] = _decode_vertex(vertex_obj, legacy_kind_inference)
    return result


def _validate_envelope(obj: dict) -> None:
    """Validate top-level envelope."""
    if not isinstance(obj, dict):
        raise ValueError("Document must be a JSON object")
    fmt = obj.get("format")
    if fmt != FORMAT_ID:
        raise ValueError(f"Document format must be '{FORMAT_ID}', got {fmt!r}")
    version = obj.get("version")
    if version not in SUPPORTED_VERSIONS:
        raise ValueError(
            f"Document version {version} is not supported. Supported: {sorted(SUPPORTED_VERSIONS)}"
        )
    if "graph" not in obj:
        raise ValueError("Document must have 'graph'")
    if not isinstance(obj["graph"], dict):
        raise ValueError("Document 'graph' must be an object")


def dump_graph_to_dict(graph: Graph) -> dict:
    """Serialize graph to envelope dict. Deterministic (sorted keys)."""
    return {
        "format": FORMAT_ID,
        "version": 1,
        "graph": _encode_graph(graph),
    }


def dump_graph(graph: Graph) -> str:
    """Serialize graph to JSON string. Deterministic output."""
    return json.dumps(dump_graph_to_dict(graph), sort_keys=True)


def load_graph_from_dict(obj: dict, legacy_kind_inference: bool = False) -> Graph:
    """Load graph from envelope dict."""
    _validate_envelope(obj)
    return _decode_graph(obj["graph"], legacy_kind_inference)


def load_graph(data: str | bytes, legacy_kind_inference: bool = False) -> Graph:
    """Deserialize JSON string or bytes to graph."""
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    obj = json.loads(data)
    return load_graph_from_dict(obj, legacy_kind_inference)
