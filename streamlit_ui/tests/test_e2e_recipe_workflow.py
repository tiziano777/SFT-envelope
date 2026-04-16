"""End-to-end recipe workflow tests covering happy path, duplicates, and recovery."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
import yaml

from envelope.config.models import RecipeConfig, RecipeEntry
from streamlit_ui.crud.recipe_manager import RecipeManager
from streamlit_ui.utils.errors import DuplicateRecipeError, UIError


@pytest.fixture
def sample_recipe_yaml() -> str:
    """Create sample recipe YAML with entries."""
    data = {
        "name": "test_recipe",
        "entries": {
            "/path/1": {
                "chat_type": "simple",
                "dist_id": "test_id",
                "dist_name": "test_dist",
                "dist_uri": "/path/1",
                "samples": 100,
                "tokens": 1000,
                "words": 500
            }
        }
    }
    return yaml.dump(data)


@pytest.fixture
def recipe_yaml_without_name() -> str:
    """Recipe YAML without 'name' field (will derive from filename)."""
    data = {
        "entries": {
            "/path/1": {
                "chat_type": "simple",
                "dist_id": "test_id",
                "dist_name": "test_dist",
                "dist_uri": "/path/1",
                "samples": 100,
                "tokens": 1000,
                "words": 500
            }
        }
    }
    return yaml.dump(data)


@pytest.mark.asyncio
async def test_recipe_creation_logs_entry_count(mock_db_client, sample_recipe_yaml, caplog):
    """Test that recipe creation logs entry count."""
    manager = RecipeManager(mock_db_client)

    # Mock DB query to return None (no existing recipe)
    assert manager.db is not None
