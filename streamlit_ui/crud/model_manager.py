"""Model CRUD manager."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from streamlit_ui.utils.errors import DeleteProtectionError, UIError
from streamlit_ui.db.neo4j_async import AsyncNeo4jClient

logger = logging.getLogger(__name__)


class ModelManager:
    """Manager for Model CRUD operations."""

    def __init__(self, db_client: AsyncNeo4jClient):
        """Initialize ModelManager.

        Args:
            db_client: AsyncNeo4jClient for Neo4j queries.
        """
        self.db = db_client

    async def create_model(
        self,
        model_name: str,
        version: str = "",
        uri: str = "",
        url: str = "",
        doc_url: str = "",
        description: str = "",
    ) -> dict:
        """Create a new model node.

        Args:
            model_name: Unique model name.
            version: Model version.
            uri: Model URI.
            url: Model URL.
            doc_url: Documentation URL.
            description: Model description.

        Returns:
            Created model data.
        """
        model_id = str(uuid.uuid4())
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

    async def list_models(self) -> list[dict]:
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

    async def get_model(self, model_id: str) -> Optional[dict]:
        """Get a specific model by ID.

        Args:
            model_id: Model ID.

        Returns:
            Model dictionary or None if not found.
        """
        query = """
        MATCH (m:Model {id: $id})
        RETURN m.id as id, m.model_name as model_name, m.version as version,
               m.uri as uri, m.url as url, m.doc_url as doc_url,
               m.description as description, m.created_at as created_at
        """

        result = await self.db.run_single(query, id=model_id)
        return result

    async def update_model(
        self,
        model_id: str,
        version: str = "",
        uri: str = "",
        url: str = "",
        doc_url: str = "",
        description: str = "",
    ) -> dict:
        """Update model descriptive fields (not model_name).

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

    async def delete_model(self, model_id: str) -> None:
        """Delete a model (with dependency check).

        Args:
            model_id: Model ID to delete.

        Raises:
            DeleteProtectionError: If model has dependencies.
        """
        # Check for incoming relationships
        dep_count = await self.check_model_dependencies(model_id)
        if dep_count > 0:
            raise DeleteProtectionError("model", dep_count, "experiment/recipe")

        query = "MATCH (m:Model {id: $id}) DETACH DELETE m"
        await self.db.run(query, id=model_id)
        logger.warning(f"Model deleted: id={model_id}")

    async def check_model_dependencies(self, model_id: str) -> int:
        """Count relationships to this model.

        Args:
            model_id: Model ID.

        Returns:
            Number of dependent relationships.
        """
        return await self.db.count_relationships(model_id, "Model")

    async def is_model_deletable(self, model_id: str) -> bool:
        """Check if model can be deleted (no related experiments).

        Args:
            model_id: Model ID to check.

        Returns:
            True if model has no related experiments, False otherwise.
        """
        from streamlit_ui.crud.repository.model_repository import ModelRepository
        repo = ModelRepository(self.db)
        return await repo.is_deletable(model_id)
