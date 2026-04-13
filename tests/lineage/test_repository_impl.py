"""Tests for ExperimentRepositoryAsync CRUD operations."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from envelope.middleware.shared.config_hasher import ConfigSnapshot
from master.neo4j.client import get_driver
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


# --- T01: create_experiment (MERGE-based idempotency) ---


@pytest.mark.asyncio
async def test_create_experiment_creates_new(repo, sample_snapshot):
    """create_experiment creates new Experiment node."""
    exp = await repo.create_experiment(
        recipe_id="r-001",
        exp_id="e-001",
        model_id="m-001",
        config_hash="h1",
        code_hash="h2",
        req_hash="h3",
        config_snapshot=sample_snapshot,
    )

    assert exp.exp_id == "e-001"
    assert exp.recipe_id == "r-001"
    assert exp.model_id == "m-001"
    assert exp.config_hash == "h1"


@pytest.mark.asyncio
async def test_create_experiment_idempotent(repo, sample_snapshot):
    """create_experiment returns same node on duplicate exp_id (MERGE)."""
    exp1 = await repo.create_experiment(
        recipe_id="r-001",
        exp_id="e-002",
        model_id="m-001",
        config_hash="h1",
        code_hash="h2",
        req_hash="h3",
        config_snapshot=sample_snapshot,
    )

    exp2 = await repo.create_experiment(
        recipe_id="r-001",
        exp_id="e-002",
        model_id="m-001",
        config_hash="h1",
        code_hash="h2",
        req_hash="h3",
        config_snapshot=sample_snapshot,
    )

    assert exp1.exp_id == exp2.exp_id
    assert exp1.created_at == exp2.created_at  # Not updated on second create


# --- T02: upsert_checkpoint (Atomic Transaction) ---


@pytest.mark.asyncio
async def test_upsert_checkpoint_creates(repo, sample_snapshot):
    """upsert_checkpoint creates new checkpoint."""
    # First create experiment
    exp = await repo.create_experiment(
        recipe_id="r-001",
        exp_id="e-003",
        model_id="m-001",
        config_hash="h1",
        code_hash="h2",
        req_hash="h3",
        config_snapshot=sample_snapshot,
    )

    # Create checkpoint
    ckp = await repo.upsert_checkpoint(
        exp_id="e-003",
        ckp_id="c-001",
        epoch=0,
        run=1,
        metrics_snapshot={"loss": 0.5, "accuracy": 0.9},
        uri="file:///path/to/ckp/c-001",
    )

    assert ckp.ckp_id == "c-001"
    assert ckp.epoch == 0
    assert ckp.run == 1
    assert ckp.metrics_snapshot["loss"] == 0.5


@pytest.mark.asyncio
async def test_upsert_checkpoint_updates(repo, sample_snapshot):
    """upsert_checkpoint updates existing checkpoint metrics."""
    # Create experiment and checkpoint
    exp = await repo.create_experiment(
        recipe_id="r-001",
        exp_id="e-004",
        model_id="m-001",
        config_hash="h1",
        code_hash="h2",
        req_hash="h3",
        config_snapshot=sample_snapshot,
    )

    ckp1 = await repo.upsert_checkpoint(
        exp_id="e-004",
        ckp_id="c-002",
        epoch=0,
        run=1,
        metrics_snapshot={"loss": 0.5},
    )

    # Update same checkpoint
    ckp2 = await repo.upsert_checkpoint(
        exp_id="e-004",
        ckp_id="c-002",
        epoch=0,
        run=1,
        metrics_snapshot={"loss": 0.4, "accuracy": 0.95},
    )

    assert ckp2.ckp_id == "c-002"
    assert ckp2.metrics_snapshot["loss"] == 0.4


@pytest.mark.asyncio
async def test_upsert_checkpoint_creates_relation(repo, sample_snapshot):
    """upsert_checkpoint creates PRODUCED_BY relation to experiment."""
    exp = await repo.create_experiment(
        recipe_id="r-001",
        exp_id="e-005",
        model_id="m-001",
        config_hash="h1",
        code_hash="h2",
        req_hash="h3",
        config_snapshot=sample_snapshot,
    )

    ckp = await repo.upsert_checkpoint(
        exp_id="e-005",
        ckp_id="c-003",
        epoch=5,
        run=2,
        metrics_snapshot={"loss": 0.3},
    )

    # Verify relation exists via direct query
    driver = await get_driver()
    async with driver.session() as session:
        result = await session.run(
            """MATCH (e:Experiment {exp_id: $exp_id})-[:PRODUCED_BY]-(c:Checkpoint {ckp_id: $ckp_id})
               RETURN COUNT(*) AS count""",
            {"exp_id": "e-005", "ckp_id": "c-003"},
        )
        record = await result.single()
        assert record["count"] == 1


# --- T03: find_experiment_by_hashes (Query) ---


@pytest.mark.asyncio
async def test_find_experiment_by_hashes_found(repo, sample_snapshot):
    """find_experiment_by_hashes queries and returns existing experiment."""
    # Create experiment
    exp1 = await repo.create_experiment(
        recipe_id="r-001",
        exp_id="e-006",
        model_id="m-001",
        config_hash="h1",
        code_hash="h2",
        req_hash="h3",
        config_snapshot=sample_snapshot,
    )

    # Query by hashes
    exp2 = await repo.find_experiment_by_hashes(
        config_hash="h1",
        code_hash="h2",
        req_hash="h3",
    )

    assert exp2 is not None
    assert exp2.exp_id == "e-006"


@pytest.mark.asyncio
async def test_find_experiment_by_hashes_not_found(repo):
    """find_experiment_by_hashes returns None when no match."""
    exp = await repo.find_experiment_by_hashes(
        config_hash="nonexistent1",
        code_hash="nonexistent2",
        req_hash="nonexistent3",
    )

    assert exp is None


@pytest.mark.asyncio
async def test_find_experiment_by_hashes_all_three_required(repo, sample_snapshot):
    """find_experiment_by_hashes requires all three hashes to match."""
    # Create experiment
    exp1 = await repo.create_experiment(
        recipe_id="r-001",
        exp_id="e-007",
        model_id="m-001",
        config_hash="h1",
        code_hash="h2",
        req_hash="h3",
        config_snapshot=sample_snapshot,
    )

    # Try query with wrong req_hash
    exp2 = await repo.find_experiment_by_hashes(
        config_hash="h1",
        code_hash="h2",
        req_hash="h_wrong",
    )

    assert exp2 is None


# --- T04: get_latest_checkpoint (Order DESC) ---


@pytest.mark.asyncio
async def test_get_latest_checkpoint_highest_epoch(repo, sample_snapshot):
    """get_latest_checkpoint returns checkpoint with highest epoch."""
    # Create experiment
    exp = await repo.create_experiment(
        recipe_id="r-001",
        exp_id="e-008",
        model_id="m-001",
        config_hash="h1",
        code_hash="h2",
        req_hash="h3",
        config_snapshot=sample_snapshot,
    )

    # Create multiple checkpoints
    await repo.upsert_checkpoint(
        exp_id="e-008",
        ckp_id="c-010",
        epoch=0,
        run=1,
        metrics_snapshot={"loss": 0.8},
    )
    await repo.upsert_checkpoint(
        exp_id="e-008",
        ckp_id="c-011",
        epoch=5,
        run=1,
        metrics_snapshot={"loss": 0.5},
    )
    await repo.upsert_checkpoint(
        exp_id="e-008",
        ckp_id="c-012",
        epoch=10,
        run=1,
        metrics_snapshot={"loss": 0.2},
    )

    latest = await repo.get_latest_checkpoint(exp_id="e-008")

    assert latest is not None
    assert latest.ckp_id == "c-012"
    assert latest.epoch == 10


@pytest.mark.asyncio
async def test_get_latest_checkpoint_no_checkpoints(repo, sample_snapshot):
    """get_latest_checkpoint returns None when no checkpoints exist."""
    # Create experiment with no checkpoints
    exp = await repo.create_experiment(
        recipe_id="r-001",
        exp_id="e-009",
        model_id="m-001",
        config_hash="h1",
        code_hash="h2",
        req_hash="h3",
        config_snapshot=sample_snapshot,
    )

    latest = await repo.get_latest_checkpoint(exp_id="e-009")

    assert latest is None


@pytest.mark.asyncio
async def test_get_latest_checkpoint_ties_by_run(repo, sample_snapshot):
    """get_latest_checkpoint breaks epoch ties by highest run."""
    exp = await repo.create_experiment(
        recipe_id="r-001",
        exp_id="e-010",
        model_id="m-001",
        config_hash="h1",
        code_hash="h2",
        req_hash="h3",
        config_snapshot=sample_snapshot,
    )

    # Create checkpoints with same epoch, different runs
    await repo.upsert_checkpoint(
        exp_id="e-010",
        ckp_id="c-020",
        epoch=5,
        run=1,
        metrics_snapshot={"loss": 0.5},
    )
    await repo.upsert_checkpoint(
        exp_id="e-010",
        ckp_id="c-021",
        epoch=5,
        run=3,
        metrics_snapshot={"loss": 0.3},
    )

    latest = await repo.get_latest_checkpoint(exp_id="e-010")

    assert latest is not None
    assert latest.ckp_id == "c-021"
    assert latest.run == 3
