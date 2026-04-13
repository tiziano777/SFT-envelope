"""Unit tests for master/storage/resolver.py."""

from __future__ import annotations

import json
import os
import pytest
from unittest.mock import patch

from master.storage.resolver import URIResolver
from master.storage.base import URINotSupported
from master.storage.local import LocalStorageWriter
from master.storage.stubs import S3StorageWriter, NFSStorageWriter


class TestURIResolver:
    """Test URIResolver dispatch logic."""

    def test_default_backends_loaded(self):
        """Test URIResolver loads default backends."""
        resolver = URIResolver()
        # file:// should be LocalStorageWriter
        assert "file" in resolver.backends
        assert isinstance(resolver.backends["file"], LocalStorageWriter)

    def test_dispatch_to_local_writer(self):
        """Test dispatch routes file:// to LocalStorageWriter."""
        resolver = URIResolver()
        writer = resolver._get_writer_for_uri("file:///tmp/test.txt")
        assert isinstance(writer, LocalStorageWriter)

    def test_dispatch_to_s3_writer(self):
        """Test dispatch routes s3:// to S3StorageWriter."""
        resolver = URIResolver()
        writer = resolver._get_writer_for_uri("s3://bucket/key")
        assert isinstance(writer, S3StorageWriter)

    def test_dispatch_to_nfs_writer(self):
        """Test dispatch routes nfs:// to NFSStorageWriter."""
        resolver = URIResolver()
        writer = resolver._get_writer_for_uri("nfs://server/path")
        assert isinstance(writer, NFSStorageWriter)

    def test_unsupported_uri_prefix(self):
        """Test unsupported URI prefix raises URINotSupported."""
        resolver = URIResolver()
        with pytest.raises(URINotSupported):
            resolver._get_writer_for_uri("unknown://path")

    def test_custom_backends_from_env(self):
        """Test URIResolver respects STORAGE_BACKENDS env var."""
        backends_config = {
            "file": {"class": "LocalStorageWriter", "config": {}},
            "s3": {"class": "S3StorageWriter", "config": {}},
        }
        with patch.dict(os.environ, {"STORAGE_BACKENDS": json.dumps(backends_config)}):
            resolver = URIResolver()
            # Should still have both file and s3 backends
            assert "file" in resolver.backends
            assert "s3" in resolver.backends

    @pytest.mark.asyncio
    async def test_read_file_local(self):
        """Test reading a file via resolver."""
        import tempfile
        from pathlib import Path

        resolver = URIResolver()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_bytes(b"test data")
            uri = f"file://{test_file}"

            result = await resolver.read_file(uri)
            assert result == b"test data"

    @pytest.mark.asyncio
    async def test_write_file_local(self):
        """Test writing a file via resolver."""
        import tempfile
        from pathlib import Path

        resolver = URIResolver()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            uri = f"file://{test_file}"

            await resolver.write_file(uri, b"test data")
            assert test_file.exists()
            assert test_file.read_bytes() == b"test data"

    @pytest.mark.asyncio
    async def test_file_exists_local(self):
        """Test checking file existence via resolver."""
        import tempfile
        from pathlib import Path

        resolver = URIResolver()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_bytes(b"data")
            uri = f"file://{test_file}"

            result = await resolver.file_exists(uri)
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_file_local(self):
        """Test deleting a file via resolver."""
        import tempfile
        from pathlib import Path

        resolver = URIResolver()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_bytes(b"data")
            uri = f"file://{test_file}"

            await resolver.delete_file(uri)
            assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_s3_not_implemented(self):
        """Test S3 operations raise NotImplementedError."""
        resolver = URIResolver()
        with pytest.raises(NotImplementedError):
            await resolver.read_file("s3://bucket/key")
