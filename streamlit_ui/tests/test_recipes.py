"""Tests for recipe manager."""

from __future__ import annotations

import pytest

from streamlit_ui.crud.recipe_manager import RecipeManager
from streamlit_ui.errors import UIError


@pytest.mark.asyncio
async def test_recipe_manager_init(mock_db_client, mock_api_client):
    """Test RecipeManager initialization."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    assert manager.db is not None
    assert manager.api is not None


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

    # Invalid: empty name
    with pytest.raises(ValueError, match="cannot be empty"):
        RecipeConfig(
            name="   ",
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


@pytest.mark.asyncio
async def test_recipe_name_unique_db_check(mock_db_client, mock_api_client):
    """Test RecipeManager enforces name uniqueness at DB level."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    # Mock existing recipe
    mock_db_client.query.return_value = [{"name": "existing_recipe"}]

    # Attempt to create duplicate should fail
    with pytest.raises(UIError, match="already exists"):
        await manager.create("existing_recipe", {})


@pytest.mark.asyncio
async def test_create_recipe(mock_db_client, mock_api_client):
    """Test creating a new recipe."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    # First call: check uniqueness (returns None)
    # Second call: create returns recipe data
    mock_db_client.query.side_effect = [
        None,  # get_by_name returns None (unique)
        [{"name": "new_recipe", "description": "Test recipe"}]  # create returns data
    ]

    result = await manager.create("new_recipe", {}, "Test recipe")
    assert result["name"] == "new_recipe"


@pytest.mark.asyncio
async def test_get_recipe_by_name(mock_db_client, mock_api_client):
    """Test retrieving recipe by name."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    recipe_data = {
        "name": "test_recipe",
        "entries": {"path1": "data1"},
        "created_at": "2026-04-14"
    }
    mock_db_client.query.return_value = [recipe_data]

    result = await manager.get_by_name("test_recipe")
    assert result == recipe_data


@pytest.mark.asyncio
async def test_get_recipe_by_name_not_found(mock_db_client, mock_api_client):
    """Test retrieving non-existent recipe returns None."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    mock_db_client.query.return_value = None

    result = await manager.get_by_name("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_update_recipe_name(mock_db_client, mock_api_client):
    """Test updating recipe name with uniqueness check."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    # Mock: get existing → check new name doesn't exist → update
    mock_db_client.query.side_effect = [
        [{"name": "old_name"}],           # get_by_name("old_name")
        None,                              # get_by_name("new_name")
        [{"name": "new_name"}]            # update returns new data
    ]

    result = await manager.update("old_name", new_name="new_name")
    assert result["name"] == "new_name"


@pytest.mark.asyncio
async def test_update_recipe_description(mock_db_client, mock_api_client):
    """Test updating recipe description."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    mock_db_client.query.side_effect = [
        [{"name": "recipe", "description": "old"}],
        [{"name": "recipe", "description": "new"}]
    ]

    result = await manager.update("recipe", description="new")
    assert result["description"] == "new"


@pytest.mark.asyncio
async def test_delete_recipe_with_confirmation(mock_db_client, mock_api_client):
    """Test deleting recipe."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    mock_db_client.query.side_effect = [
        [{"name": "recipe"}],  # exists check
        None                   # delete
    ]

    await manager.delete("recipe")
    # Verify delete was called
    assert mock_db_client.query.call_count == 2


@pytest.mark.asyncio
async def test_delete_recipe_not_found(mock_db_client, mock_api_client):
    """Test deleting non-existent recipe fails."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    mock_db_client.query.return_value = None

    with pytest.raises(UIError, match="not found"):
        await manager.delete("nonexistent")


@pytest.mark.asyncio
async def test_list_recipes(mock_db_client, mock_api_client):
    """Test listing all recipes."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    recipes = [
        {"name": "recipe1", "created_at": "2026-04-14"},
        {"name": "recipe2", "created_at": "2026-04-13"}
    ]
    mock_db_client.query.return_value = recipes

    result = await manager.list_all()
    assert result == recipes
