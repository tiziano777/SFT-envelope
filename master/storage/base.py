"""Abstract base class for storage writers and error hierarchy."""

from __future__ import annotations

from abc import ABC, abstractmethod


# --- Error Hierarchy ---


class StorageError(Exception):
    """Base exception for all storage operations."""

    def __init__(self, message: str) -> None:
        """Initialize StorageError with message.

        Args:
            message: Error description
        """
        self.message = message
        super().__init__(message)


class FileNotFound(StorageError):
    """Raised when file doesn't exist on read or delete attempt."""

    pass


class URINotSupported(StorageError):
    """Raised when URI prefix is not recognized."""

    pass


# --- BaseStorageWriter ABC ---


class BaseStorageWriter(ABC):
    """Abstract base class for storage writer implementations.

    All subclasses must implement the 4 async methods:
    read_file, write_file, file_exists, delete_file.
    """

    @abstractmethod
    async def read_file(self, uri: str) -> bytes:
        """Read file contents from storage.

        Args:
            uri: Full URI (e.g., 'file:///tmp/x')

        Returns:
            File contents as bytes

        Raises:
            FileNotFound: If file doesn't exist
            URINotSupported: If URI prefix not recognized
        """
        pass

    @abstractmethod
    async def write_file(self, uri: str, data: bytes) -> None:
        """Write file to storage.

        Args:
            uri: Full URI
            data: Bytes to write

        Raises:
            URINotSupported: If URI prefix not recognized
        """
        pass

    @abstractmethod
    async def file_exists(self, uri: str) -> bool:
        """Check if file exists (returns False for directories).

        Args:
            uri: Full URI

        Returns:
            True if file exists and is regular file, False otherwise

        Raises:
            URINotSupported: If URI prefix not recognized
        """
        pass

    @abstractmethod
    async def delete_file(self, uri: str) -> None:
        """Delete file from storage (idempotent).

        Args:
            uri: Full URI

        Raises:
            URINotSupported: If URI prefix not recognized
        """
        pass
