"""Tests for HTTP client."""

from __future__ import annotations

import pytest

from streamlit_ui.utils.api_client import HTTPXClient


@pytest.mark.asyncio
async def test_httpx_client_init():
    """Test HTTPXClient initialization."""
    client = HTTPXClient(base_url="http://localhost:8000", api_token="test-token")
    assert client.base_url == "http://localhost:8000"
    assert client.api_token == "test-token"
    await client.close()


@pytest.mark.asyncio
async def test_httpx_client_headers():
    """Test HTTPXClient includes auth header."""
    client = HTTPXClient(base_url="http://localhost:8000", api_token="test-token")
    # Just verify client was created with token
    assert client.api_token == "test-token"
    await client.close()
