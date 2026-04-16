"""Tests for component repository."""

from __future__ import annotations

import pytest

from streamlit_ui.crud.repository.component_repository import ComponentRepository


@pytest.mark.asyncio
async def test_component_repository_init(config):
    """Test ComponentRepository initialization."""
    from streamlit_ui.db.neo4j_async import AsyncNeo4jClient

    db_client = AsyncNeo4jClient("neo4j://localhost:7687", "neo4j", "password")
    repo = ComponentRepository(db_client)

    assert repo.db is not None

    await db_client.close()
