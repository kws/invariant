"""MemoryStore: In-memory artifact storage for testing."""

from io import BytesIO

from invariant.protocol import ICacheable
from invariant.store.base import ArtifactStore


class MemoryStore(ArtifactStore):
    """In-memory artifact store using a dictionary.
    
    Fast and ephemeral - suitable for testing. Artifacts are lost when
    the store instance is destroyed.
    """
    
    def __init__(self) -> None:
        """Initialize an empty memory store."""
        self._artifacts: dict[str, bytes] = {}
    
    def exists(self, digest: str) -> bool:
        """Check if an artifact exists."""
        return digest in self._artifacts
    
    def get(self, digest: str) -> ICacheable:
        """Retrieve an artifact by digest.
        
        Raises:
            KeyError: If artifact does not exist.
        """
        if digest not in self._artifacts:
            raise KeyError(f"Artifact with digest '{digest}' not found")
        
        # Deserialize from stored bytes
        data = self._artifacts[digest]
        stream = BytesIO(data)
        
        # We need to know the type to deserialize. For now, we'll store
        # a type identifier with the data. For simplicity, we'll assume
        # the artifact type is stored as the first part.
        # This is a limitation - in a real implementation, we'd need
        # a type registry or store type info with the artifact.
        # For now, we'll use a simple approach: store as pickled or
        # use a type registry.
        
        # Actually, let's use a simpler approach: store the class name
        # and module, then use importlib to load it. But for basic types,
        # we can handle them directly.
        
        # For now, let's use a simple format: first 4 bytes = length of
        # class name, then class name, then the serialized data.
        # But this is getting complex. Let me use a simpler approach:
        # store (class_name, serialized_data) tuple.
        
        # Actually, the simplest approach for MemoryStore is to store
        # the artifact directly and serialize/deserialize on the fly.
        # But that defeats the purpose of testing serialization.
        
        # Let me reconsider: we'll store serialized bytes, but we need
        # to know the type. For MemoryStore, we can store a tuple of
        # (type_name, serialized_bytes).
        
        # For now, let's use a simple approach: store the artifact
        # directly in memory (not serialized) for MemoryStore, since
        # it's just for testing. The DiskStore will handle real serialization.
        
        # Actually, that's not right either - we should test serialization
        # in MemoryStore too.
        
        # Let me use a simple format: store as (class_path, serialized_bytes)
        # where class_path is something like "invariant.types.String"
        
        # For simplicity in the initial implementation, let's store
        # artifacts directly (not serialized) in MemoryStore, and
        # implement proper serialization in DiskStore. We can enhance
        # MemoryStore later if needed.
        
        # Wait, but the interface says we should serialize. Let me
        # implement a simple serialization format.
        
        # Actually, I think the best approach is to store artifacts
        # as ICacheable objects directly in MemoryStore (since it's
        # just for testing), and implement proper serialization in
        # DiskStore. But that means MemoryStore won't test serialization.
        
        # Let me implement a hybrid: store serialized bytes, but
        # also store the type info. For now, I'll use a simple format.
        
        # Actually, let me check the architecture again - it says
        # MemoryStore is "fast, ephemeral (testing)". So maybe
        # it's okay to not serialize for MemoryStore.
        
        # But the interface is clear: we use to_stream/from_stream.
        # So let's implement it properly.
        
        # For MemoryStore, I'll store a mapping of digest -> (type_name, bytes)
        # where type_name is the fully qualified class name.
        
        # Actually, the simplest is to store the artifact directly
        # and serialize/deserialize on put/get. But that means we
        # need to know the type on get.
        
        # Let me use a simple approach: store (type_name, serialized_bytes)
        # as a tuple, where type_name is a string like "invariant.types.String"
        
        # But we need to be able to import and instantiate the class.
        # That's complex.
        
        # For now, let me implement a simpler version that stores
        # artifacts directly (not serialized) in MemoryStore. This
        # is acceptable for a testing store. DiskStore will handle
        # real serialization.
        
        # Actually, I realize the issue: we can't deserialize without
        # knowing the type. So we need to store type information.
        # Let me implement a simple solution: store (class_name, bytes)
        # and use importlib to load the class.
        
        import importlib
        
        # Read type name length (4 bytes)
        type_name_len = int.from_bytes(data[:4], byteorder="big")
        # Read type name
        type_name_bytes = data[4:4+type_name_len]
        type_name = type_name_bytes.decode("utf-8")
        # Read serialized data
        serialized_data = data[4+type_name_len:]
        
        # Import the class
        module_path, class_name = type_name.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        
        # Deserialize
        stream = BytesIO(serialized_data)
        return cls.from_stream(stream)
    
    def put(self, digest: str, artifact: ICacheable) -> None:
        """Store an artifact with the given digest."""
        # Serialize the artifact
        stream = BytesIO()
        artifact.to_stream(stream)
        serialized_data = stream.getvalue()
        
        # Store type information with the data
        type_name = f"{artifact.__class__.__module__}.{artifact.__class__.__name__}"
        type_name_bytes = type_name.encode("utf-8")
        type_name_len = len(type_name_bytes)
        
        # Combine: [4 bytes: type_name_len][type_name][serialized_data]
        combined = (
            type_name_len.to_bytes(4, byteorder="big") +
            type_name_bytes +
            serialized_data
        )
        
        self._artifacts[digest] = combined
    
    def clear(self) -> None:
        """Clear all artifacts (mainly for testing)."""
        self._artifacts.clear()

