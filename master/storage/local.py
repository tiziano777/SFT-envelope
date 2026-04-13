"""LocalStorageWriter implementation for file:// URIs."""

from __future__ import annotations

import asyncio
from pathlib import Path

from master.storage.base import BaseStorageWriter, FileNotFound, URINotSupported


class LocalStorageWriter(BaseStorageWriter):
    """Storage writer for local filesystem using file:// URIs."""

    def __init__(self, root_dir: str | None = None) -> None:
        """Initialize with optional root directory.

        Args:
            root_dir: Optional base directory (defaults to None — all paths absolute)
        """
        self.root_dir = Path(root_dir) if root_dir else None

    def _extract_path(self, uri: str) -> Path:
        """Extract file path from file:// URI.

        Args:
            uri: Full URI (e.g., 'file:///tmp/x' or 'file://localhost/tmp/x')

        Returns:
            pathlib.Path

        Raises:
            URINotSupported: If URI doesn't start with 'file://'
        """
        if not uri.startswith("file://"):
            raise URINotSupported(f"Unsupported URI prefix: {uri}")

        # Remove file:// prefix, handle both file:///path and file://localhost/path
        path_str = uri[7:]  # Remove 'file://'
        if path_str.startswith("localhost/"):
            path_str = "/" + path_str[10:]  # Remove 'localhost' prefix

        return Path(path_str)

    async def read_file(self, uri: str) -> bytes:
        """Read file via file:// URI.

        Args:
            uri: Full URI

        Returns:
            File contents as bytes

        Raises:
            FileNotFound: If file doesn't exist
            URINotSupported: If URI prefix not recognized
        """
        path = self._extract_path(uri)
        if not path.is_file():  # False for dirs and nonexistent
            raise FileNotFound(f"File not found: {uri}")
        # Use asyncio.to_thread for I/O
        return await asyncio.to_thread(path.read_bytes)

    async def write_file(self, uri: str, data: bytes) -> None:
        """Write file via file:// URI, creating parent directories.

        Args:
            uri: Full URI
            data: Bytes to write

        Raises:
            URINotSupported: If URI prefix not recognized
        """
        path = self._extract_path(uri)
        parent = path.parent

        # Create parent dirs
        await asyncio.to_thread(lambda: parent.mkdir(parents=True, exist_ok=True))
        # Write file
        await asyncio.to_thread(path.write_bytes, data)

    async def file_exists(self, uri: str) -> bool:
        """Check if file exists (False for directories).

        Args:
            uri: Full URI

        Returns:
            True if file exists and is regular file, False otherwise

        Raises:
            URINotSupported: If URI prefix not recognized
        """
        path = self._extract_path(uri)
        return await asyncio.to_thread(path.is_file)  # Returns False for dirs

    async def delete_file(self, uri: str) -> None:
        """Delete file (idempotent).

        Args:
            uri: Full URI

        Raises:
            URINotSupported: If URI prefix not recognized
        """
        path = self._extract_path(uri)

        def _delete():
            if path.exists():
                path.unlink()

        await asyncio.to_thread(_delete)
