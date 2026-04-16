"""Recipe CRUD manager."""

from __future__ import annotations

import logging
import uuid
from typing import Optional

import yaml

from envelope.config.models import RecipeConfig
from streamlit_ui.api_client import HTTPXClient
from streamlit_ui.errors import UIError, DuplicateRecipeError
from streamlit_ui.neo4j_async import AsyncNeo4jClient
from streamlit_ui.crud.repository.recipe_repository import RecipeRepository

logger = logging.getLogger(__name__)


class RecipeManager:
    """Manager for Recipe CRUD operations."""

    def __init__(self, db_client: AsyncNeo4jClient, api_client: HTTPXClient):
        """Initialize RecipeManager.

        Args:
            db_client: AsyncNeo4jClient for Neo4j queries.
            api_client: HTTPXClient for Master API calls.
        """
        self.db = db_client
        self.api = api_client
        self.repo = RecipeRepository(db_client)

    async def get_by_name(self, name: str) -> Optional[dict]:
        """Retrieve recipe by name via repository."""
        return await self.repo.get_by_name(name)

    async def get_by_recipe_id(self, recipe_id: str) -> Optional[dict]:
        """Retrieve recipe by recipe_id via repository."""
        return await self.repo.get_by_recipe_id(recipe_id)

    async def create(
        self,
        name: Optional[str],
        entries: dict,
        description: str = "",
        recipe_id: Optional[str] = None,
    ) -> dict:
        """Create a new recipe via repository.

        Args:
            name: Unique recipe name.
            entries: Dictionary mapping paths to RecipeEntry data.
            description: Optional recipe description.
            recipe_id: Optional recipe ID (generated if not provided).

        Returns:
            Created recipe data.
        """
        if recipe_id is None:
            recipe_id = str(uuid.uuid4())

        return await self.repo.create(
            recipe_id=recipe_id,
            name=name,
            entries=entries,
            description=description,
        )

    async def create_recipe(
        self,
        yaml_content: str = "",
        filename: str = "",
        description: str = ""
    ) -> dict:
        """Create recipe from YAML content with deterministic name from filename.

        Recipe name is extracted from filename (without extension).
        This ensures a single, unambiguous source of truth for recipe naming.

        YAML format:
        - entries: {path1: {...}, path2: {...}}
        - description: (optional)

        Args:
            yaml_content: YAML content string containing entries and optional description.
            filename: Source filename (required) - recipe name is extracted from this.
            description: Optional recipe description (overrides YAML description if provided).

        Returns:
            Created recipe data.

        Raises:
            ValueError: If filename is missing or empty.
            UIError: If YAML parsing or creation fails.
        """
        try:
            logger.debug("Recipe upload: yaml_size=%d bytes", len(yaml_content))
            data = yaml.safe_load(yaml_content)
            if not isinstance(data, dict):
                raise UIError("YAML must contain a dictionary")

            # Expect top-level keys: name (optional), description (optional), recipe_id (optional), entries (required)
            entries_data = data.get("entries")
            if entries_data is None or not isinstance(entries_data, dict):
                raise UIError("YAML must contain top-level 'entries' mapping of dataset URIs to metadata")

            yaml_name = data.get("name")
            yaml_description = data.get("description") if "description" in data else None
            yaml_recipe_id = data.get("recipe_id")

            # Create RecipeConfig to validate entries
            config = RecipeConfig(name=yaml_name, entries=entries_data)
            logger.info(f"Recipe YAML parsed: name={config.name} entries={len(config.entries)}")

            # Convert entries to plain dicts
            entries_dict = {
                path: entry.model_dump(mode="json", exclude_none=True)
                for path, entry in config.entries.items()
            }

            # Determine recipe_id: use provided or generate new UUID
            if yaml_recipe_id:
                recipe_id = str(yaml_recipe_id)
            else:
                import uuid

                recipe_id = str(uuid.uuid4())

            final_description = description if description is not None else yaml_description

            logger.info("Creating recipe: recipe_id=%s name=%s entry_count=%d", recipe_id, config.name, len(entries_dict))
            result = await self.create(
                name=config.name,
                entries=entries_dict,
                description=final_description,
                recipe_id=recipe_id,
            )
            # attach recipe_id to returned result if not present
            if result and "recipe_id" not in result:
                result["recipe_id"] = recipe_id
            logger.info("Recipe created successfully: recipe_id=%s name=%s entry_count=%d", recipe_id, result.get("name"), len(entries_dict))
            return result
        except ValueError as e:
            raise UIError(f"Invalid filename or YAML: {str(e)}")
        except (UIError, DuplicateRecipeError) as e:
            raise
        except Exception as e:
            logger.error(f"Recipe creation failed: {str(e)}", exc_info=True)
            raise UIError(f"Failed to create recipe: {str(e)}")

    async def update(
        self,
        recipe_id: Optional[str] = None,
        new_name: Optional[str] = None,
        description: Optional[str] = None,
        scope: Optional[str] = None,
        tasks: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
    ) -> dict:
        """Update recipe metadata.

        Args:
            recipe_id: Recipe ID to update.
            new_name: New name (must be unique if provided).
            description: New description.
            scope: New scope.
            tasks: New tasks list.
            tags: New tags list.

        Returns:
            Updated recipe data.
        """
        return await self.repo.update(
            recipe_id=recipe_id,
            new_name=new_name,
            description=description,
            scope=scope,
            tasks=tasks,
            tags=tags,
        )

    async def delete(self, recipe_id: str) -> None:
        """Delete recipe (disabled - use repository layer for future deletion logic).

        WARNING: Delete operations are commented out to preserve data integrity.
        Future implementation should include comprehensive dependency checking.

        Args:
            recipe_id: Recipe ID to delete.
        """
        # TODO: Implement deletion with proper dependency checking
        # Current implementation disabled for safety - recipes are immutable after creation
        raise UIError("Recipe deletion is not implemented. Recipes are immutable.")

    async def list_all(self) -> list[dict]:
        """List all recipes via repository."""
        return await self.repo.list_all()

    async def list_recipes(self, limit: int = 20) -> list[dict]:
        """List recipes with limit via repository."""
        return await self.repo.list_with_limit(limit=limit)

    async def search_recipes(self, query: str) -> list[dict]:
        """Search recipes by name via repository."""
        return await self.repo.search(query)
