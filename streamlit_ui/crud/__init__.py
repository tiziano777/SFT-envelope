"""Recipe CRUD manager."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from streamlit_ui.api_client import HTTPXClient
from streamlit_ui.errors import UIError
from streamlit_ui.neo4j_async import AsyncNeo4jClient


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

    async def create_recipe(
        self, name: str, yaml_content: str, description: str = "", tags: list[str] | None = None
    ) -> dict:
        """Create a new recipe node.

        Args:
            name: Recipe name.
            yaml_content: YAML configuration as string.
            description: Optional description.
            tags: Optional list of tags.

        Returns:
            Created recipe data.
        """
        recipe_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        tags = tags or []

        query = """
        CREATE (r:Recipe {
            id: $id,
            recipe_id: $recipe_id,
            name: $name,
            description: $description,
            config_yaml: $config_yaml,
            tags: $tags,
            issued: $issued,
            modified: $modified,
            created_at: $created_at,
            updated_at: $updated_at
        })
        RETURN r
        """

        result = await self.db.run_single(
            query,
            id=recipe_id,
            recipe_id=recipe_id,
            name=name,
            description=description,
            config_yaml=yaml_content,
            tags=tags,
            issued=now,
            modified=now,
            created_at=now,
            updated_at=now,
        )

        if not result:
            raise UIError("Failed to create recipe in Neo4j")

        return {
            "id": recipe_id,
            "name": name,
            "description": description,
            "tags": tags,
            "created_at": now,
        }

    async def list_recipes(self, limit: int = 100) -> list[dict]:
        """List all recipes with optional limit.

        Args:
            limit: Max number of recipes to return.

        Returns:
            List of recipe dictionaries.
        """
        query = """
        MATCH (r:Recipe)
        RETURN r.id as id, r.name as name, r.description as description,
               r.tags as tags, r.created_at as created_at
        LIMIT $limit
        """

        results = await self.db.run_list(query, limit=limit)
        return results

    async def search_recipes(self, query_str: str) -> list[dict]:
        """Search recipes by name (case-insensitive prefix match).

        Args:
            query_str: Search query.

        Returns:
            List of matching recipe dictionaries.
        """
        query = """
        MATCH (r:Recipe)
        WHERE toLower(r.name) CONTAINS toLower($query)
        RETURN r.id as id, r.name as name, r.description as description,
               r.tags as tags, r.created_at as created_at
        LIMIT 100
        """

        results = await self.db.run_list(query, query=query_str)
        return results

    async def get_recipe(self, recipe_id: str) -> Optional[dict]:
        """Get a specific recipe by ID.

        Args:
            recipe_id: Recipe ID.

        Returns:
            Recipe dictionary or None if not found.
        """
        query = """
        MATCH (r:Recipe {id: $id})
        RETURN r.id as id, r.name as name, r.description as description,
               r.config_yaml as config_yaml, r.tags as tags,
               r.created_at as created_at, r.updated_at as updated_at
        """

        result = await self.db.run_single(query, id=recipe_id)
        return result

    async def update_recipe(
        self, recipe_id: str, description: str = "", tags: list[str] | None = None
    ) -> dict:
        """Update recipe descriptive fields (not config_yaml).

        Args:
            recipe_id: Recipe ID.
            description: New description.
            tags: New tags list.

        Returns:
            Updated recipe data.
        """
        now = datetime.utcnow().isoformat()
        tags = tags or []

        query = """
        MATCH (r:Recipe {id: $id})
        SET r.description = $description, r.tags = $tags, r.updated_at = $updated_at
        RETURN r.id as id, r.name as name, r.description as description,
               r.tags as tags, r.updated_at as updated_at
        """

        result = await self.db.run_single(
            query, id=recipe_id, description=description, tags=tags, updated_at=now
        )

        if not result:
            raise UIError(f"Recipe {recipe_id} not found")

        return result

    async def delete_recipe(self, recipe_id: str) -> None:
        """Delete a recipe (with dependency check).

        Args:
            recipe_id: Recipe ID to delete.

        Raises:
            UIError: If recipe has dependencies.
        """
        # Check for incoming relationships
        dep_count = await self.db.count_relationships(recipe_id, "Recipe")
        if dep_count > 0:
            raise UIError(
                f"Cannot delete recipe: {dep_count} experiment(s) depend on it. "
                f"Delete those first."
            )

        query = "MATCH (r:Recipe {id: $id}) DETACH DELETE r"
        await self.db.run(query, id=recipe_id)

    async def check_recipe_dependencies(self, recipe_id: str) -> int:
        """Count experiments using this recipe.

        Args:
            recipe_id: Recipe ID.

        Returns:
            Number of dependent experiments.
        """
        return await self.db.count_relationships(recipe_id, "Recipe")
