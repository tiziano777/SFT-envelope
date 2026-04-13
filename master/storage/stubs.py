"""Stub implementations for S3 and NFS storage writers."""

from __future__ import annotations

from master.storage.base import BaseStorageWriter


# --- S3StorageWriter Stub ---


class S3StorageWriter(BaseStorageWriter):
    """Stub implementation for S3 storage (not yet implemented)."""

    def __init__(self) -> None:
        """Initialize S3StorageWriter stub."""
        pass

    async def read_file(self, uri: str) -> bytes:
        """S3 storage not yet implemented."""
        raise NotImplementedError("S3 storage not yet implemented")

    async def write_file(self, uri: str, data: bytes) -> None:
        """S3 storage not yet implemented."""
        raise NotImplementedError("S3 storage not yet implemented")

    async def file_exists(self, uri: str) -> bool:
        """S3 storage not yet implemented."""
        raise NotImplementedError("S3 storage not yet implemented")

    async def delete_file(self, uri: str) -> None:
        """S3 storage not yet implemented."""
        raise NotImplementedError("S3 storage not yet implemented")


# --- NFSStorageWriter Stub ---


class NFSStorageWriter(BaseStorageWriter):
    """Stub implementation for NFS storage (not yet implemented)."""

    def __init__(self) -> None:
        """Initialize NFSStorageWriter stub."""
        pass

    async def read_file(self, uri: str) -> bytes:
        """NFS storage not yet implemented."""
        raise NotImplementedError("NFS storage not yet implemented")

    async def write_file(self, uri: str, data: bytes) -> None:
        """NFS storage not yet implemented."""
        raise NotImplementedError("NFS storage not yet implemented")

    async def file_exists(self, uri: str) -> bool:
        """NFS storage not yet implemented."""
        raise NotImplementedError("NFS storage not yet implemented")

    async def delete_file(self, uri: str) -> None:
        """NFS storage not yet implemented."""
        raise NotImplementedError("NFS storage not yet implemented")
