"""
Storage abstraction. Business logic (services) only ever talks to
`StorageBackend`, never to the filesystem or an S3 SDK directly, so the
backing store can be swapped (local disk -> S3/MinIO) without touching
service code. See `app.storage.factory.get_storage_backend`.
"""
from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, *, relative_path: str, content: bytes) -> str:
        """Persist `content` and return the storage path actually used."""

    @abstractmethod
    async def read(self, *, storage_path: str) -> bytes:
        """Raises FileNotFoundError if the object does not exist."""

    @abstractmethod
    async def delete(self, *, storage_path: str) -> None:
        ...

    @abstractmethod
    async def exists(self, *, storage_path: str) -> bool:
        ...
