"""URIResolver for dispatch to pluggable storage backends."""

from __future__ import annotations

import json
import os

from master.storage.base import BaseStorageWriter, URINotSupported
from master.storage.local import LocalStorageWriter
from master.storage.stubs import S3StorageWriter, NFSStorageWriter


class URIResolver:
    """Routes URIs to appropriate storage writer backends.

    Supports dynamic backend configuration via STORAGE_BACKENDS env var
    (JSON dict mapping prefix to class name). Defaults to file:// (LocalStorageWriter),
    s3://, and nfs:// (stubs).
    """

    def __init__(self) -> None:
        """Initialize URIResolver with backends from env or defaults."""
        self.backends: dict[str, BaseStorageWriter] = {}
        self._load_backends()

    def _load_backends(self) -> None:
        """Load storage backends from env var or use defaults."""
        # Default backends
        default_backends = {
            "file": LocalStorageWriter(),
            "s3": S3StorageWriter(),
            "nfs": NFSStorageWriter(),
        }

        # Try to load custom backends from env
        env_backends_json = os.getenv("STORAGE_BACKENDS")
        if env_backends_json:
            try:
                backends_config = json.loads(env_backends_json)
                # Load configured backends
                for prefix, config in backends_config.items():
                    class_name = config.get("class", "")
                    backend_config = config.get("config", {})
                    writer_class = self._get_class(class_name)
                    if writer_class:
                        self.backends[prefix] = writer_class(**backend_config)
                return
            except (json.JSONDecodeError, ValueError):
                # Fall through to defaults
                pass

        # Use defaults
        self.backends = default_backends

    def _get_class(self, class_name: str) -> type[BaseStorageWriter] | None:
        """Get storage writer class by name.

        Args:
            class_name: Class name (e.g., 'LocalStorageWriter', 'S3StorageWriter')

        Returns:
            Class object or None if not found
        """
        classes = {
            "LocalStorageWriter": LocalStorageWriter,
            "S3StorageWriter": S3StorageWriter,
            "NFSStorageWriter": NFSStorageWriter,
        }
        return classes.get(class_name)

    def _get_writer_for_uri(self, uri: str) -> BaseStorageWriter:
        """Get appropriate writer for a URI.

        Args:
            uri: Full URI (e.g., 'file:///tmp/x', 's3://bucket/key')

        Returns:
            Storage writer instance

        Raises:
            URINotSupported: If URI prefix not recognized
        """
        # Extract prefix (e.g., 'file' from 'file://...')
        if "://" not in uri:
            raise URINotSupported(f"Invalid URI format: {uri}")

        prefix = uri.split("://")[0]

        if prefix not in self.backends:
            raise URINotSupported(f"Unsupported URI prefix: {prefix}")

        return self.backends[prefix]

    async def read_file(self, uri: str) -> bytes:
        """Read file from appropriate backend.

        Args:
            uri: Full URI

        Returns:
            File contents as bytes

        Raises:
            URINotSupported: If URI prefix not recognized
        """
        writer = self._get_writer_for_uri(uri)
        return await writer.read_file(uri)

    async def write_file(self, uri: str, data: bytes) -> None:
        """Write file to appropriate backend.

        Args:
            uri: Full URI
            data: Bytes to write

        Raises:
            URINotSupported: If URI prefix not recognized
        """
        writer = self._get_writer_for_uri(uri)
        await writer.write_file(uri, data)

    async def file_exists(self, uri: str) -> bool:
        """Check if file exists in appropriate backend.

        Args:
            uri: Full URI

        Returns:
            True if file exists, False otherwise

        Raises:
            URINotSupported: If URI prefix not recognized
        """
        writer = self._get_writer_for_uri(uri)
        return await writer.file_exists(uri)

    async def delete_file(self, uri: str) -> None:
        """Delete file from appropriate backend.

        Args:
            uri: Full URI

        Raises:
            URINotSupported: If URI prefix not recognized
        """
        writer = self._get_writer_for_uri(uri)
        await writer.delete_file(uri)
