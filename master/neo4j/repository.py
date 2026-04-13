"""Abstract base class and concrete implementation for experiment repository operations."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Optional

from neo4j import AsyncDriver

from envelope.middleware.shared.nodes import CheckpointNode, ExperimentNode
from envelope.middleware.shared.config_hasher import ConfigSnapshot


class RepositoryError(Exception):
    """Base exception for repository operations."""

    pass


class ExperimentAlreadyExists(RepositoryError):
    """Raised when attempting to create already-existing experiment."""

    pass


class CheckpointNotFound(RepositoryError):
    """Raised when checkpoint query returns no results."""

    pass


class BaseExperimentRepository(ABC):
    """Abstract repository for experiment lineage operations.

    Defines async interface for all Neo4j operations on Experiment and Checkpoint nodes.
    Implementations must ensure atomic transactions and idempotency.
    """

    @abstractmethod
    async def create_experiment(
        self,
        recipe_id: str,
        exp_id: str,
        model_id: str,
        config_hash: str,
        code_hash: str,
        req_hash: str,
        config_snapshot: ConfigSnapshot,
    ) -> ExperimentNode:
        """Create new experiment node (MERGE-based, idempotent).

        Args:
            recipe_id: Unique recipe identifier
            exp_id: Unique experiment identifier
            model_id: Model name/identifier
            config_hash: SHA256 hash of config.yaml (trigger)
            code_hash: SHA256 hash of train.py (trigger)
            req_hash: SHA256 hash of requirements.txt (trigger)
            config_snapshot: Full ConfigSnapshot with file hashes

        Returns:
            Created or existing ExperimentNode

        Raises:
            RepositoryError: If transaction fails
        """
        pass

    @abstractmethod
    async def upsert_checkpoint(
        self,
        exp_id: str,
        ckp_id: str,
        epoch: int,
        run: int,
        metrics_snapshot: dict,
        uri: Optional[str] = None,
    ) -> CheckpointNode:
        """Create or update checkpoint node (atomic transaction).

        Args:
            exp_id: Parent experiment ID
            ckp_id: Unique checkpoint identifier
            epoch: Training epoch number
            run: Training run number
            metrics_snapshot: Dictionary of metrics (loss, accuracy, etc.)
            uri: Optional URI to checkpoint artifact (file://, s3://, etc.)

        Returns:
            Created or updated CheckpointNode

        Raises:
            RepositoryError: If transaction fails
        """
        pass

    @abstractmethod
    async def find_experiment_by_hashes(
        self,
        config_hash: str,
        code_hash: str,
        req_hash: str,
    ) -> Optional[ExperimentNode]:
        """Find experiment matching all three trigger hashes.

        Used by handshake logic to detect RESUME vs NEW vs BRANCH strategies.

        Args:
            config_hash: SHA256 hash of config.yaml
            code_hash: SHA256 hash of train.py
            req_hash: SHA256 hash of requirements.txt

        Returns:
            ExperimentNode if found, None if no match

        Raises:
            RepositoryError: If query fails
        """
        pass

    @abstractmethod
    async def get_latest_checkpoint(self, exp_id: str) -> Optional[CheckpointNode]:
        """Get most recent checkpoint for experiment (ordered by epoch DESC).

        Used by RESUME logic to find baseline checkpoint.

        Args:
            exp_id: Experiment identifier

        Returns:
            CheckpointNode with highest epoch, or None if no checkpoints

        Raises:
            RepositoryError: If query fails
        """
        pass

    @abstractmethod
    async def create_merged_checkpoint(
        self,
        exp_id: str,
        merged_ckp_id: str,
        source_ckp_ids: list[str],
        epoch: int,
    ) -> CheckpointNode:
        """Create checkpoint with N MERGED_FROM relations (for merge technique).

        Args:
            exp_id: Target experiment ID
            merged_ckp_id: Unique ID for merged checkpoint
            source_ckp_ids: List of checkpoint IDs to merge from
            epoch: Target epoch

        Returns:
            Created merged CheckpointNode

        Raises:
            RepositoryError: If transaction fails
        """
        pass

    @abstractmethod
    async def create_derived_from_relation(
        self,
        source_exp_id: str,
        target_exp_id: str,
        diff_patch: dict,
    ) -> None:
        """Create DERIVED_FROM relation with diff metadata.

        Args:
            source_exp_id: Source (parent) experiment ID
            target_exp_id: Target (child) experiment ID
            diff_patch: Git-style diff dictionary with keys: config, train, requirements, hyperparams, rewards

        Raises:
            RepositoryError: If transaction fails
        """
        pass

    @abstractmethod
    async def create_retry_from_relation(
        self,
        source_exp_id: str,
        target_exp_id: str,
    ) -> None:
        """Create RETRY_FROM relation (same config, different random seed/hardware).

        Args:
            source_exp_id: Source experiment ID
            target_exp_id: Target (retry) experiment ID

        Raises:
            RepositoryError: If transaction fails
        """
        pass

    @abstractmethod
    async def get_experiment(self, exp_id: str) -> Optional[ExperimentNode]:
        """Get experiment by ID.

        Args:
            exp_id: Experiment identifier

        Returns:
            ExperimentNode if found, None otherwise

        Raises:
            RepositoryError: If query fails
        """
        pass


# --- Concrete Implementation ---


class ExperimentRepositoryAsync(BaseExperimentRepository):
    """Async Neo4j implementation of experiment repository.

    All operations use MERGE for idempotency and atomic transactions
    for consistency across multiple operations.
    """

    def __init__(self, driver: AsyncDriver):
        """Initialize with Neo4j async driver."""
        self.driver = driver

    async def create_experiment(
        self,
        recipe_id: str,
        exp_id: str,
        model_id: str,
        config_hash: str,
        code_hash: str,
        req_hash: str,
        config_snapshot: ConfigSnapshot,
    ) -> ExperimentNode:
        """Create or MERGE existing experiment (idempotent via MERGE)."""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MERGE (e:Experiment {exp_id: $exp_id})
                SET e.recipe_id = $recipe_id,
                    e.model_id = $model_id,
                    e.config_hash = $config_hash,
                    e.code_hash = $code_hash,
                    e.req_hash = $req_hash
                RETURN e
                """,
                {
                    "exp_id": exp_id,
                    "recipe_id": recipe_id,
                    "model_id": model_id,
                    "config_hash": config_hash,
                    "code_hash": code_hash,
                    "req_hash": req_hash,
                },
            )
            record = await result.single()
            if record is None:
                raise RepositoryError(f"Failed to create experiment {exp_id}")
            return ExperimentNode.from_neo4j(record["e"])

    async def upsert_checkpoint(
        self,
        exp_id: str,
        ckp_id: str,
        epoch: int,
        run: int,
        metrics_snapshot: dict,
        uri: Optional[str] = None,
    ) -> CheckpointNode:
        """Create or update checkpoint node (atomic transaction)."""
        async with self.driver.session() as session:
            # Use atomic transaction to ensure PRODUCED_BY relation
            tx = session.begin_transaction()

            try:
                # MERGE checkpoint
                ckp_result = await tx.run(
                    """
                    MERGE (c:Checkpoint {ckp_id: $ckp_id})
                    SET c.epoch = $epoch,
                        c.run = $run,
                        c.metrics_snapshot = $metrics,
                        c.uri = $uri,
                        c.is_usable = true,
                        c.is_merging = false
                    RETURN c
                    """,
                    {
                        "ckp_id": ckp_id,
                        "epoch": epoch,
                        "run": run,
                        "metrics": json.dumps(metrics_snapshot),
                        "uri": uri,
                    },
                )
                ckp_record = await ckp_result.single()
                if ckp_record is None:
                    raise RepositoryError(f"Failed to create checkpoint {ckp_id}")

                # MERGE relation: checkpoint PRODUCED_BY experiment
                rel_result = await tx.run(
                    """
                    MATCH (e:Experiment {exp_id: $exp_id}),
                          (c:Checkpoint {ckp_id: $ckp_id})
                    MERGE (c)-[:PRODUCED_BY]->(e)
                    RETURN COUNT(*) AS count
                    """,
                    {"exp_id": exp_id, "ckp_id": ckp_id},
                )
                rel_record = await rel_result.single()
                if rel_record is None or rel_record["count"] == 0:
                    raise RepositoryError(
                        f"Failed to create PRODUCED_BY relation for {ckp_id}"
                    )

                await tx.commit()
                return CheckpointNode.from_neo4j(ckp_record["c"])

            except Exception as e:
                await tx.rollback()
                raise RepositoryError(f"upsert_checkpoint failed: {str(e)}")

    async def find_experiment_by_hashes(
        self,
        config_hash: str,
        code_hash: str,
        req_hash: str,
    ) -> Optional[ExperimentNode]:
        """Find experiment matching all three trigger hashes."""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Experiment)
                WHERE e.config_hash = $config_hash
                  AND e.code_hash = $code_hash
                  AND e.req_hash = $req_hash
                RETURN e
                LIMIT 1
                """,
                {
                    "config_hash": config_hash,
                    "code_hash": code_hash,
                    "req_hash": req_hash,
                },
            )
            record = await result.single()
            if record is None:
                return None
            return ExperimentNode.from_neo4j(record["e"])

    async def get_latest_checkpoint(self, exp_id: str) -> Optional[CheckpointNode]:
        """Get most recent checkpoint (highest epoch, then highest run)."""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Experiment {exp_id: $exp_id})<-[:PRODUCED_BY]-(c:Checkpoint)
                RETURN c
                ORDER BY c.epoch DESC, c.run DESC
                LIMIT 1
                """,
                {"exp_id": exp_id},
            )
            record = await result.single()
            if record is None:
                return None
            return CheckpointNode.from_neo4j(record["c"])

    async def create_merged_checkpoint(
        self,
        exp_id: str,
        merged_ckp_id: str,
        source_ckp_ids: list[str],
        epoch: int,
    ) -> CheckpointNode:
        """Create checkpoint with N MERGED_FROM relations."""
        async with self.driver.session() as session:
            tx = session.begin_transaction()

            try:
                # Create merged checkpoint with is_merging=true
                ckp_result = await tx.run(
                    """
                    CREATE (c:Checkpoint {
                        ckp_id: $ckp_id,
                        epoch: $epoch,
                        run: 0,
                        is_merging: true,
                        is_usable: true
                    })
                    RETURN c
                    """,
                    {"ckp_id": merged_ckp_id, "epoch": epoch},
                )
                ckp_record = await ckp_result.single()
                if ckp_record is None:
                    raise RepositoryError(f"Failed to create merged checkpoint {merged_ckp_id}")

                # Create relations to parent experiment
                await tx.run(
                    "MATCH (e:Experiment {exp_id: $exp_id}), (c:Checkpoint {ckp_id: $ckp_id}) MERGE (c)-[:PRODUCED_BY]->(e)",
                    {"exp_id": exp_id, "ckp_id": merged_ckp_id},
                )

                # Create MERGED_FROM relations to source checkpoints
                for source_ckp_id in source_ckp_ids:
                    await tx.run(
                        "MATCH (merged:Checkpoint {ckp_id: $merged_id}), (source:Checkpoint {ckp_id: $source_id}) MERGE (merged)-[:MERGED_FROM]->(source)",
                        {"merged_id": merged_ckp_id, "source_id": source_ckp_id},
                    )

                await tx.commit()
                return CheckpointNode.from_neo4j(ckp_record["c"])

            except Exception as e:
                await tx.rollback()
                raise RepositoryError(f"create_merged_checkpoint failed: {str(e)}")

    async def create_derived_from_relation(
        self,
        source_exp_id: str,
        target_exp_id: str,
        diff_patch: dict,
    ) -> None:
        """Create DERIVED_FROM relation with diff_patch metadata."""
        async with self.driver.session() as session:
            await session.run(
                """
                MATCH (source:Experiment {exp_id: $source_id}),
                      (target:Experiment {exp_id: $target_id})
                CREATE (target)-[:DERIVED_FROM {diff_patch: $diff}]->(source)
                """,
                {
                    "source_id": source_exp_id,
                    "target_id": target_exp_id,
                    "diff": json.dumps(diff_patch),
                },
            )

    async def create_retry_from_relation(
        self,
        source_exp_id: str,
        target_exp_id: str,
    ) -> None:
        """Create RETRY_FROM relation between experiments."""
        async with self.driver.session() as session:
            await session.run(
                """
                MATCH (source:Experiment {exp_id: $source_id}),
                      (target:Experiment {exp_id: $target_id})
                CREATE (target)-[:RETRY_FROM]->(source)
                """,
                {"source_id": source_exp_id, "target_id": target_exp_id},
            )

    async def get_experiment(self, exp_id: str) -> Optional[ExperimentNode]:
        """Get experiment by ID."""
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (e:Experiment {exp_id: $exp_id}) RETURN e",
                {"exp_id": exp_id},
            )
            record = await result.single()
            if record is None:
                return None
            return ExperimentNode.from_neo4j(record["e"])
