"""Tests for connection layer."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from envelope.middleware.worker.http_connection import HTTPConnection
from envelope.middleware.worker.ssh_connection import SSHConnection
from envelope.middleware.shared.connection import BaseConnection


@pytest.fixture
def http_conn():
    return HTTPConnection("http://localhost:8000", api_key="test-key")


@pytest.fixture
def ssh_conn():
    return SSHConnection("master.local", "user")


@pytest.fixture
def tmp_file(tmp_path):
    f = tmp_path / "test.json"
    f.write_text('{"test": "data"}')
    return f


@pytest.mark.asyncio
async def test_http_send_metadata_success(http_conn):
    """HTTPConnection.send_metadata succeeds."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        result = await http_conn.send_metadata({"event_id": "ev-1"})

        assert result is True


@pytest.mark.asyncio
async def test_http_send_metadata_failure(http_conn):
    """HTTPConnection.send_metadata fails gracefully."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        result = await http_conn.send_metadata({"event_id": "ev-1"})

        assert result is False


@pytest.mark.asyncio
async def test_http_transfer_file_success(http_conn, tmp_file):
    """HTTPConnection.transfer_file sends file."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        result = await http_conn.transfer_file(tmp_file, "file:///checkpoint.json")

        assert result is True


@pytest.mark.asyncio
async def test_http_health_check_ok(http_conn):
    """HTTPConnection.health_check succeeds."""
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        result = await http_conn.health_check()

        assert result is True


@pytest.mark.asyncio
async def test_http_health_check_fail(http_conn):
    """HTTPConnection.health_check fails."""
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("Master unreachable")

        result = await http_conn.health_check()

        assert result is False


def test_ssh_connection_send_metadata_not_implemented(ssh_conn):
    """SSHConnection.send_metadata raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        import asyncio
        asyncio.run(ssh_conn.send_metadata({}))


def test_ssh_connection_transfer_file_not_implemented(ssh_conn):
    """SSHConnection.transfer_file raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        import asyncio
        asyncio.run(ssh_conn.transfer_file(Path("test"), "file:///test"))


def test_base_connection_is_abstract():
    """BaseConnection cannot be instantiated."""
    with pytest.raises(TypeError):
        BaseConnection()
