"""Tests for Neo4j UNIQUE constraints and indexes."""

import pytest
from neo4j.exceptions import ConstraintError


@pytest.mark.asyncio
async def test_unique_constraint_recipe_id(neo4j_session):
    """UNIQUE constraint on Recipe.recipe_id is enforced."""
    # Create first recipe
    await neo4j_session.run(
        "CREATE (:Recipe {recipe_id: $id, name: 'Recipe 1'})",
        {"id": "r-001"},
    )

    # Attempt duplicate should fail
    with pytest.raises(ConstraintError):
        await neo4j_session.run(
            "CREATE (:Recipe {recipe_id: $id, name: 'Recipe 2'})",
            {"id": "r-001"},
        )


@pytest.mark.asyncio
async def test_unique_constraint_exp_id(neo4j_session):
    """UNIQUE constraint on Experiment.exp_id is enforced."""
    await neo4j_session.run(
        "CREATE (:Experiment {exp_id: $id, config_hash: 'h1', code_hash: 'h2', req_hash: 'h3'})",
        {"id": "e-001"},
    )

    with pytest.raises(ConstraintError):
        await neo4j_session.run(
            "CREATE (:Experiment {exp_id: $id, config_hash: 'h4', code_hash: 'h5', req_hash: 'h6'})",
            {"id": "e-001"},
        )


@pytest.mark.asyncio
async def test_unique_constraint_ckp_id(neo4j_session):
    """UNIQUE constraint on Checkpoint.ckp_id is enforced."""
    await neo4j_session.run(
        "CREATE (:Checkpoint {ckp_id: $id, epoch: 0, run: 1, is_merging: false})",
        {"id": "c-001"},
    )

    with pytest.raises(ConstraintError):
        await neo4j_session.run(
            "CREATE (:Checkpoint {ckp_id: $id, epoch: 1, run: 2, is_merging: false})",
            {"id": "c-001"},
        )


@pytest.mark.asyncio
async def test_unique_constraint_model_name(neo4j_session):
    """UNIQUE constraint on Model.model_name is enforced."""
    await neo4j_session.run(
        "CREATE (:Model {model_name: $name})",
        {"name": "llama-7b"},
    )

    with pytest.raises(ConstraintError):
        await neo4j_session.run(
            "CREATE (:Model {model_name: $name})",
            {"name": "llama-7b"},
        )


@pytest.mark.asyncio
async def test_composite_unique_component(neo4j_session):
    """UNIQUE constraint on Component(technique_code, framework_code) is enforced."""
    await neo4j_session.run(
        "CREATE (:Component {technique_code: $tc, framework_code: $fc})",
        {"tc": "lora", "fc": "trl"},
    )

    with pytest.raises(ConstraintError):
        await neo4j_session.run(
            "CREATE (:Component {technique_code: $tc, framework_code: $fc})",
            {"tc": "lora", "fc": "trl"},
        )


@pytest.mark.asyncio
async def test_indexes_on_experiment_hashes(neo4j_session):
    """BTREE indexes exist on Experiment(config_hash, code_hash, req_hash)."""
    # Query APOC indexes catalog
    result = await neo4j_session.run(
        "CALL db.indexes() YIELD name WHERE name LIKE 'idx_experiment_%' RETURN COUNT(*) AS count"
    )
    record = await result.single()
    assert record["count"] >= 3, "Expected at least 3 indexes on Experiment hashes"
