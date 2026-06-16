import io
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO
from app.core.config import get_settings

class StorageBackend(ABC):
    @abstractmethod
    async def save(self, path: str, data: bytes | BinaryIO, content_type: str | None = None) -> str:
        """Save file and return stored path/URL."""
        ...

    @abstractmethod
    async def read(self, path: str) -> bytes:
        ...

    @abstractmethod
    async def delete(self, path: str) -> None:
        ...

    @abstractmethod
    async def exists(self, path: str) -> bool:
        ...

    @abstractmethod
    def get_url(self, path: str) -> str:
        ...

class LocalStorage(StorageBackend):
    def __init__(self, base_path: str | None = None) -> None:
        settings = get_settings()
        self.base_path = Path(base_path or settings.STORAGE_LOCAL_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.url_prefix = settings.STORAGE_URL_PREFIX

    async def save(self, path: str, data: bytes | BinaryIO, content_type: str | None = None) -> str:
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            full_path.write_bytes(data)
        else:
            with open(full_path, "wb") as f:
                shutil.copyfileobj(data, f)
        return path

    async def read(self, path: str) -> bytes:
        full_path = self.base_path / path
        return full_path.read_bytes()

    async def delete(self, path: str) -> None:
        full_path = self.base_path / path
        if full_path.exists():
            if full_path.is_dir():
                shutil.rmtree(full_path)
            else:
                full_path.unlink()

    async def exists(self, path: str) -> bool:
        return (self.base_path / path).exists()

    def get_url(self, path: str) -> str:
        return f"{self.url_prefix}/{path}"

    def get_local_path(self, path: str) -> Path:
        return self.base_path / path

_storage_instance: StorageBackend | None = None

def get_storage() -> StorageBackend:
    global _storage_instance
    if _storage_instance is None:
        settings = get_settings()
        if settings.STORAGE_BACKEND == "local":
            _storage_instance = LocalStorage()
        else:
            raise ValueError(f"Unsupported storage backend: {settings.STORAGE_BACKEND}")
    return _storage_instance
