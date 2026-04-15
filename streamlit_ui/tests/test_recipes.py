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


@pytest.mark.asyncio
async def test_create_recipe_with_entries(mock_db_client, mock_api_client):
    """Test creating recipe properly saves entries from RecipeConfig."""
    from envelope.config.models import RecipeConfig, RecipeEntry
    
    manager = RecipeManager(mock_db_client, mock_api_client)
    
    # Setup: RecipeConfig with entries
    entries_dict = {
        "/dataset/path1": {
            "chat_type": "simple",
            "dist_id": "dist_001",
            "dist_name": "Dataset 1",
            "dist_uri": "/mnt/data/dataset1.jsonl",
            "samples": 1000,
            "tokens": 500000,
            "words": 100000,
            "replica": 1
        }
    }
    
    # Mock: unique check passes, create returns recipe with entries
    mock_db_client.query.side_effect = [
        None,  # get_by_name returns None (unique)
        [{"name": "test_recipe", "entries": entries_dict}]  # create returns recipe
    ]
    
    result = await manager.create(
        name="test_recipe",
        entries=entries_dict,
        description="Test recipe"
    )
    
    # Verify entries are in result
    assert result["entries"] == entries_dict
    assert result["name"] == "test_recipe"


@pytest.mark.asyncio
async def test_duplicate_recipe_name_error_message(mock_db_client, mock_api_client):
    """Test duplicate recipe name raises UIError with user-friendly message."""
    manager = RecipeManager(mock_db_client, mock_api_client)
    
    # Mock: get_by_name returns existing recipe
    mock_db_client.query.return_value = [{"name": "existing_recipe"}]
    
    with pytest.raises(UIError) as exc_info:
        await manager.create(
            name="existing_recipe",
            entries={},
            description=""
        )
    
    # Verify user-friendly error message
    error = exc_info.value
    assert "already exists" in error.user_message.lower()
    assert "existing_recipe" in error.user_message
    assert "⚠️" in error.user_message


@pytest.mark.asyncio
async def test_list_recipes_includes_entries(mock_db_client, mock_api_client):
    """Test listing recipes includes entries field."""
    manager = RecipeManager(mock_db_client, mock_api_client)
    
    entries = {
        "/path1": {
            "dist_id": "dist_001",
            "samples": 1000,
            "tokens": 500000,
            "words": 100000
        }
    }
    
    recipes = [
        {
            "name": "recipe1",
            "description": "Test",
            "entries": entries,
            "created_at": "2026-04-14",
            "id": "recipe_1"
        }
    ]
    
    mock_db_client.query.return_value = recipes
    
    result = await manager.list_recipes(limit=20)
    
    # Verify entries are included
    assert len(result) == 1
    assert result[0]["entries"] == entries
    assert result[0]["id"] == "recipe_1"


@pytest.mark.asyncio
async def test_search_recipes_includes_entries(mock_db_client, mock_api_client):
    """Test searching recipes includes entries field."""
    manager = RecipeManager(mock_db_client, mock_api_client)
    
    entries = {
        "/path1": {
            "dist_id": "dist_001",
            "samples": 500,
            "tokens": 250000,
            "words": 50000
        }
    }
    
    recipes = [
        {
            "name": "search_result",
            "entries": entries,
            "created_at": "2026-04-14",
            "id": "recipe_2"
        }
    ]
    
    mock_db_client.query.return_value = recipes

    result = await manager.search_recipes("search")

    # Verify entries are included in search results
    assert len(result) == 1
    assert result[0]["entries"] == entries


@pytest.mark.asyncio
async def test_recipe_config_ensure_name_from_filename():
    """Test RecipeConfig.ensure_name() extracts name from filename."""
    from envelope.config.models import RecipeConfig, RecipeEntry

    config = RecipeConfig(
        name=None,
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

    # Initially None
    assert config.name is None

    # Extract from "my_recipe.yaml" → "my_recipe"
    config.ensure_name("my_recipe.yaml")
    assert config.name == "my_recipe"


@pytest.mark.asyncio
async def test_recipe_config_ensure_name_preserves_existing():
    """Test RecipeConfig.ensure_name() doesn't override existing name."""
    from envelope.config.models import RecipeConfig, RecipeEntry

    config = RecipeConfig(
        name="existing_name",
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

    # Has existing name
    assert config.name == "existing_name"

    # ensure_name() should not override
    config.ensure_name("new_recipe.yaml")
    assert config.name == "existing_name"


@pytest.mark.asyncio
async def test_recipe_config_ensure_name_handles_edge_cases():
    """Test RecipeConfig.ensure_name() handles edge cases like .yaml.bak."""
    from envelope.config.models import RecipeConfig, RecipeEntry

    config = RecipeConfig(
        name=None,
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

    # "recipe.yaml.bak" should extract "recipe.yaml"
    config.ensure_name("recipe.yaml.bak")
    assert config.name == "recipe.yaml"


@pytest.mark.asyncio
async def test_extract_recipe_name_priority_param_over_all():
    """Test _extract_recipe_name() prioritizes name_param over YAML and filename."""
    from envelope.config.models import RecipeConfig, RecipeEntry

    manager = RecipeManager(None, None)

    config = RecipeConfig(
        name="yaml_name",
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

    # name_param should win
    result = manager._extract_recipe_name(
        name_param="param_name",
        filename="filename_name.yaml",
        config=config
    )
    assert result == "param_name"


@pytest.mark.asyncio
async def test_extract_recipe_name_priority_yaml_over_filename():
    """Test _extract_recipe_name() prioritizes YAML name over filename."""
    from envelope.config.models import RecipeConfig, RecipeEntry

    manager = RecipeManager(None, None)

    config = RecipeConfig(
        name="yaml_name",
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

    # YAML name should win over filename
    result = manager._extract_recipe_name(
        name_param=None,
        filename="filename_name.yaml",
        config=config
    )
    assert result == "yaml_name"


@pytest.mark.asyncio
async def test_extract_recipe_name_fallback_to_filename():
    """Test _extract_recipe_name() falls back to filename when no other source."""
    from envelope.config.models import RecipeConfig, RecipeEntry

    manager = RecipeManager(None, None)

    config = RecipeConfig(
        name=None,
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

    # Should fall back to filename
    result = manager._extract_recipe_name(
        name_param=None,
        filename="my_recipe.yaml",
        config=config
    )
    assert result == "my_recipe"


@pytest.mark.asyncio
async def test_extract_recipe_name_raises_when_no_source():
    """Test _extract_recipe_name() raises ValueError when no name source available."""
    from envelope.config.models import RecipeConfig, RecipeEntry

    manager = RecipeManager(None, None)

    config = RecipeConfig(
        name=None,
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

    # Should raise ValueError
    with pytest.raises(ValueError, match="Recipe name required"):
        manager._extract_recipe_name(
            name_param=None,
            filename=None,
            config=config
        )


@pytest.mark.asyncio
async def test_create_recipe_with_filename_fallback(mock_db_client, mock_api_client):
    """Test create_recipe() uses filename when YAML has no name."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    yaml_content = """
entries:
  /path/1:
    chat_type: simple
    dist_id: id1
    dist_name: dist1
    dist_uri: /path/1
    samples: 100
    tokens: 1000
    words: 500
"""

    # Mock: unique check passes, create returns recipe
    mock_db_client.query.side_effect = [
        None,  # get_by_name returns None (unique)
        [{"name": "my_recipe", "entries": {}}]  # create returns recipe
    ]

    result = await manager.create_recipe(
        name=None,
        yaml_content=yaml_content,
        filename="my_recipe.yaml"
    )

    assert result["name"] == "my_recipe"


@pytest.mark.asyncio
async def test_create_recipe_yaml_name_takes_precedence(mock_db_client, mock_api_client):
    """Test create_recipe() prefers YAML name over filename."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    yaml_content = """
name: yaml_name
entries:
  /path/1:
    chat_type: simple
    dist_id: id1
    dist_name: dist1
    dist_uri: /path/1
    samples: 100
    tokens: 1000
    words: 500
"""

    # Mock: unique check passes, create returns recipe
    mock_db_client.query.side_effect = [
        None,  # get_by_name returns None (unique)
        [{"name": "yaml_name", "entries": {}}]  # create returns recipe
    ]

    result = await manager.create_recipe(
        name=None,
        yaml_content=yaml_content,
        filename="filename_name.yaml"
    )

    assert result["name"] == "yaml_name"


@pytest.mark.asyncio
async def test_recipe_config_ensure_name_from_filename():
    """Test RecipeConfig.ensure_name() extracts name from filename."""
    from envelope.config.models import RecipeConfig, RecipeEntry

    config = RecipeConfig(
        name=None,
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

    # Initially None
    assert config.name is None

    # Extract from "my_recipe.yaml" → "my_recipe"
    config.ensure_name("my_recipe.yaml")
    assert config.name == "my_recipe"


@pytest.mark.asyncio
async def test_recipe_config_ensure_name_preserves_existing():
    """Test RecipeConfig.ensure_name() doesn't override existing name."""
    from envelope.config.models import RecipeConfig, RecipeEntry

    config = RecipeConfig(
        name="existing_name",
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

    # Has existing name
    assert config.name == "existing_name"

    # ensure_name() should not override
    config.ensure_name("new_recipe.yaml")
    assert config.name == "existing_name"


@pytest.mark.asyncio
async def test_recipe_config_ensure_name_handles_edge_cases():
    """Test RecipeConfig.ensure_name() handles edge cases like .yaml.bak."""
    from envelope.config.models import RecipeConfig, RecipeEntry

    config = RecipeConfig(
        name=None,
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

    # "recipe.yaml.bak" should extract "recipe.yaml"
    config.ensure_name("recipe.yaml.bak")
    assert config.name == "recipe.yaml"


@pytest.mark.asyncio
async def test_extract_recipe_name_priority_param_over_all():
    """Test _extract_recipe_name() prioritizes name_param over YAML and filename."""
    from envelope.config.models import RecipeConfig, RecipeEntry

    manager = RecipeManager(None, None)

    config = RecipeConfig(
        name="yaml_name",
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

    # name_param should win
    result = manager._extract_recipe_name(
        name_param="param_name",
        filename="filename_name.yaml",
        config=config
    )
    assert result == "param_name"


@pytest.mark.asyncio
async def test_extract_recipe_name_priority_yaml_over_filename():
    """Test _extract_recipe_name() prioritizes YAML name over filename."""
    from envelope.config.models import RecipeConfig, RecipeEntry

    manager = RecipeManager(None, None)

    config = RecipeConfig(
        name="yaml_name",
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

    # YAML name should win over filename
    result = manager._extract_recipe_name(
        name_param=None,
        filename="filename_name.yaml",
        config=config
    )
    assert result == "yaml_name"


@pytest.mark.asyncio
async def test_extract_recipe_name_fallback_to_filename():
    """Test _extract_recipe_name() falls back to filename when no other source."""
    from envelope.config.models import RecipeConfig, RecipeEntry

    manager = RecipeManager(None, None)

    config = RecipeConfig(
        name=None,
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

    # Should fall back to filename
    result = manager._extract_recipe_name(
        name_param=None,
        filename="my_recipe.yaml",
        config=config
    )
    assert result == "my_recipe"


@pytest.mark.asyncio
async def test_extract_recipe_name_raises_when_no_source():
    """Test _extract_recipe_name() raises ValueError when no name source available."""
    from envelope.config.models import RecipeConfig, RecipeEntry

    manager = RecipeManager(None, None)

    config = RecipeConfig(
        name=None,
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

    # Should raise ValueError
    with pytest.raises(ValueError, match="Recipe name required"):
        manager._extract_recipe_name(
            name_param=None,
            filename=None,
            config=config
        )


@pytest.mark.asyncio
async def test_create_recipe_with_filename_fallback(mock_db_client, mock_api_client):
    """Test create_recipe() uses filename when YAML has no name."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    yaml_content = """
entries:
  /path/1:
    chat_type: simple
    dist_id: id1
    dist_name: dist1
    dist_uri: /path/1
    samples: 100
    tokens: 1000
    words: 500
"""

    # Mock: unique check passes, create returns recipe
    mock_db_client.query.side_effect = [
        None,  # get_by_name returns None (unique)
        [{"name": "my_recipe", "entries": {}}]  # create returns recipe
    ]

    result = await manager.create_recipe(
        name=None,
        yaml_content=yaml_content,
        filename="my_recipe.yaml"
    )

    assert result["name"] == "my_recipe"


@pytest.mark.asyncio
async def test_create_recipe_yaml_name_takes_precedence(mock_db_client, mock_api_client):
    """Test create_recipe() prefers YAML name over filename."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    yaml_content = """
name: yaml_name
entries:
  /path/1:
    chat_type: simple
    dist_id: id1
    dist_name: dist1
    dist_uri: /path/1
    samples: 100
    tokens: 1000
    words: 500
"""

    # Mock: unique check passes, create returns recipe
    mock_db_client.query.side_effect = [
        None,  # get_by_name returns None (unique)
        [{"name": "yaml_name", "entries": {}}]  # create returns recipe
    ]

    result = await manager.create_recipe(
        name=None,
        yaml_content=yaml_content,
        filename="filename_name.yaml"
    )

    assert result["name"] == "yaml_name"
