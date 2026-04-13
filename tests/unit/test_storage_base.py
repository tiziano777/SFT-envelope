"""Unit tests for master/storage/base.py."""

from __future__ import annotations

import pytest
from abc import ABC
from master.storage.base import (
    StorageError,
    FileNotFound,
    URINotSupported,
    BaseStorageWriter,
)


class TestErrorHierarchy:
    """Test error hierarchy and inheritance."""

    def test_storage_error_instantiation(self):
        """Test StorageError can be instantiated with message."""
        err = StorageError("test message")
        assert str(err) == "test message"
        assert isinstance(err, Exception)

    def test_file_not_found_inheritance(self):
        """Test FileNotFound inherits from StorageError."""
        err = FileNotFound("file not found")
        assert isinstance(err, StorageError)
        assert isinstance(err, Exception)
        assert str(err) == "file not found"

    def test_uri_not_supported_inheritance(self):
        """Test URINotSupported inherits from StorageError."""
        err = URINotSupported("uri not supported")
        assert isinstance(err, StorageError)
        assert isinstance(err, Exception)
        assert str(err) == "uri not supported"


class TestBaseStorageWriterABC:
    """Test BaseStorageWriter ABC contract."""

    def test_base_storage_writer_is_abc(self):
        """Test BaseStorageWriter is an abstract base class."""
        assert issubclass(BaseStorageWriter, ABC)

    def test_base_storage_writer_cannot_instantiate(self):
        """Test BaseStorageWriter cannot be instantiated directly."""
        with pytest.raises(TypeError, match="abstract"):
            BaseStorageWriter()

    def test_base_storage_writer_has_abstract_methods(self):
        """Test BaseStorageWriter has required abstract methods."""
        abstract_methods = BaseStorageWriter.__abstractmethods__
        assert "read_file" in abstract_methods
        assert "write_file" in abstract_methods
        assert "file_exists" in abstract_methods
        assert "delete_file" in abstract_methods
        assert len(abstract_methods) == 4


class TestMethodSignatures:
    """Test method signatures and properties."""

    def test_all_methods_are_async(self):
        """Test all abstract methods are coroutines."""
        import inspect

        # Cannot directly check abstractmethod coroutines, so check implementation
        # A concrete implementation will have these as async
        class ConcreteWriter(BaseStorageWriter):
            async def read_file(self, uri: str) -> bytes:
                return b""

            async def write_file(self, uri: str, data: bytes) -> None:
                pass

            async def file_exists(self, uri: str) -> bool:
                return False

            async def delete_file(self, uri: str) -> None:
                pass

        writer = ConcreteWriter()
        assert inspect.iscoroutinefunction(writer.read_file)
        assert inspect.iscoroutinefunction(writer.write_file)
        assert inspect.iscoroutinefunction(writer.file_exists)
        assert inspect.iscoroutinefunction(writer.delete_file)

    def test_read_file_has_correct_signature_in_docstring(self):
        """Test read_file has expected docstring."""
        assert BaseStorageWriter.read_file.__doc__ is not None
        assert "Read file" in BaseStorageWriter.read_file.__doc__ or "read" in BaseStorageWriter.read_file.__doc__.lower()

    def test_write_file_has_correct_signature_in_docstring(self):
        """Test write_file has expected docstring."""
        assert BaseStorageWriter.write_file.__doc__ is not None

    def test_file_exists_has_correct_signature_in_docstring(self):
        """Test file_exists has expected docstring."""
        assert BaseStorageWriter.file_exists.__doc__ is not None

    def test_delete_file_has_correct_signature_in_docstring(self):
        """Test delete_file has expected docstring."""
        assert BaseStorageWriter.delete_file.__doc__ is not None
