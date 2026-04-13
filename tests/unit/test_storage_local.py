"""Unit tests for master/storage/local.py."""

from __future__ import annotations

import asyncio
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from master.storage.local import LocalStorageWriter
from master.storage.base import FileNotFound, URINotSupported


@pytest.fixture
def temp_storage():
    """Create LocalStorageWriter with temp directory."""
    with TemporaryDirectory() as tmpdir:
        yield LocalStorageWriter(root_dir=tmpdir), Path(tmpdir)


class TestLocalStorageWriterInit:
    """Test LocalStorageWriter initialization."""

    def test_instantiation_with_root_dir(self):
        """Test instantiation with root directory."""
        with TemporaryDirectory() as tmpdir:
            writer = LocalStorageWriter(root_dir=tmpdir)
            assert writer.root_dir == Path(tmpdir)

    def test_instantiation_without_root_dir(self):
        """Test instantiation without root directory."""
        writer = LocalStorageWriter(root_dir=None)
        assert writer.root_dir is None


class TestLocalStorageWriterRead:
    """Test read_file method."""

    @pytest.mark.asyncio
    async def test_read_file_existing(self, temp_storage):
        """Test reading an existing file."""
        writer, tmpdir = temp_storage
        test_file = tmpdir / "test.txt"
        test_file.write_bytes(b"test data")

        uri = f"file://{test_file}"
        result = await writer.read_file(uri)
        assert result == b"test data"

    @pytest.mark.asyncio
    async def test_read_file_nonexistent(self, temp_storage):
        """Test reading nonexistent file raises FileNotFound."""
        writer, tmpdir = temp_storage
        nonexistent = tmpdir / "nonexistent.txt"
        uri = f"file://{nonexistent}"

        with pytest.raises(FileNotFound):
            await writer.read_file(uri)

    @pytest.mark.asyncio
    async def test_read_file_invalid_uri(self, temp_storage):
        """Test reading with invalid URI prefix raises URINotSupported."""
        writer, _ = temp_storage
        with pytest.raises(URINotSupported):
            await writer.read_file("s3://bucket/key")


class TestLocalStorageWriterWrite:
    """Test write_file method."""

    @pytest.mark.asyncio
    async def test_write_file_creates_file(self, temp_storage):
        """Test writing creates a new file."""
        writer, tmpdir = temp_storage
        test_file = tmpdir / "test.txt"
        uri = f"file://{test_file}"

        await writer.write_file(uri, b"test data")
        assert test_file.exists()
        assert test_file.read_bytes() == b"test data"

    @pytest.mark.asyncio
    async def test_write_file_creates_parent_dirs(self, temp_storage):
        """Test writing creates parent directories."""
        writer, tmpdir = temp_storage
        nested_file = tmpdir / "a" / "b" / "test.txt"
        uri = f"file://{nested_file}"

        await writer.write_file(uri, b"nested data")
        assert nested_file.exists()
        assert nested_file.read_bytes() == b"nested data"

    @pytest.mark.asyncio
    async def test_write_file_overwrites(self, temp_storage):
        """Test writing overwrites existing file."""
        writer, tmpdir = temp_storage
        test_file = tmpdir / "test.txt"
        test_file.write_bytes(b"old data")
        uri = f"file://{test_file}"

        await writer.write_file(uri, b"new data")
        assert test_file.read_bytes() == b"new data"

    @pytest.mark.asyncio
    async def test_write_file_invalid_uri(self, temp_storage):
        """Test writing with invalid URI raises URINotSupported."""
        writer, _ = temp_storage
        with pytest.raises(URINotSupported):
            await writer.write_file("s3://bucket/key", b"data")


class TestLocalStorageWriterExists:
    """Test file_exists method."""

    @pytest.mark.asyncio
    async def test_file_exists_true(self, temp_storage):
        """Test file_exists returns True for existing file."""
        writer, tmpdir = temp_storage
        test_file = tmpdir / "test.txt"
        test_file.write_bytes(b"data")
        uri = f"file://{test_file}"

        result = await writer.file_exists(uri)
        assert result is True

    @pytest.mark.asyncio
    async def test_file_exists_false_nonexistent(self, temp_storage):
        """Test file_exists returns False for nonexistent file."""
        writer, tmpdir = temp_storage
        nonexistent = tmpdir / "nonexistent.txt"
        uri = f"file://{nonexistent}"

        result = await writer.file_exists(uri)
        assert result is False

    @pytest.mark.asyncio
    async def test_file_exists_false_for_directory(self, temp_storage):
        """Test file_exists returns False for directories."""
        writer, tmpdir = temp_storage
        uri = f"file://{tmpdir}"

        result = await writer.file_exists(uri)
        assert result is False

    @pytest.mark.asyncio
    async def test_file_exists_invalid_uri(self, temp_storage):
        """Test file_exists with invalid URI raises URINotSupported."""
        writer, _ = temp_storage
        with pytest.raises(URINotSupported):
            await writer.file_exists("s3://bucket/key")


class TestLocalStorageWriterDelete:
    """Test delete_file method."""

    @pytest.mark.asyncio
    async def test_delete_file_removes_file(self, temp_storage):
        """Test delete_file removes the file."""
        writer, tmpdir = temp_storage
        test_file = tmpdir / "test.txt"
        test_file.write_bytes(b"data")
        uri = f"file://{test_file}"

        assert test_file.exists()
        await writer.delete_file(uri)
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_delete_file_idempotent(self, temp_storage):
        """Test delete_file is idempotent (no error on nonexistent)."""
        writer, tmpdir = temp_storage
        nonexistent = tmpdir / "nonexistent.txt"
        uri = f"file://{nonexistent}"

        # Should not raise
        await writer.delete_file(uri)

    @pytest.mark.asyncio
    async def test_delete_file_invalid_uri(self, temp_storage):
        """Test delete_file with invalid URI raises URINotSupported."""
        writer, _ = temp_storage
        with pytest.raises(URINotSupported):
            await writer.delete_file("s3://bucket/key")
