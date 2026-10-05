from functools import lru_cache

from app.core.config import settings
from app.storage.interface import StorageBackend
from app.storage.local_storage import LocalStorageBackend


@lru_cache
def get_storage_backend() -> StorageBackend:
    if settings.storage_backend == "s3":
        # Placeholder for a future S3/MinIO implementation. Raising here
        # (rather than silently falling back to local disk) makes a
        # misconfiguration obvious instead of quietly storing patient
        # documents in the wrong place.
        raise NotImplementedError(
            "S3 storage backend is not implemented yet. Set STORAGE_BACKEND=local."
        )
    return LocalStorageBackend()
