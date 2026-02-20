"""DiskStore: Filesystem-based artifact storage."""

from pathlib import Path
from typing import Any

from invariant.cacheable import is_cacheable
from invariant.store.base import ArtifactStore
from invariant.store.codec import deserialize, serialize


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

    def _get_path(self, op_name: str, digest: str) -> Path:
        """Get filesystem path for an operation and digest.

        Args:
            op_name: The name of the operation.
            digest: The SHA-256 hash (64 character hex string).

        Returns:
            Path to the artifact file.
        """
        if len(digest) != 64:
            raise ValueError(f"Invalid digest length: {len(digest)}, expected 64")

        # Sanitize op_name for filesystem (replace : with _)
        safe_op_name = op_name.replace(":", "_").replace("/", "_")

        # Three-level directory structure: op_name / first 2 chars / remaining 62 chars
        dir_path = self.cache_dir / safe_op_name / digest[:2]
        file_path = dir_path / digest[2:]
        return file_path

    def exists(self, op_name: str, digest: str) -> bool:
        """Check if an artifact exists."""
        path = self._get_path(op_name, digest)
        return path.exists()

    def get(self, op_name: str, digest: str) -> Any:
        """Retrieve an artifact by operation name and digest.

        Raises:
            KeyError: If artifact does not exist.
        """
        path = self._get_path(op_name, digest)

        if not path.exists():
            raise KeyError(
                f"Artifact with op_name '{op_name}' and digest '{digest}' not found"
            )

        # Read file
        with open(path, "rb") as f:
            data = f.read()

        # Deserialize using codec
        return deserialize(data)

    def put(self, op_name: str, digest: str, artifact: Any) -> None:
        """Store an artifact with the given operation name and digest."""
        # Validate artifact is cacheable
        if not is_cacheable(artifact):
            raise TypeError(
                f"Artifact is not cacheable: {type(artifact)}. "
                f"Use is_cacheable() to check values before storing."
            )

        path = self._get_path(op_name, digest)

        # Create parent directory if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize using codec
        serialized_data = serialize(artifact)

        # Write atomically (write to temp file, then rename)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        with open(temp_path, "wb") as f:
            f.write(serialized_data)
        temp_path.replace(path)
