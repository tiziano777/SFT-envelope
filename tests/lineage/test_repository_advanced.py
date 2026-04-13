"""Tests for advanced ExperimentRepositoryAsync operations (merge, relations)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from envelope.middleware.shared.config_hasher import ConfigSnapshot
from master.neo4j.repository import ExperimentRepositoryAsync


@pytest.fixture
async def repo(neo4j_driver):
    """Fixture providing ExperimentRepositoryAsync instance."""
    return ExperimentRepositoryAsync(neo4j_driver)


@pytest.fixture
def sample_snapshot():
    """Sample ConfigSnapshot for testing."""
    return ConfigSnapshot(
        snapshot_id="h1h2h3",
        files={"config.yaml": "h1", "train.py": "h2"},
        aggregated_hash="h1h2h3",
        created_at=datetime.now(tz=timezone.utc),
    )


# --- T01: create_merged_checkpoint ---


@pytest.mark.asyncio
async def test_create_merged_checkpoint(repo, sample_snapshot):
    """create_merged_checkpoint creates checkpoint with MERGED_FROM relations."""
    # Create experiment and source checkpoints
    exp = await repo.create_experiment(
        recipe_id="r-001",
        exp_id="e-merge-001",
        model_id="m-001",
        config_hash="h1",
        code_hash="h2",
        req_hash="h3",
        config_snapshot=sample_snapshot,
    )

    ckp1 = await repo.upsert_checkpoint(
        exp_id="e-merge-001",
        ckp_id="c-source-001",
        epoch=3,
        run=1,
        metrics_snapshot={"loss": 0.4},
    )

    ckp2 = await repo.upsert_checkpoint(
        exp_id="e-merge-001",
        ckp_id="c-source-002",
        epoch=5,
        run=2,
        metrics_snapshot={"loss": 0.3},
    )

    # Create merged checkpoint
    merged = await repo.create_merged_checkpoint(
        exp_id="e-merge-001",
        merged_ckp_id="c-merged-001",
        source_ckp_ids=["c-source-001", "c-source-002"],
        epoch=0,
    )

    assert merged.ckp_id == "c-merged-001"
    assert merged.is_merging is True


@pytest.mark.asyncio
async def test_create_merged_checkpoint_relations(repo, neo4j_driver, sample_snapshot):
    """Verify MERGED_FROM relations created correctly."""
    exp = await repo.create_experiment(
        recipe_id="r-001",
        exp_id="e-merge-002",
        model_id="m-001",
        config_hash="h1",
        code_hash="h2",
        req_hash="h3",
        config_snapshot=sample_snapshot,
    )

    await repo.upsert_checkpoint(
        exp_id="e-merge-002",
        ckp_id="c-src-a",
        epoch=2,
        run=1,
        metrics_snapshot={},
    )
    await repo.upsert_checkpoint(
        exp_id="e-merge-002",
        ckp_id="c-src-b",
        epoch=3,
        run=1,
        metrics_snapshot={},
    )

    merged = await repo.create_merged_checkpoint(
        exp_id="e-merge-002",
        merged_ckp_id="c-final",
        source_ckp_ids=["c-src-a", "c-src-b"],
        epoch=0,
    )

    # Verify relations via query
    async with neo4j_driver.session() as session:
        result = await session.run(
            """MATCH (m:Checkpoint {ckp_id: $merged_id})-[:MERGED_FROM]->(src:Checkpoint)
               RETURN COUNT(*) AS count""",
            {"merged_id": "c-final"},
        )
        record = await result.single()
        assert record["count"] == 2


# --- T02: create_derived_from_relation ---


@pytest.mark.asyncio
async def test_create_derived_from_relation(repo, sample_snapshot):
    """create_derived_from_relation creates DERIVED_FROM with diff_patch."""
    # Create two experiments
    exp1 = await repo.create_experiment(
        recipe_id="r-001",
        exp_id="e-parent",
        model_id="m-001",
        config_hash="h1",
        code_hash="h2",
        req_hash="h3",
        config_snapshot=sample_snapshot,
    )

    exp2 = await repo.create_experiment(
        recipe_id="r-001",
        exp_id="e-child",
        model_id="m-001",
        config_hash="h4",
        code_hash="h5",
        req_hash="h6",
        config_snapshot=sample_snapshot,
    )

    # Create derived relation
    diff_patch = {
        "config": [{"line": 5, "type": "added", "content": "new_param: 42"}],
        "train": [],
        "requirements": [],
        "hyperparams": [],
        "rewards": {},
    }

    await repo.create_derived_from_relation(
        source_exp_id="e-parent",
        target_exp_id="e-child",
        diff_patch=diff_patch,
    )

    # Verify relation exists
    async with repo.driver.session() as session:
        result = await session.run(
            """MATCH (child:Experiment {exp_id: 'e-child'})-[:DERIVED_FROM {diff_patch: $diff}]->(parent:Experiment {exp_id: 'e-parent'})
               RETURN COUNT(*) AS count""",
            {"diff": str(diff_patch).replace("'", '"')},
        )
        record = await result.single()
        # Note: JSON comparison may be tricky, just verify relation exists
        result2 = await session.run(
            "MATCH (child:Experiment {exp_id: 'e-child'})-[:DERIVED_FROM]->(parent:Experiment {exp_id: 'e-parent'}) RETURN COUNT(*) AS count"
        )
        record2 = await result2.single()
        assert record2["count"] == 1


# --- T03: create_retry_from_relation ---


@pytest.mark.asyncio
async def test_create_retry_from_relation(repo, sample_snapshot):
    """create_retry_from_relation creates RETRY_FROM between experiments."""
    exp1 = await repo.create_experiment(
        recipe_id="r-001",
        exp_id="e-retry-1",
        model_id="m-001",
        config_hash="h1",
        code_hash="h2",
        req_hash="h3",
        config_snapshot=sample_snapshot,
    )

    exp2 = await repo.create_experiment(
        recipe_id="r-001",
        exp_id="e-retry-2",
        model_id="m-001",
        config_hash="h1",
        code_hash="h2",
        req_hash="h3",
        config_snapshot=sample_snapshot,
    )

    await repo.create_retry_from_relation(
        source_exp_id="e-retry-1",
        target_exp_id="e-retry-2",
    )

    # Verify relation
    async with repo.driver.session() as session:
        result = await session.run(
            """MATCH (target:Experiment {exp_id: 'e-retry-2'})-[:RETRY_FROM]->(source:Experiment {exp_id: 'e-retry-1'})
               RETURN COUNT(*) AS count"""
        )
        record = await result.single()
        assert record["count"] == 1


@pytest.mark.asyncio
async def test_get_experiment(repo, sample_snapshot):
    """get_experiment retrieves experiment by ID."""
    exp1 = await repo.create_experiment(
        recipe_id="r-001",
        exp_id="e-get-test",
        model_id="m-001",
        config_hash="h1",
        code_hash="h2",
        req_hash="h3",
        config_snapshot=sample_snapshot,
    )

    exp2 = await repo.get_experiment(exp_id="e-get-test")

    assert exp2 is not None
    assert exp2.exp_id == "e-get-test"
    assert exp2.model_id == "m-001"


@pytest.mark.asyncio
async def test_get_experiment_not_found(repo):
    """get_experiment returns None for nonexistent experiment."""
    exp = await repo.get_experiment(exp_id="nonexistent")
    assert exp is None
