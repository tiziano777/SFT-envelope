"""Recipe CRUD manager."""

from __future__ import annotations

import logging
import json
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
            RETURN r.recipe_id as recipe_id, r.name as name, r.entries as entries, r.created_at as created_at
            """
            result = await self.db.query(query, {"name": name})
            if result:
                row = result[0]
                # Neo4j doesn't accept nested maps as property values; entries may be stored as JSON string.
                entries_val = row.get('entries')
                if isinstance(entries_val, str):
                    try:
                        row['entries'] = json.loads(entries_val)
                    except Exception:
                        logger.exception("Failed to parse entries JSON for recipe %s", name)
                entry_count = len(row.get('entries', {})) if row.get('entries') else 0
                logger.debug(f"Recipe found: {name} (entry_count={entry_count})")
                # ensure recipe_id for compatibility
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
            RETURN r.recipe_id as recipe_id, r.name as name, r.entries as entries, r.description as description, r.created_at as created_at
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
        name: Optional[str],
        entries: dict,
        description: str = "",
        recipe_id: Optional[str] = None,
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
        # Determine recipe_id
        if recipe_id is None:
            import uuid

            recipe_id = str(uuid.uuid4())

        # Check uniqueness by recipe_id first
        logger.debug("Checking recipe uniqueness: recipe_id=%s name=%s", recipe_id, name)
        existing_by_id = await self.get_by_recipe_id(recipe_id)
        if existing_by_id:
            logger.warning("Recipe recipe_id already exists: %s", recipe_id)
            raise DuplicateRecipeError(recipe_id, recovery_suggestions=[f"{recipe_id}_dup"]) 

        # If name provided, ensure name is unique (and not pointing to another recipe_id)
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
                entries: $entries,
                created_at: datetime()
            })
            RETURN r.recipe_id as recipe_id, r.name as name, r.description as description, r.entries as entries
            """
            # Serialize entries to JSON string because Neo4j properties must be primitives or arrays
            try:
                entries_payload = json.dumps(entries)
            except Exception:
                logger.exception("Failed to serialize entries for recipe %s", name)
                raise UIError("Failed to serialize recipe entries for storage")

            result = await self.db.query(query, {
                "recipe_id": recipe_id,
                "name": name,
                "description": description,
                "entries": entries_payload,
            })
            if result:
                # parse entries back to dict for return
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
        name: Optional[str] = None,
        recipe_id: Optional[str] = None,
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
        # Verify current recipe exists by recipe_id if provided, otherwise by name
        existing = None
        if recipe_id:
            existing = await self.get_by_recipe_id(recipe_id)
        elif name:
            existing = await self.get_by_name(name)

        if not existing:
            raise UIError(f"Recipe not found")

        # Check new name uniqueness if changing
        if new_name and new_name != existing.get('name'):
            conflict = await self.get_by_name(new_name)
            if conflict and conflict.get('recipe_id') != existing.get('recipe_id'):
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
            if recipe_id or (existing and existing.get('recipe_id')):
                query = f"""
                MATCH (r:Recipe {{recipe_id: $old_recipe_id}})
                SET {set_clause}
                RETURN r.recipe_id as recipe_id, r.name as name, r.description as description, r.entries as entries
                """
                params = {"old_recipe_id": recipe_id or existing.get('recipe_id'), **updates}
            else:
                query = f"""
                MATCH (r:Recipe {{name: $old_name}})
                SET {set_clause}
                RETURN r.recipe_id as recipe_id, r.name as name, r.description as description, r.entries as entries
                """
                params = {"old_name": name, **updates}
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
            logger.error(f"Recipe update failed: {name}", exc_info=True)
            raise UIError(f"Failed to update recipe: {str(e)}")

    async def delete(self, name: str) -> None:
        """Delete recipe by name.

        Args:
            name: Recipe name to delete.

        Raises:
            UIError: If recipe not found or query fails.
        """
        # Backwards-compatible: allow deletion by name or recipe_id
        async def _exists_by_name(n: str):
            return await self.get_by_name(n)

        # Accept either name or recipe_id in the `name` param
        identifier = name
        existing = await _exists_by_name(name)
        if existing and existing.get('recipe_id'):
            recipe_id = existing.get('recipe_id')
        else:
            recipe_id = name

        # Verify exists by recipe_id
        existing_by_id = await self.get_by_recipe_id(recipe_id)
        if not existing_by_id:
            raise UIError(f"Recipe '{name}' not found")

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
            RETURN r.name as name, r.description as description,
                   r.created_at as created_at, r.entries as entries
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
                # ensure recipe_id present
                if 'recipe_id' not in row and row.get('name'):
                    row['recipe_id'] = row.get('name')
            logger.debug(f"Found {len(rows)} recipes")
            return rows
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
            rows = result or []
            for row in rows:
                if isinstance(row.get('entries'), str):
                    try:
                        row['entries'] = json.loads(row['entries'])
                    except Exception:
                        logger.exception("Failed to parse entries JSON in list_recipes")
                if 'recipe_id' not in row and row.get('name'):
                    row['recipe_id'] = row.get('name')
            logger.debug(f"Found {len(rows) if rows else 0} recipes")
            return rows
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
            rows = result or []
            # ensure recipe_id for backward compatibility
            for row in rows:
                if isinstance(row.get('entries'), str):
                    try:
                        row['entries'] = json.loads(row['entries'])
                    except Exception:
                        logger.exception("Failed to parse entries JSON in search_recipes")
                if 'recipe_id' not in row and row.get('name'):
                    row['recipe_id'] = row.get('name')
                if 'recipe_id' not in row and row.get('name'):
                    row['recipe_id'] = row.get('name')
            logger.debug(f"Found {len(rows) if rows else 0} recipes matching '{query}'")
            return rows
        except Exception as e:
            logger.error(f"Failed to search recipes: {e}")
            raise UIError(f"Failed to search recipes: {str(e)}")
