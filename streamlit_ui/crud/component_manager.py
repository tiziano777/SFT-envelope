"""Component CRUD manager."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from streamlit_ui.utils.errors import DeleteProtectionError, UIError
from streamlit_ui.db.neo4j_async import AsyncNeo4jClient

logger = logging.getLogger(__name__)


class ComponentManager:
    """Manager for Component CRUD operations."""

    def __init__(self, db_client: AsyncNeo4jClient):
        """Initialize ComponentManager.

        Args:
            db_client: AsyncNeo4jClient for Neo4j queries.
        """
        self.db = db_client

    async def create_component(
        self,
        opt_code: str,
        technique_code: str,
        framework_code: str,
        docs_url: str = "",
        description: str = "",
    ) -> dict:
        """Create a new component node.

        Args:
            opt_code: Optimization code.
            technique_code: Technique code (e.g., lora_grpo).
            framework_code: Framework code (e.g., unsloth).
            docs_url: Documentation URL.
            description: Component description.

        Returns:
            Created component data.
        """
        component_id = str(uuid.uuid4())
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
            id=component_id,
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

        logger.info(f"Component created: id={component_id}, opt_code={opt_code}")
        return result

    async def list_components(self) -> list[dict]:
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

    async def get_component(self, component_id: str) -> Optional[dict]:
        """Get a specific component by ID.

        Args:
            component_id: Component ID.

        Returns:
            Component dictionary or None if not found.
        """
        query = """
        MATCH (c:Component {id: $id})
        RETURN c.id as id, c.opt_code as opt_code, c.technique_code as technique_code,
               c.framework_code as framework_code, c.docs_url as docs_url,
               c.description as description, c.created_at as created_at
        """

        result = await self.db.run_single(query, id=component_id)
        return result

    async def update_component(
        self,
        component_id: str,
        docs_url: str = "",
        description: str = "",
    ) -> dict:
        """Update component descriptive fields.

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

    async def delete_component(self, component_id: str) -> None:
        """Delete a component (with dependency check).

        Args:
            component_id: Component ID to delete.

        Raises:
            DeleteProtectionError: If component has dependencies.
        """
        # Check for incoming relationships
        dep_count = await self.check_component_dependencies(component_id)
        if dep_count > 0:
            raise DeleteProtectionError("component", dep_count, "experiment/recipe")

        query = "MATCH (c:Component {id: $id}) DETACH DELETE c"
        await self.db.run(query, id=component_id)
        logger.warning(f"Component deleted: id={component_id}")

    async def check_component_dependencies(self, component_id: str) -> int:
        """Count relationships to this component.

        Args:
            component_id: Component ID.

        Returns:
            Number of dependent relationships.
        """
        return await self.db.count_relationships(component_id, "Component")

    async def is_component_deletable(self, component_id: str) -> bool:
        """Check if component can be deleted (no related experiments).

        Args:
            component_id: Component ID to check.

        Returns:
            True if component has no related experiments, False otherwise.
        """
        from streamlit_ui.crud.repository.component_repository import ComponentRepository
        repo = ComponentRepository(self.db)
        return await repo.is_deletable(component_id)
