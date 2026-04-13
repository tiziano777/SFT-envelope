"""Tests for neo4j_async module."""

from __future__ import annotations

import pytest

from streamlit_ui.neo4j_async import AsyncNeo4jClient


@pytest.mark.asyncio
async def test_async_neo4j_client_init():
    """Test AsyncNeo4jClient initialization."""
    client = AsyncNeo4jClient(
        uri="neo4j://localhost:7687",
        user="neo4j",
        password="password",
    )
    assert client.uri == "neo4j://localhost:7687"
    assert client.user == "neo4j"
    await client.close()
