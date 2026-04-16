"""Repository for Experiment entity - Neo4j data access layer."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from streamlit_ui.errors import UIError
from streamlit_ui.neo4j_async import AsyncNeo4jClient

logger = logging.getLogger(__name__)


class ExperimentRepository:
    """Data access layer for Experiment entity."""

    def __init__(self, db_client: AsyncNeo4jClient):
        """Initialize repository with Neo4j client."""
        self.db = db_client

    async def create(
        self,
        exp_id: str,
        model_id: str,
        status: str = "PENDING",
        description: str = "",
    ) -> dict:
        """Create a new experiment.

        Args:
            exp_id: Unique experiment ID.
            model_id: Associated Model ID.
            status: Experiment status.
            description: Experiment description.

        Returns:
            Created experiment data.
        """
        now = datetime.utcnow().isoformat()

        query = """
        CREATE (e:Experiment {
            id: $id,
            exp_id: $exp_id,
            model_id: $model_id,
            status: $status,
            description: $description,
            created_at: $created_at,
            updated_at: $updated_at,
            usable: true
        })
        RETURN e.id as id, e.exp_id as exp_id, e.model_id as model_id,
               e.status as status, e.description as description,
               e.created_at as created_at
        """

        result = await self.db.run_single(
            query,
            id=exp_id,
            exp_id=exp_id,
            model_id=model_id,
            status=status,
            description=description,
            created_at=now,
            updated_at=now,
        )

        if not result:
            raise UIError("Failed to create experiment in Neo4j")

        logger.info(f"Experiment created: id={exp_id}, model_id={model_id}")
        return result

    async def get_by_id(self, exp_id: str) -> Optional[dict]:
        """Get experiment by ID.

        Args:
            exp_id: Experiment ID.

        Returns:
            Experiment data or None if not found.
        """
        query = """
        MATCH (e:Experiment {id: $id})
        RETURN e.id as id, e.exp_id as exp_id, e.model_id as model_id,
               e.status as status, e.description as description,
               e.created_at as created_at, e.updated_at as updated_at
        """

        result = await self.db.run_single(query, id=exp_id)
        return result

    async def list_all(self, status: Optional[str] = None) -> list[dict]:
        """List experiments optionally filtered by status.

        Args:
            status: Optional status filter.

        Returns:
            List of experiment dictionaries.
        """
        if status:
            query = """
            MATCH (e:Experiment {status: $status})
            RETURN e.id as id, e.exp_id as exp_id, e.model_id as model_id,
                   e.status as status, e.description as description,
                   e.created_at as created_at
            LIMIT 100
            """
            results = await self.db.run_list(query, status=status)
        else:
            query = """
            MATCH (e:Experiment)
            RETURN e.id as id, e.exp_id as exp_id, e.model_id as model_id,
                   e.status as status, e.description as description,
                   e.created_at as created_at
            LIMIT 100
            """
            results = await self.db.run_list(query)

        return results

    async def update(
        self,
        exp_id: str,
        status: Optional[str] = None,
        description: Optional[str] = None,
        exit_status: Optional[str] = None,
        exit_msg: Optional[str] = None,
    ) -> dict:
        """Update experiment fields.

        Args:
            exp_id: Experiment ID.
            status: New status.
            description: New description.
            exit_status: Exit status.
            exit_msg: Exit message.

        Returns:
            Updated experiment data.
        """
        now = datetime.utcnow().isoformat()
        params = {"id": exp_id, "updated_at": now}

        # Build parameterized query based on which fields are provided
        if status is not None and description is not None and exit_status is not None and exit_msg is not None:
            query = """
            MATCH (e:Experiment {id: $id})
            SET e.status = $status, e.description = $description,
                e.exit_status = $exit_status, e.exit_msg = $exit_msg,
                e.updated_at = $updated_at
            RETURN e.id as id, e.exp_id as exp_id, e.model_id as model_id,
                   e.status as status, e.description as description,
                   e.updated_at as updated_at
            """
            params.update({"status": status, "description": description, "exit_status": exit_status, "exit_msg": exit_msg})
        elif status is not None and description is not None:
            query = """
            MATCH (e:Experiment {id: $id})
            SET e.status = $status, e.description = $description, e.updated_at = $updated_at
            RETURN e.id as id, e.exp_id as exp_id, e.model_id as model_id,
                   e.status as status, e.description as description,
                   e.updated_at as updated_at
            """
            params.update({"status": status, "description": description})
        elif status is not None:
            query = """
            MATCH (e:Experiment {id: $id})
            SET e.status = $status, e.updated_at = $updated_at
            RETURN e.id as id, e.exp_id as exp_id, e.model_id as model_id,
                   e.status as status, e.description as description,
                   e.updated_at as updated_at
            """
            params["status"] = status
        elif description is not None:
            query = """
            MATCH (e:Experiment {id: $id})
            SET e.description = $description, e.updated_at = $updated_at
            RETURN e.id as id, e.exp_id as exp_id, e.model_id as model_id,
                   e.status as status, e.description as description,
                   e.updated_at as updated_at
            """
            params["description"] = description
        else:
            query = """
            MATCH (e:Experiment {id: $id})
            RETURN e.id as id, e.exp_id as exp_id, e.model_id as model_id,
                   e.status as status, e.description as description,
                   e.updated_at as updated_at
            """

        result = await self.db.run_single(query, **params)

        if not result:
            raise UIError(f"Experiment {exp_id} not found")

        logger.info(f"Experiment updated: id={exp_id}")
        return result

    async def delete(self, exp_id: str) -> None:
        """Delete experiment (use with caution - no dependency check here).

        Args:
            exp_id: Experiment ID to delete.

        Raises:
            UIError: If deletion fails.
        """
        try:
            query = "MATCH (e:Experiment {id: $id}) DETACH DELETE e"
            await self.db.run(query, id=exp_id)
            logger.warning(f"Experiment deleted: id={exp_id}")
        except Exception as e:
            logger.error(f"Experiment deletion failed: {exp_id}", exc_info=True)
            raise UIError(f"Failed to delete experiment: {str(e)}")

    async def count_dependencies(self, exp_id: str) -> int:
        """Count checkpoints for this experiment.

        Args:
            exp_id: Experiment ID.

        Returns:
            Number of dependent checkpoints.
        """
        query = """
        MATCH (e:Experiment {id: $id})-[r:HAS_CHECKPOINT]->(cp)
        RETURN count(r) as dep_count
        """

        result = await self.db.run_single(query, id=exp_id)
        return result["dep_count"] if result else 0
