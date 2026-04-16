"""Repository for Recipe entity - Neo4j data access layer."""

from __future__ import annotations

import json
import logging
from typing import Optional

from streamlit_ui.errors import UIError, DuplicateRecipeError
from streamlit_ui.neo4j_async import AsyncNeo4jClient

logger = logging.getLogger(__name__)


class RecipeRepository:
    """Data access layer for Recipe entity."""

    def __init__(self, db_client: AsyncNeo4jClient):
        """Initialize repository with Neo4j client.

        Args:
            db_client: AsyncNeo4jClient for database queries.
        """
        self.db = db_client

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
            RETURN r.recipe_id as recipe_id, r.name as name, r.description as description,
                   r.scope as scope, r.tasks as tasks, r.tags as tags, r.entries as entries,
                   r.created_at as created_at
            """
            result = await self.db.query(query, {"name": name})
            if result:
                row = result[0]
                entries_val = row.get('entries')
                if isinstance(entries_val, str):
                    try:
                        row['entries'] = json.loads(entries_val)
                    except Exception:
                        logger.exception("Failed to parse entries JSON for recipe %s", name)
                entry_count = len(row.get('entries', {})) if row.get('entries') else 0
                logger.debug(f"Recipe found: {name} (entry_count={entry_count})")
                if 'recipe_id' not in row and row.get('name'):
                    row['recipe_id'] = row.get('name')
                return row
            logger.debug(f"Recipe not found: {name}")
            return None
        except Exception as e:
            logger.error(f"Failed to get recipe by name: {e}")
            raise UIError(f"Failed to retrieve recipe: {str(e)}")

    async def get_by_recipe_id(self, recipe_id: str) -> Optional[dict]:
        """Retrieve recipe by recipe_id."""
        logger.debug(f"Querying recipe by recipe_id: {recipe_id}")
        try:
            query = """
            MATCH (r:Recipe {recipe_id: $recipe_id})
            RETURN r.recipe_id as recipe_id, r.name as name, r.description as description,
                   r.scope as scope, r.tasks as tasks, r.tags as tags, r.entries as entries,
                   r.created_at as created_at
            """
            result = await self.db.query(query, {"recipe_id": recipe_id})
            if result:
                row = result[0]
                entries_val = row.get('entries')
                if isinstance(entries_val, str):
                    try:
                        row['entries'] = json.loads(entries_val)
                    except Exception:
                        logger.exception("Failed to parse entries JSON for recipe_id %s", recipe_id)
                return row
            return None
        except Exception as e:
            logger.error(f"Failed to get recipe by recipe_id: {e}")
            raise UIError(f"Failed to retrieve recipe: {str(e)}")

    async def create(
        self,
        recipe_id: str,
        name: str,
        entries: dict,
        description: str = "",
        scope: str = "",
        tasks: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """Create a new recipe.

        Args:
            recipe_id: Unique recipe ID.
            name: Unique recipe name.
            entries: Dictionary mapping paths to RecipeEntry data.
            description: Optional recipe description.
            scope: Optional scope (e.g., 'sft', 'preference', 'rl').
            tasks: Optional list of tasks.
            tags: Optional list of tags.

        Returns:
            Created recipe data.

        Raises:
            DuplicateRecipeError: If name already exists.
            UIError: If database query fails.
        """
        # Check uniqueness by recipe_id first
        logger.debug("Checking recipe uniqueness: recipe_id=%s name=%s", recipe_id, name)
        existing_by_id = await self.get_by_recipe_id(recipe_id)
        if existing_by_id:
            logger.warning("Recipe recipe_id already exists: %s", recipe_id)
            raise DuplicateRecipeError(recipe_id, recovery_suggestions=[f"{recipe_id}_dup"])

        # If name provided, ensure name is unique
        if name:
            existing_by_name = await self.get_by_name(name)
            if existing_by_name and existing_by_name.get('recipe_id') != recipe_id:
                logger.warning("Recipe name already exists: %s", name)
                suggestions = [f"{name}_v1", f"{name}_v2", f"{name}_backup"]
                raise DuplicateRecipeError(name, recovery_suggestions=suggestions)

        try:
            entry_count = len(entries)
            logger.info(f"Inserting recipe: name={name}, entry_count={entry_count}")
            query = """
            CREATE (r:Recipe {
                recipe_id: $recipe_id,
                name: $name,
                description: $description,
                scope: $scope,
                tasks: $tasks,
                tags: $tags,
                entries: $entries,
                created_at: datetime()
            })
            RETURN r.recipe_id as recipe_id, r.name as name, r.description as description,
                   r.scope as scope, r.tasks as tasks, r.tags as tags, r.entries as entries
            """
            # Serialize entries to JSON string
            try:
                entries_payload = json.dumps(entries)
            except Exception:
                logger.exception("Failed to serialize entries for recipe %s", name)
                raise UIError("Failed to serialize recipe entries for storage")

            result = await self.db.query(query, {
                "recipe_id": recipe_id,
                "name": name,
                "description": description,
                "scope": scope,
                "tasks": tasks or [],
                "tags": tags or [],
                "entries": entries_payload,
            })
            if result:
                row = result[0]
                if isinstance(row.get('entries'), str):
                    try:
                        row['entries'] = json.loads(row['entries'])
                    except Exception:
                        logger.exception("Failed to parse returned entries JSON for recipe %s", name)
                logger.info(f"Recipe inserted successfully: name={row['name']}")
                return row
            raise UIError("Failed to create recipe")
        except Exception as e:
            if isinstance(e, (UIError, DuplicateRecipeError)):
                raise
            logger.error(f"Recipe insertion failed: {name}", exc_info=True)
            raise UIError(f"Failed to create recipe: {str(e)}")

    async def update(
        self,
        recipe_id: str,
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

        Raises:
            UIError: If recipe not found or conflict occurs.
        """
        existing = await self.get_by_recipe_id(recipe_id)
        if not existing:
            raise UIError(f"Recipe not found")

        # Check new name uniqueness if changing
        if new_name and new_name != existing.get('name'):
            conflict = await self.get_by_name(new_name)
            if conflict and conflict.get('recipe_id') != recipe_id:
                raise UIError(f"Recipe '{new_name}' already exists")

        try:
            updates: dict = {}
            if new_name:
                updates["name"] = new_name
            if description is not None:
                updates["description"] = description
            if scope is not None:
                updates["scope"] = scope
            if tasks is not None:
                updates["tasks"] = tasks
            if tags is not None:
                updates["tags"] = tags

            if not updates:
                return existing

            logger.info(f"Updating recipe: recipe_id={recipe_id}, fields={list(updates.keys())}")
            set_clause = ", ".join([f"r.{k} = ${k}" for k in updates.keys()])
            query = f"""
            MATCH (r:Recipe {{recipe_id: $recipe_id}})
            SET {set_clause}
            RETURN r.recipe_id as recipe_id, r.name as name, r.description as description,
                   r.scope as scope, r.tasks as tasks, r.tags as tags, r.entries as entries
            """
            params = {"recipe_id": recipe_id, **updates}
            result = await self.db.query(query, params)
            if result:
                row = result[0]
                if isinstance(row.get('entries'), str):
                    try:
                        row['entries'] = json.loads(row['entries'])
                    except Exception:
                        logger.exception("Failed to parse entries JSON on update")
                logger.info(f"Recipe updated: {row.get('recipe_id')}")
                return row
            raise UIError("Failed to update recipe")
        except Exception as e:
            if isinstance(e, UIError):
                raise
            logger.error(f"Recipe update failed: {recipe_id}", exc_info=True)
            raise UIError(f"Failed to update recipe: {str(e)}")

    async def delete(self, recipe_id: str) -> None:
        """Delete recipe by recipe_id.

        Args:
            recipe_id: Recipe ID to delete.

        Raises:
            UIError: If recipe not found or query fails.
        """
        existing = await self.get_by_recipe_id(recipe_id)
        if not existing:
            raise UIError(f"Recipe '{recipe_id}' not found")

        try:
            logger.info("Deleting recipe: recipe_id=%s", recipe_id)
            query = "MATCH (r:Recipe {recipe_id: $recipe_id}) DELETE r"
            await self.db.query(query, {"recipe_id": recipe_id})
            logger.info("Recipe deleted: recipe_id=%s", recipe_id)
        except Exception as e:
            logger.error(f"Recipe deletion failed: {recipe_id}", exc_info=True)
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
            RETURN r.name as name, r.description as description, r.scope as scope,
                   r.tasks as tasks, r.tags as tags, r.created_at as created_at,
                   r.entries as entries, r.recipe_id as recipe_id
            ORDER BY r.created_at DESC
            """
            result = await self.db.query(query)
            rows = result or []
            for row in rows:
                if isinstance(row.get('entries'), str):
                    try:
                        row['entries'] = json.loads(row['entries'])
                    except Exception:
                        logger.exception("Failed to parse entries JSON in list_all")
                if 'recipe_id' not in row and row.get('name'):
                    row['recipe_id'] = row.get('name')
            logger.debug(f"Found {len(rows)} recipes")
            return rows
        except Exception as e:
            logger.error(f"Failed to list recipes: {e}")
            raise UIError(f"Failed to list recipes: {str(e)}")

    async def list_with_limit(self, limit: int = 20) -> list[dict]:
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
            RETURN r.name as name, r.description as description, r.scope as scope,
                   r.tasks as tasks, r.tags as tags, r.created_at as created_at,
                   r.entries as entries, r.recipe_id as recipe_id, id(r) as id
            ORDER BY r.created_at DESC
            LIMIT $limit
            """
            result = await self.db.query(query, {"limit": limit})
            rows = result or []
            for row in rows:
                if isinstance(row.get('entries'), str):
                    try:
                        row['entries'] = json.loads(row['entries'])
                    except Exception:
                        logger.exception("Failed to parse entries JSON in list_with_limit")
                if 'recipe_id' not in row and row.get('name'):
                    row['recipe_id'] = row.get('name')
            logger.debug(f"Found {len(rows) if rows else 0} recipes")
            return rows
        except Exception as e:
            logger.error(f"Failed to list recipes: {e}")
            raise UIError(f"Failed to list recipes: {str(e)}")

    async def search(self, query_str: str) -> list[dict]:
        """Search recipes by name.

        Args:
            query_str: Search query string.

        Returns:
            List of matching recipes.

        Raises:
            UIError: On database query failure.
        """
        try:
            logger.debug(f"Searching recipes: query={query_str}")
            cypher_query = """
            MATCH (r:Recipe)
            WHERE toLower(r.name) CONTAINS toLower($query)
            RETURN r.name as name, r.description as description, r.scope as scope,
                   r.tasks as tasks, r.tags as tags, r.created_at as created_at,
                   r.entries as entries, r.recipe_id as recipe_id, id(r) as id
            ORDER BY r.created_at DESC
            """
            result = await self.db.query(cypher_query, {"query": query_str})
            rows = result or []
            for row in rows:
                if isinstance(row.get('entries'), str):
                    try:
                        row['entries'] = json.loads(row['entries'])
                    except Exception:
                        logger.exception("Failed to parse entries JSON in search")
                if 'recipe_id' not in row and row.get('name'):
                    row['recipe_id'] = row.get('name')
            logger.debug(f"Found {len(rows) if rows else 0} recipes matching '{query_str}'")
            return rows
        except Exception as e:
            logger.error(f"Failed to search recipes: {e}")
            raise UIError(f"Failed to search recipes: {str(e)}")
