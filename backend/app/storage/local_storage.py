"""
Local-disk storage backend. Default for development and the student-project
deployment target; production can swap in an S3-backed implementation
behind the same `StorageBackend` interface without any service-layer
changes.

Security notes:
 - `relative_path` is expected to already be a server-generated, sanitized
   name (see app.utils.files.sanitize_filename) — never a raw user-supplied
   filename — but we still normalise and reject path traversal here as a
   defence-in-depth measure.
"""
import os
from pathlib import Path

from app.core.config import settings
from app.storage.interface import StorageBackend


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_path: str | None = None) -> None:
        self.base_path = Path(base_path or settings.storage_local_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self.base_path / relative_path).resolve()
        if self.base_path not in candidate.parents and candidate != self.base_path:
            raise ValueError("Invalid storage path (path traversal attempt).")
        return candidate

    async def save(self, *, relative_path: str, content: bytes) -> str:
        target = self._resolve(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as f:
            f.write(content)
        return str(target.relative_to(self.base_path))

    async def read(self, *, storage_path: str) -> bytes:
        target = self._resolve(storage_path)
        if not target.exists():
            raise FileNotFoundError(storage_path)
        with open(target, "rb") as f:
            return f.read()

    async def delete(self, *, storage_path: str) -> None:
        target = self._resolve(storage_path)
        if target.exists():
            os.remove(target)

    async def exists(self, *, storage_path: str) -> bool:
        return self._resolve(storage_path).exists()
