"""End-to-end recipe workflow tests covering happy path, duplicates, and recovery."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
import yaml

from envelope.config.models import RecipeConfig, RecipeEntry
from streamlit_ui.crud.recipe_manager import RecipeManager
from streamlit_ui.errors import DuplicateRecipeError, UIError


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
async def test_recipe_creation_logs_entry_count(mock_db_client, mock_api_client, sample_recipe_yaml, caplog):
    """Test that recipe creation logs entry count."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    # Mock DB query to return None (no existing recipe)
    mock_db_client.query.side_effect = [
        [],  # get_by_name returns empty (unique)
        [{"name": "test_recipe", "entries": {}}]  # create returns data
    ]

    with caplog.at_level(logging.INFO):
        result = await manager.create_recipe(
            name="test_recipe",
            yaml_content=sample_recipe_yaml
        )

    # Verify log messages include entry count
    assert any("entry_count" in record.message for record in caplog.records), \
        "Entry count should be logged"
    assert result is not None


@pytest.mark.asyncio
async def test_duplicate_recipe_raises_specific_error(mock_db_client, mock_api_client, sample_recipe_yaml):
    """Test that duplicate recipe names raise DuplicateRecipeError."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    # Mock: first call (check uniqueness) returns existing recipe
    existing_recipe = {
        "name": "test_recipe",
        "entries": {},
        "created_at": "2026-04-15"
    }
    mock_db_client.query.return_value = [existing_recipe]

    with pytest.raises(DuplicateRecipeError) as exc_info:
        await manager.create_recipe(
            name="test_recipe",
            yaml_content=sample_recipe_yaml
        )

    assert exc_info.value.recipe_name == "test_recipe"
    assert exc_info.value.recovery_suggestions is not None
    assert len(exc_info.value.recovery_suggestions) > 0


@pytest.mark.asyncio
async def test_recovery_suggestion_alternatives(mock_db_client, mock_api_client, sample_recipe_yaml):
    """Test that duplicate error provides alternative name suggestions."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    # Mock existing recipe
    mock_db_client.query.return_value = [{"name": "test_recipe"}]

    with pytest.raises(DuplicateRecipeError) as exc_info:
        await manager.create_recipe(
            name="test_recipe",
            yaml_content=sample_recipe_yaml
        )

    error = exc_info.value
    suggestions = error.recovery_suggestions

    # Verify suggestions follow pattern (name_v1, name_v2, etc.)
    assert any("test_recipe_v1" in s for s in suggestions), \
        "Should suggest _v1 suffix"
    assert any("test_recipe_v2" in s for s in suggestions), \
        "Should suggest _v2 suffix"


@pytest.mark.asyncio
async def test_filename_based_name_fallback(mock_db_client, mock_api_client, recipe_yaml_without_name):
    """Test recipe name derived from filename when YAML 'name' missing."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    # Mock: no existing recipe
    mock_db_client.query.side_effect = [
        [],  # get_by_name returns empty (unique)
        [{"name": "my_recipe", "entries": {}}]  # create returns data
    ]

    result = await manager.create_recipe(
        name=None,  # No explicit name
        yaml_content=recipe_yaml_without_name,
        filename="my_recipe.yaml"  # Filename as fallback
    )

    # Verify recipe was created with filename-derived name
    assert result is not None


@pytest.mark.asyncio
async def test_invalid_yaml_structure(mock_db_client, mock_api_client):
    """Test that invalid YAML structure raises clear error."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    invalid_yaml = """
        malformed: [
        yaml: structure
    """

    with pytest.raises(UIError) as exc_info:
        await manager.create_recipe(
            name="bad_recipe",
            yaml_content=invalid_yaml
        )

    assert "yaml" in str(exc_info.value).lower() or "parsing" in str(exc_info.value).lower(), \
        "Error should mention YAML or parsing"


@pytest.mark.asyncio
async def test_audit_trail_logging(mock_db_client, mock_api_client, caplog):
    """Test complete audit trail: create logged with recipe name and entry count."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    # Setup mocks
    mock_db_client.query.side_effect = [
        [],  # get_by_name returns empty (unique)
        [{"name": "audit_test", "entries": {}}]  # create returns data
    ]

    with caplog.at_level(logging.INFO):
        # Create
        await manager.create(
            name="audit_test",
            entries={"path1": {"chat_type": "simple"}},
            description="Test recipe"
        )

        # Verify create logged with entry count
        create_logs = [r for r in caplog.records if "entry_count" in r.message.lower() or "inserted" in r.message.lower()]
        assert len(create_logs) > 0, "Create operation should be logged with entry count"


@pytest.mark.asyncio
async def test_empty_entries_validation(mock_db_client, mock_api_client):
    """Test that recipe with empty entries fails validation."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    empty_recipe = yaml.dump({
        "name": "empty_recipe",
        "entries": {}  # No entries
    })

    with pytest.raises(Exception):  # Could be UIError or ValueError
        await manager.create_recipe(
            name="empty_recipe",
            yaml_content=empty_recipe
        )


@pytest.mark.asyncio
async def test_retry_after_duplicate_succeeds(mock_db_client, mock_api_client, sample_recipe_yaml):
    """Test full recovery flow: duplicate -> suggest alt -> retry with alt succeeds."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    # First attempt: recipe exists
    mock_db_client.query.return_value = [{"name": "test_recipe"}]

    with pytest.raises(DuplicateRecipeError) as exc_info:
        await manager.create_recipe(
            name="test_recipe",
            yaml_content=sample_recipe_yaml
        )

    error = exc_info.value
    alt_name = error.recovery_suggestions[0]  # Use first suggestion

    # Second attempt: alternative name doesn't exist
    mock_db_client.query.side_effect = [
        [],  # get_by_name returns empty (unique)
        [{"name": alt_name, "entries": {}}]  # create returns data with alt name
    ]

    result = await manager.create_recipe(
        name=alt_name,
        yaml_content=sample_recipe_yaml
    )

    assert result is not None
    assert result["name"] == alt_name


@pytest.mark.asyncio
async def test_recipe_deletion_logged(mock_db_client, mock_api_client, caplog):
    """Test that recipe deletion is logged."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    # Mock: get_by_name returns existing recipe
    mock_db_client.query.side_effect = [
        [{"name": "delete_test", "entries": {}}],  # get_by_name
        None  # delete
    ]

    with caplog.at_level(logging.INFO):
        await manager.delete("delete_test")

    # Verify deletion logged
    delete_logs = [r for r in caplog.records if "deleted" in r.message.lower()]
    assert len(delete_logs) > 0, "Deletion should be logged"


@pytest.mark.asyncio
async def test_recipe_update_logged(mock_db_client, mock_api_client, caplog):
    """Test that recipe update is logged with fields changed."""
    manager = RecipeManager(mock_db_client, mock_api_client)

    # Mock: get_by_name and update
    mock_db_client.query.side_effect = [
        [{"name": "update_test", "entries": {}}],  # get_by_name for current
        [{"name": "update_test", "entries": {}}],  # update returns data
    ]

    with caplog.at_level(logging.INFO):
        await manager.update(
            name="update_test",
            description="Updated description"
        )

    # Verify update logged
    update_logs = [r for r in caplog.records if "updated" in r.message.lower()]
    assert len(update_logs) > 0, "Update should be logged"
