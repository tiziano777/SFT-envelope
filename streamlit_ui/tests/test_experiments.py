"""Tests for experiment repository."""

from __future__ import annotations

import pytest

from streamlit_ui.crud.repository.experiment_repository import ExperimentRepository


@pytest.mark.asyncio
async def test_experiment_repository_init(config):
    """Test ExperimentRepository initialization."""
    from streamlit_ui.db.neo4j_async import AsyncNeo4jClient

    db_client = AsyncNeo4jClient("neo4j://localhost:7687", "neo4j", "password")
    repo = ExperimentRepository(db_client)

    assert repo.db is not None

    await db_client.close()
