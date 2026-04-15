"""Recipe CRUD manager."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

from envelope.config.models import RecipeConfig
from streamlit_ui.api_client import HTTPXClient
from streamlit_ui.errors import UIError, DuplicateRecipeError
from streamlit_ui.neo4j_async import AsyncNeo4jClient

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

    def _extract_name_from_filename(self, filename: str) -> str:
        """Extract recipe name from filename (only source of truth for naming).

        Removes file extension and returns the stem.
        Examples: "my_recipe.yaml" → "my_recipe", "recipe.yaml.bak" → "recipe.yaml"

        Args:
            filename: Source filename.

        Returns:
            Extracted recipe name.

        Raises:
            ValueError: If extracted name is empty or invalid.
        """
        path = Path(filename)
        name_with_extension = path.name
        if "." in name_with_extension:
            extracted_name = name_with_extension.rsplit(".", 1)[0]
        else:
            extracted_name = name_with_extension

        if not extracted_name or not extracted_name.strip():
            raise ValueError(
                f"Invalid filename: cannot extract recipe name from '{filename}'"
            )

        return extracted_name

    async def get_by_name(self, name: str) -> Optional[dict]:
        """Retrieve recipe by name.

        Args:
            name: Recipe name to lookup.

        Returns:
            Recipe data if found, None otherwise.

        Raises:
            UIError: On database query failure.
        """
        logger.debug(f"Querying recipe by name: {name}")
        try:
            query = """
            MATCH (r:Recipe {name: $name})
            RETURN r.name as name, r.entries as entries, r.created_at as created_at
            """
            result = await self.db.query(query, {"name": name})
            if result:
                entry_count = len(result[0].get('entries', {})) if result[0].get('entries') else 0
                logger.debug(f"Recipe found: {name} (entry_count={entry_count})")
                return result[0]
            logger.debug(f"Recipe not found: {name}")
            return None
        except Exception as e:
            logger.error(f"Failed to get recipe by name: {e}")
            raise UIError(f"Failed to retrieve recipe: {str(e)}")

    async def create(
        self,
        name: str,
        entries: dict,
        description: str = ""
    ) -> dict:
        """Create a new recipe.

        Args:
            name: Unique recipe name.
            entries: Dictionary mapping paths to RecipeEntry data.
            description: Optional recipe description.

        Returns:
            Created recipe data.

        Raises:
            DuplicateRecipeError: If name already exists.
            UIError: If database query fails.
        """
        # Check uniqueness
        logger.debug(f"Checking recipe uniqueness: name={name}")
        existing = await self.get_by_name(name)
        if existing:
            logger.warning(f"Recipe name already exists: {name}")
            # Generate alternative name suggestions
            suggestions = [
                f"{name}_v1",
                f"{name}_v2",
                f"{name}_backup",
            ]
            raise DuplicateRecipeError(name, recovery_suggestions=suggestions)

        try:
            entry_count = len(entries)
            logger.info(f"Inserting recipe: name={name}, entry_count={entry_count}")
            query = """
            CREATE (r:Recipe {
                name: $name,
                description: $description,
                entries: $entries,
                created_at: datetime()
            })
            RETURN r.name as name, r.description as description, r.entries as entries
            """
            result = await self.db.query(query, {
                "name": name,
                "description": description,
                "entries": entries
            })
            if result:
                logger.info(f"Recipe inserted successfully: name={result[0]['name']}")
                return result[0]
            raise UIError("Failed to create recipe")
        except Exception as e:
            if isinstance(e, (UIError, DuplicateRecipeError)):
                raise
            logger.error(f"Recipe insertion failed: {name}", exc_info=True)
            raise UIError(f"Failed to create recipe: {str(e)}")

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
        if not filename or not filename.strip():
            raise ValueError("Filename is required to derive recipe name")

        try:
            logger.debug(f"Recipe upload: filename={filename}, yaml_size={len(yaml_content)} bytes")
            data = yaml.safe_load(yaml_content)
            if not isinstance(data, dict):
                raise UIError("YAML must contain a dictionary")

            # Auto-detect format: if 'entries' key exists, use it; otherwise treat entire dict as entries
            if "entries" in data:
                entries_data = data.get("entries", {})
                yaml_description = data.get("description", "")
            else:
                # Treat entire dict as entries (URI-based format)
                logger.debug(f"Auto-wrapping entries-only YAML format: {len(data)} entries detected")
                entries_data = data
                yaml_description = ""

            # Create minimal RecipeConfig with only entries (name is optional at this stage)
            config = RecipeConfig(name=None, entries=entries_data)
            logger.info(f"Recipe YAML parsed: entries={len(config.entries)}")

            # Extract name from filename (only source of truth)
            recipe_name = self._extract_name_from_filename(filename)

            # Convert Pydantic RecipeEntry models to plain dicts for Neo4j storage
            entries_dict = {
                path: entry.model_dump(mode="json", exclude_none=True)
                for path, entry in config.entries.items()
            }

            # Use provided description or fall back to YAML description
            final_description = description if description else yaml_description

            logger.info(f"Creating recipe: name={recipe_name}, entry_count={len(entries_dict)}")
            result = await self.create(
                name=recipe_name,
                entries=entries_dict,
                description=final_description
            )
            logger.info(f"Recipe created successfully: name={result['name']}, entry_count={len(entries_dict)}")
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
        name: str,
        new_name: Optional[str] = None,
        description: Optional[str] = None
    ) -> dict:
        """Update recipe name and/or description.

        Args:
            name: Current recipe name (identifier).
            new_name: New name (must be unique if provided).
            description: New description.

        Returns:
            Updated recipe data.

        Raises:
            UIError: If recipe not found, new name already exists, or query fails.
        """
        # Verify current recipe exists
        existing = await self.get_by_name(name)
        if not existing:
            raise UIError(f"Recipe '{name}' not found")

        # Check new name uniqueness if changing
        if new_name and new_name != name:
            conflict = await self.get_by_name(new_name)
            if conflict:
                raise UIError(f"Recipe '{new_name}' already exists")

        try:
            updates: dict = {}
            if new_name:
                updates["name"] = new_name
            if description is not None:
                updates["description"] = description

            if not updates:
                return existing

            logger.info(f"Updating recipe: name={name}, fields={list(updates.keys())}")
            set_clause = ", ".join([f"r.{k} = ${k}" for k in updates.keys()])
            query = f"""
            MATCH (r:Recipe {{name: $old_name}})
            SET {set_clause}
            RETURN r.name as name, r.description as description, r.entries as entries
            """

            params = {"old_name": name, **updates}
            result = await self.db.query(query, params)
            if result:
                logger.info(f"Recipe updated: {name}")
                return result[0]
            raise UIError("Failed to update recipe")
        except Exception as e:
            if isinstance(e, UIError):
                raise
            logger.error(f"Recipe update failed: {name}", exc_info=True)
            raise UIError(f"Failed to update recipe: {str(e)}")

    async def delete(self, name: str) -> None:
        """Delete recipe by name.

        Args:
            name: Recipe name to delete.

        Raises:
            UIError: If recipe not found or query fails.
        """
        # Verify exists
        existing = await self.get_by_name(name)
        if not existing:
            raise UIError(f"Recipe '{name}' not found")

        try:
            logger.info(f"Deleting recipe: {name}")
            query = "MATCH (r:Recipe {name: $name}) DELETE r"
            await self.db.query(query, {"name": name})
            logger.info(f"Recipe deleted: {name}")
        except Exception as e:
            logger.error(f"Recipe deletion failed: {name}", exc_info=True)
            raise UIError(f"Failed to delete recipe: {str(e)}")

    async def list_all(self) -> list[dict]:
        """List all recipes.

        Returns:
            List of recipe data.

        Raises:
            UIError: On database query failure.
        """
        try:
            logger.debug("Listing all recipes")
            query = """
            MATCH (r:Recipe)
            RETURN r.name as name, r.description as description,
                   r.created_at as created_at, r.entries as entries
            ORDER BY r.created_at DESC
            """
            result = await self.db.query(query)
            logger.debug(f"Found {len(result)} recipes")
            return result or []
        except Exception as e:
            logger.error(f"Failed to list recipes: {e}")
            raise UIError(f"Failed to list recipes: {str(e)}")

    async def list_recipes(self, limit: int = 20) -> list[dict]:
        """List recipes with limit.

        Args:
            limit: Maximum recipes to return.

        Returns:
            List of recipe data.

        Raises:
            UIError: On database query failure.
        """
        try:
            logger.debug(f"Listing recipes (limit={limit})")
            query = """
            MATCH (r:Recipe)
            RETURN r.name as name, r.description as description,
                   r.created_at as created_at, r.entries as entries, id(r) as id
            ORDER BY r.created_at DESC
            LIMIT $limit
            """
            result = await self.db.query(query, {"limit": limit})
            logger.debug(f"Found {len(result) if result else 0} recipes")
            return result or []
        except Exception as e:
            logger.error(f"Failed to list recipes: {e}")
            raise UIError(f"Failed to list recipes: {str(e)}")

    async def search_recipes(self, query: str) -> list[dict]:
        """Search recipes by name.

        Args:
            query: Search query string.

        Returns:
            List of matching recipes.

        Raises:
            UIError: On database query failure.
        """
        try:
            logger.debug(f"Searching recipes: query={query}")
            cypher_query = """
            MATCH (r:Recipe)
            WHERE toLower(r.name) CONTAINS toLower($query)
            RETURN r.name as name, r.description as description,
                   r.created_at as created_at, r.entries as entries, id(r) as id
            ORDER BY r.created_at DESC
            """
            result = await self.db.query(cypher_query, {"query": query})
            logger.debug(f"Found {len(result) if result else 0} recipes matching '{query}'")
            return result or []
        except Exception as e:
            logger.error(f"Failed to search recipes: {e}")
            raise UIError(f"Failed to search recipes: {str(e)}")
