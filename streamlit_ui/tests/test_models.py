"""Tests for model manager."""

from __future__ import annotations

import pytest

from streamlit_ui.crud.model_manager import ModelManager


@pytest.mark.asyncio
async def test_model_manager_init(config):
    """Test ModelManager initialization."""
    from streamlit_ui.neo4j_async import AsyncNeo4jClient
    from streamlit_ui.api_client import HTTPXClient

    db_client = AsyncNeo4jClient("neo4j://localhost:7687", "neo4j", "password")
    api_client = HTTPXClient("http://localhost:8000", "test-token")
    manager = ModelManager(db_client, api_client)

    assert manager.db is not None
    assert manager.api is not None

    await db_client.close()
    await api_client.close()
