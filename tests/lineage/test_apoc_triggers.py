"""Tests for APOC triggers (timestamps and validation)."""

import pytest
from datetime import datetime, timezone
from neo4j.exceptions import ConstraintError


@pytest.mark.asyncio
async def test_created_at_timestamp_on_node_create(neo4j_session):
    """APOC trigger automatically sets created_at on node creation."""
    await neo4j_session.run(
        """CREATE (e:Experiment {
            exp_id: $exp_id,
            config_hash: 'h1',
            code_hash: 'h2',
            req_hash: 'h3'
        })""",
        {"exp_id": "e-001"},
    )

    result = await neo4j_session.run(
        "MATCH (e:Experiment {exp_id: $exp_id}) RETURN e.created_at IS NOT NULL AS has_timestamp",
        {"exp_id": "e-001"},
    )
    record = await result.single()
    assert record["has_timestamp"] is True, "created_at timestamp was not set by trigger"


@pytest.mark.asyncio
async def test_updated_at_on_property_change(neo4j_session):
    """APOC trigger automatically sets updated_at on property update."""
    await neo4j_session.run(
        """CREATE (e:Experiment {
            exp_id: $exp_id,
            config_hash: 'h1',
            code_hash: 'h2',
            req_hash: 'h3'
        })""",
        {"exp_id": "e-002"},
    )

    # Update a property
    await neo4j_session.run(
        "MATCH (e:Experiment {exp_id: $exp_id}) SET e.status = 'running'",
        {"exp_id": "e-002"},
    )

    result = await neo4j_session.run(
        "MATCH (e:Experiment {exp_id: $exp_id}) RETURN e.updated_at IS NOT NULL AS has_timestamp",
        {"exp_id": "e-002"},
    )
    record = await result.single()
    assert record["has_timestamp"] is True, "updated_at timestamp was not set by trigger"


@pytest.mark.asyncio
async def test_orphan_checkpoint_validation_fails(neo4j_session):
    """Creating standalone Checkpoint without parent violates validation trigger."""
    with pytest.raises(ConstraintError):
        await neo4j_session.run(
            """CREATE (:Checkpoint {
                ckp_id: $ckp_id,
                epoch: 1,
                run: 0,
                is_merging: false
            })""",
            {"ckp_id": "c-orphan"},
        )


@pytest.mark.asyncio
async def test_merged_checkpoint_allows_orphan_with_flag(neo4j_session):
    """Checkpoint with is_merging=true can be created as orphan."""
    # Should NOT raise error
    await neo4j_session.run(
        """CREATE (:Checkpoint {
            ckp_id: $ckp_id,
            epoch: 1,
            run: 0,
            is_merging: true
        })""",
        {"ckp_id": "c-merge"},
    )

    result = await neo4j_session.run(
        "MATCH (c:Checkpoint {ckp_id: $ckp_id}) RETURN c.ckp_id",
        {"ckp_id": "c-merge"},
    )
    record = await result.single()
    assert record["ckp_id"] == "c-merge"
