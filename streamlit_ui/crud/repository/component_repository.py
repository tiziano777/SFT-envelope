"""Repository for Component entity - Neo4j data access layer."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from streamlit_ui.errors import UIError
from streamlit_ui.neo4j_async import AsyncNeo4jClient

logger = logging.getLogger(__name__)


class ComponentRepository:
    """Data access layer for Component entity."""

    def __init__(self, db_client: AsyncNeo4jClient):
        """Initialize repository with Neo4j client."""
        self.db = db_client

    async def create(
        self,
        component_id: str,
        technique_code: str,
        framework_code: str,
        opt_code: str = "",
        docs_url: str = "",
        description: str = "",
    ) -> dict:
        """Create a new component.

        Args:
            component_id: Unique component ID.
            technique_code: Technique code.
            framework_code: Framework code.
            opt_code: Optimization code.
            docs_url: Documentation URL.
            description: Component description.

        Returns:
            Created component data.
        """
        component_id_val = component_id
        now = datetime.utcnow().isoformat()

        query = """
        CREATE (c:Component {
            id: $id,
            opt_code: $opt_code,
            technique_code: $technique_code,
            framework_code: $framework_code,
            docs_url: $docs_url,
            description: $description,
            created_at: $created_at,
            updated_at: $updated_at
        })
        RETURN c.id as id, c.opt_code as opt_code, c.technique_code as technique_code,
               c.framework_code as framework_code, c.docs_url as docs_url,
               c.description as description, c.created_at as created_at
        """

        result = await self.db.run_single(
            query,
            id=component_id_val,
            opt_code=opt_code,
            technique_code=technique_code,
            framework_code=framework_code,
            docs_url=docs_url,
            description=description,
            created_at=now,
            updated_at=now,
        )

        if not result:
            raise UIError("Failed to create component in Neo4j")

        logger.info(f"Component created: id={component_id_val}, technique={technique_code}")
        return result

    async def get_by_id(self, component_id: str) -> Optional[dict]:
        """Get component by ID.

        Args:
            component_id: Component ID.

        Returns:
            Component data or None if not found.
        """
        query = """
        MATCH (c:Component {id: $id})
        RETURN c.id as id, c.opt_code as opt_code, c.technique_code as technique_code,
               c.framework_code as framework_code, c.docs_url as docs_url,
               c.description as description, c.created_at as created_at
        """

        result = await self.db.run_single(query, id=component_id)
        return result

    async def list_all(self) -> list[dict]:
        """List all components.

        Returns:
            List of component dictionaries.
        """
        query = """
        MATCH (c:Component)
        RETURN c.id as id, c.opt_code as opt_code, c.technique_code as technique_code,
               c.framework_code as framework_code, c.docs_url as docs_url,
               c.description as description, c.created_at as created_at
        LIMIT 100
        """

        results = await self.db.run_list(query)
        return results

    async def update(
        self,
        component_id: str,
        docs_url: str = "",
        description: str = "",
    ) -> dict:
        """Update component fields.

        Args:
            component_id: Component ID.
            docs_url: New documentation URL.
            description: New description.

        Returns:
            Updated component data.
        """
        now = datetime.utcnow().isoformat()

        query = """
        MATCH (c:Component {id: $id})
        SET c.docs_url = $docs_url, c.description = $description, c.updated_at = $updated_at
        RETURN c.id as id, c.opt_code as opt_code, c.technique_code as technique_code,
               c.framework_code as framework_code, c.docs_url as docs_url,
               c.description as description, c.updated_at as updated_at
        """

        result = await self.db.run_single(
            query,
            id=component_id,
            docs_url=docs_url,
            description=description,
            updated_at=now,
        )

        if not result:
            raise UIError(f"Component {component_id} not found")

        logger.info(f"Component updated: id={component_id}")
        return result

    async def delete(self, component_id: str) -> None:
        """Delete component (use with caution - no dependency check here).

        Args:
            component_id: Component ID to delete.

        Raises:
            UIError: If deletion fails.
        """
        try:
            query = "MATCH (c:Component {id: $id}) DETACH DELETE c"
            await self.db.run(query, id=component_id)
            logger.warning(f"Component deleted: id={component_id}")
        except Exception as e:
            logger.error(f"Component deletion failed: {component_id}", exc_info=True)
            raise UIError(f"Failed to delete component: {str(e)}")

    async def count_dependencies(self, component_id: str) -> int:
        """Count relationships to this component.

        Args:
            component_id: Component ID.

        Returns:
            Number of dependent relationships.
        """
        return await self.db.count_relationships(component_id, "Component")
