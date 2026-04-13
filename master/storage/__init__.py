"""Master storage layer: URI-driven artifact persistence with pluggable backends.

Exports:
- BaseStorageWriter: ABC for all storage writer implementations
- LocalStorageWriter: Implementation for file:// URIs
- S3StorageWriter, NFSStorageWriter: Stub implementations
- URIResolver: Dispatcher to appropriate backend based on URI prefix
- Error types: StorageError, FileNotFound, URINotSupported
"""

from __future__ import annotations

from master.storage.base import (
    BaseStorageWriter,
    StorageError,
    FileNotFound,
    URINotSupported,
)
from master.storage.local import LocalStorageWriter
from master.storage.stubs import S3StorageWriter, NFSStorageWriter
from master.storage.resolver import URIResolver

__all__ = [
    "BaseStorageWriter",
    "LocalStorageWriter",
    "S3StorageWriter",
    "NFSStorageWriter",
    "URIResolver",
    "StorageError",
    "FileNotFound",
    "URINotSupported",
]
