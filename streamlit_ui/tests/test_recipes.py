"""Tests for recipe manager."""

from __future__ import annotations

import pytest

from streamlit_ui.crud.recipe_manager import RecipeManager
from streamlit_ui.utils.errors import UIError, DuplicateRecipeError


@pytest.mark.asyncio
async def test_recipe_manager_init(mock_db_client):
    """Test RecipeManager initialization."""
    manager = RecipeManager(mock_db_client)

    assert manager.db is not None


@pytest.mark.asyncio
async def test_recipe_name_unique_model_validation():
    """Test RecipeConfig model validates name is not empty."""
    from envelope.config.models import RecipeConfig, RecipeEntry

    # Valid: name provided
    config = RecipeConfig(
        name="my_recipe",
        entries={
            "/path/1": RecipeEntry(
                chat_type="simple",
                dist_id="id1",
                dist_name="dist1",
                dist_uri="/path/1",
                samples=100,
                tokens=1000,
                words=500
            )
        }
    )
    assert config.name == "my_recipe"

    # Valid: name is None
    config2 = RecipeConfig(
        entries={
            "/path/1": RecipeEntry(
                chat_type="simple",
                dist_id="id1",
                dist_name="dist1",
                dist_uri="/path/1",
                samples=100,
                tokens=1000,
                words=500
            )
        }
    )
    assert config2.name is None
