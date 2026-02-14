"""DiskStore: Filesystem-based artifact storage."""

import importlib
from io import BytesIO
from pathlib import Path

from invariant.protocol import ICacheable
from invariant.store.base import ArtifactStore


class DiskStore(ArtifactStore):
    """Filesystem-based artifact store.

    Stores artifacts in the local filesystem under `.invariant/cache/`
    using a two-level directory structure: `{digest[:2]}/{digest[2:]}`
    for efficient filesystem performance.
    """

    def __init__(self, cache_dir: Path | str | None = None) -> None:
        """Initialize DiskStore.

        Args:
            cache_dir: Directory to store cache. Defaults to `.invariant/cache/`
                      in the current working directory.
        """
        if cache_dir is None:
            cache_dir = Path.cwd() / ".invariant" / "cache"
        elif isinstance(cache_dir, str):
            cache_dir = Path(cache_dir)

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, digest: str) -> Path:
        """Get filesystem path for a digest.

        Args:
            digest: The SHA-256 hash (64 character hex string).

        Returns:
            Path to the artifact file.
        """
        if len(digest) != 64:
            raise ValueError(f"Invalid digest length: {len(digest)}, expected 64")

        # Two-level directory structure: first 2 chars, then remaining 62 chars
        dir_path = self.cache_dir / digest[:2]
        file_path = dir_path / digest[2:]
        return file_path

    def exists(self, digest: str) -> bool:
        """Check if an artifact exists."""
        path = self._get_path(digest)
        return path.exists()

    def get(self, digest: str) -> ICacheable:
        """Retrieve an artifact by digest.

        Raises:
            KeyError: If artifact does not exist.
        """
        path = self._get_path(digest)

        if not path.exists():
            raise KeyError(f"Artifact with digest '{digest}' not found")

        # Read file
        with open(path, "rb") as f:
            data = f.read()

        # Parse: [4 bytes: type_name_len][type_name][serialized_data]
        type_name_len = int.from_bytes(data[:4], byteorder="big")
        type_name_bytes = data[4 : 4 + type_name_len]
        type_name = type_name_bytes.decode("utf-8")
        serialized_data = data[4 + type_name_len :]

        # Import the class
        module_path, class_name = type_name.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)

        # Deserialize
        stream = BytesIO(serialized_data)
        return cls.from_stream(stream)

    def put(self, digest: str, artifact: ICacheable) -> None:
        """Store an artifact with the given digest."""
        path = self._get_path(digest)

        # Create parent directory if needed
        path.parent.mkdir(parents=True, exist_ok=True)

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
            type_name_len.to_bytes(4, byteorder="big")
            + type_name_bytes
            + serialized_data
        )

        # Write atomically (write to temp file, then rename)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        with open(temp_path, "wb") as f:
            f.write(combined)
        temp_path.replace(path)
