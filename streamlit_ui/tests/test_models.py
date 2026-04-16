"""Tests for model repository."""

from __future__ import annotations

import pytest

from streamlit_ui.crud.repository.model_repository import ModelRepository


@pytest.mark.asyncio
async def test_model_repository_init(config):
    """Test ModelRepository initialization."""
    from streamlit_ui.db.neo4j_async import AsyncNeo4jClient

    db_client = AsyncNeo4jClient("neo4j://localhost:7687", "neo4j", "password")
    repo = ModelRepository(db_client)

    assert repo.db is not None

    await db_client.close()
