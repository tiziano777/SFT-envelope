"""Repository for Model entity - Neo4j data access layer."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from streamlit_ui.errors import UIError
from streamlit_ui.neo4j_async import AsyncNeo4jClient

logger = logging.getLogger(__name__)


class ModelRepository:
    """Data access layer for Model entity."""

    def __init__(self, db_client: AsyncNeo4jClient):
        """Initialize repository with Neo4j client."""
        self.db = db_client

    async def create(
        self,
        model_id: str,
        model_name: str,
        version: str = "",
        uri: str = "",
        url: str = "",
        doc_url: str = "",
        description: str = "",
    ) -> dict:
        """Create a new model.

        Args:
            model_id: Unique model ID.
            model_name: Unique model name.
            version: Model version.
            uri: Model URI.
            url: Model URL.
            doc_url: Documentation URL.
            description: Model description.

        Returns:
            Created model data.
        """
        now = datetime.utcnow().isoformat()
        query = """
        CREATE (m:Model {
            id: $id,
            model_name: $model_name,
            version: $version,
            uri: $uri,
            url: $url,
            doc_url: $doc_url,
            description: $description,
            created_at: $created_at,
            updated_at: $updated_at
        })
        RETURN m.id as id, m.model_name as model_name, m.version as version,
               m.uri as uri, m.url as url, m.doc_url as doc_url,
               m.description as description, m.created_at as created_at
        """

        result = await self.db.run_single(
            query,
            id=model_id,
            model_name=model_name,
            version=version,
            uri=uri,
            url=url,
            doc_url=doc_url,
            description=description,
            created_at=now,
            updated_at=now,
        )

        if not result:
            raise UIError("Failed to create model in Neo4j")

        logger.info(f"Model created: id={model_id}, name={model_name}")
        return result

    async def get_by_id(self, model_id: str) -> Optional[dict]:
        """Get model by ID.

        Args:
            model_id: Model ID.

        Returns:
            Model data or None if not found.
        """
        query = """
        MATCH (m:Model {id: $id})
        RETURN m.id as id, m.model_name as model_name, m.version as version,
               m.uri as uri, m.url as url, m.doc_url as doc_url,
               m.description as description, m.created_at as created_at
        """

        result = await self.db.run_single(query, id=model_id)
        return result

    async def list_all(self) -> list[dict]:
        """List all models.

        Returns:
            List of model dictionaries.
        """
        query = """
        MATCH (m:Model)
        RETURN m.id as id, m.model_name as model_name, m.version as version,
               m.uri as uri, m.url as url, m.doc_url as doc_url,
               m.description as description, m.created_at as created_at
        LIMIT 100
        """

        results = await self.db.run_list(query)
        return results

    async def update(
        self,
        model_id: str,
        version: str = "",
        uri: str = "",
        url: str = "",
        doc_url: str = "",
        description: str = "",
    ) -> dict:
        """Update model fields.

        Args:
            model_id: Model ID.
            version: New version.
            uri: New URI.
            url: New URL.
            doc_url: New documentation URL.
            description: New description.

        Returns:
            Updated model data.
        """
        now = datetime.utcnow().isoformat()

        query = """
        MATCH (m:Model {id: $id})
        SET m.version = $version, m.uri = $uri, m.url = $url,
            m.doc_url = $doc_url, m.description = $description,
            m.updated_at = $updated_at
        RETURN m.id as id, m.model_name as model_name, m.version as version,
               m.uri as uri, m.url as url, m.doc_url as doc_url,
               m.description as description, m.updated_at as updated_at
        """

        result = await self.db.run_single(
            query,
            id=model_id,
            version=version,
            uri=uri,
            url=url,
            doc_url=doc_url,
            description=description,
            updated_at=now,
        )

        if not result:
            raise UIError(f"Model {model_id} not found")

        logger.info(f"Model updated: id={model_id}")
        return result

    async def delete(self, model_id: str) -> None:
        """Delete model (use with caution - no dependency check here).

        Args:
            model_id: Model ID to delete.

        Raises:
            UIError: If deletion fails.
        """
        try:
            query = "MATCH (m:Model {id: $id}) DETACH DELETE m"
            await self.db.run(query, id=model_id)
            logger.warning(f"Model deleted: id={model_id}")
        except Exception as e:
            logger.error(f"Model deletion failed: {model_id}", exc_info=True)
            raise UIError(f"Failed to delete model: {str(e)}")

    async def count_dependencies(self, model_id: str) -> int:
        """Count relationships to this model.

        Args:
            model_id: Model ID.

        Returns:
            Number of dependent relationships.
        """
        return await self.db.count_relationships(model_id, "Model")
