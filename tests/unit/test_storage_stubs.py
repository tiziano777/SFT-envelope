"""Unit tests for master/storage/stubs.py."""

from __future__ import annotations

import pytest

from master.storage.stubs import S3StorageWriter, NFSStorageWriter


class TestS3StorageWriter:
    """Test S3StorageWriter stub implementation."""

    def test_instantiation(self):
        """Test S3StorageWriter can be instantiated."""
        writer = S3StorageWriter()
        assert writer is not None

    @pytest.mark.asyncio
    async def test_read_file_not_implemented(self):
        """Test read_file raises NotImplementedError."""
        writer = S3StorageWriter()
        with pytest.raises(NotImplementedError):
            await writer.read_file("s3://bucket/key")

    @pytest.mark.asyncio
    async def test_write_file_not_implemented(self):
        """Test write_file raises NotImplementedError."""
        writer = S3StorageWriter()
        with pytest.raises(NotImplementedError):
            await writer.write_file("s3://bucket/key", b"data")

    @pytest.mark.asyncio
    async def test_file_exists_not_implemented(self):
        """Test file_exists raises NotImplementedError."""
        writer = S3StorageWriter()
        with pytest.raises(NotImplementedError):
            await writer.file_exists("s3://bucket/key")

    @pytest.mark.asyncio
    async def test_delete_file_not_implemented(self):
        """Test delete_file raises NotImplementedError."""
        writer = S3StorageWriter()
        with pytest.raises(NotImplementedError):
            await writer.delete_file("s3://bucket/key")


class TestNFSStorageWriter:
    """Test NFSStorageWriter stub implementation."""

    def test_instantiation(self):
        """Test NFSStorageWriter can be instantiated."""
        writer = NFSStorageWriter()
        assert writer is not None

    @pytest.mark.asyncio
    async def test_read_file_not_implemented(self):
        """Test read_file raises NotImplementedError."""
        writer = NFSStorageWriter()
        with pytest.raises(NotImplementedError):
            await writer.read_file("nfs://server/path")

    @pytest.mark.asyncio
    async def test_write_file_not_implemented(self):
        """Test write_file raises NotImplementedError."""
        writer = NFSStorageWriter()
        with pytest.raises(NotImplementedError):
            await writer.write_file("nfs://server/path", b"data")

    @pytest.mark.asyncio
    async def test_file_exists_not_implemented(self):
        """Test file_exists raises NotImplementedError."""
        writer = NFSStorageWriter()
        with pytest.raises(NotImplementedError):
            await writer.file_exists("nfs://server/path")

    @pytest.mark.asyncio
    async def test_delete_file_not_implemented(self):
        """Test delete_file raises NotImplementedError."""
        writer = NFSStorageWriter()
        with pytest.raises(NotImplementedError):
            await writer.delete_file("nfs://server/path")
