"""Recipe CRUD manager."""

from __future__ import annotations

import logging
from typing import Optional

import yaml

from envelope.config.models import RecipeConfig
from streamlit_ui.api_client import HTTPXClient
from streamlit_ui.errors import UIError
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

    async def get_by_name(self, name: str) -> Optional[dict]:
        """Retrieve recipe by name.

        Args:
            name: Recipe name to lookup.

        Returns:
            Recipe data if found, None otherwise.

        Raises:
            UIError: On database query failure.
        """
        try:
            query = """
            MATCH (r:Recipe {name: $name})
            RETURN r.name as name, r.entries as entries, r.created_at as created_at
            """
            result = await self.db.query(query, {"name": name})
            if result:
                return result[0]
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
            UIError: If name already exists or database query fails.
        """
        # Check uniqueness
        existing = await self.get_by_name(name)
        if existing:
            raise UIError(
                user_message=f"⚠️ Recipe name already exists: '{name}'",
                details="Change the recipe name or rename the YAML file before uploading."
            )

        try:
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
                return result[0]
            raise UIError("Failed to create recipe")
        except Exception as e:
            if isinstance(e, UIError):
                raise
            logger.error(f"Failed to create recipe: {e}")
            raise UIError(f"Failed to create recipe: {str(e)}")

    async def create_recipe(self, name: str, yaml_content: str) -> dict:
        """Create recipe from YAML content.

        Args:
            name: Recipe name.
            yaml_content: YAML content string.

        Returns:
            Created recipe data.

        Raises:
            UIError: If YAML parsing or creation fails.
        """
        try:
            data = yaml.safe_load(yaml_content)
            if not isinstance(data, dict):
                raise UIError("YAML must contain a dictionary")

            config = RecipeConfig(**data)
            return await self.create(
                name=name or config.name or "untitled",
                entries=config.entries,  # Use validated entries from RecipeConfig, not raw data
                description=data.get("description", "")
            )
        except ValueError as e:
            raise UIError(f"YAML parsing error: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to create recipe from YAML: {e}")
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

            set_clause = ", ".join([f"r.{k} = ${k}" for k in updates.keys()])
            query = f"""
            MATCH (r:Recipe {{name: $old_name}})
            SET {set_clause}
            RETURN r.name as name, r.description as description, r.entries as entries
            """

            params = {"old_name": name, **updates}
            result = await self.db.query(query, params)
            if result:
                return result[0]
            raise UIError("Failed to update recipe")
        except Exception as e:
            if isinstance(e, UIError):
                raise
            logger.error(f"Failed to update recipe: {e}")
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
            query = "MATCH (r:Recipe {name: $name}) DELETE r"
            await self.db.query(query, {"name": name})
            logger.info(f"Deleted recipe: {name}")
        except Exception as e:
            logger.error(f"Failed to delete recipe: {e}")
            raise UIError(f"Failed to delete recipe: {str(e)}")

    async def list_all(self) -> list[dict]:
        """List all recipes.

        Returns:
            List of recipe data.

        Raises:
            UIError: On database query failure.
        """
        try:
            query = """
            MATCH (r:Recipe)
            RETURN r.name as name, r.description as description,
                   r.created_at as created_at, r.entries as entries
            ORDER BY r.created_at DESC
            """
            result = await self.db.query(query)
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
            query = """
            MATCH (r:Recipe)
            RETURN r.name as name, r.description as description,
                   r.created_at as created_at, r.entries as entries, id(r) as id
            ORDER BY r.created_at DESC
            LIMIT $limit
            """
            result = await self.db.query(query, {"limit": limit})
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
            cypher_query = """
            MATCH (r:Recipe)
            WHERE toLower(r.name) CONTAINS toLower($query)
            RETURN r.name as name, r.description as description,
                   r.created_at as created_at, r.entries as entries, id(r) as id
            ORDER BY r.created_at DESC
            """
            result = await self.db.query(cypher_query, {"query": query})
            return result or []
        except Exception as e:
            logger.error(f"Failed to search recipes: {e}")
            raise UIError(f"Failed to search recipes: {str(e)}")

