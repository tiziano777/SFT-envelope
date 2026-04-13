"""Integration tests for schema, driver, and ABC setup."""

import pytest

from master.neo4j.client import close_driver, get_driver


@pytest.mark.asyncio
async def test_schema_loads_and_validates(neo4j_session):
    """Schema loads without errors; all constraints visible."""
    result = await neo4j_session.run(
        """CALL db.constraints() YIELD name
           RETURN COUNT(*) AS constraint_count"""
    )
    record = await result.single()
    count = record["constraint_count"]
    assert (
        count >= 5
    ), f"Expected at least 5 constraints, got {count}"


@pytest.mark.asyncio
async def test_constraints_enforced(neo4j_session):
    """UNIQUE constraint actually enforced at database level."""
    from neo4j.exceptions import ConstraintError

    # Create first recipe
    await neo4j_session.run(
        "CREATE (:Recipe {recipe_id: $id, name: 'Test'})",
        {"id": "r-test-001"},
    )

    # Try to create duplicate
    with pytest.raises(ConstraintError):
        await neo4j_session.run(
            "CREATE (:Recipe {recipe_id: $id, name: 'Duplicate'})",
            {"id": "r-test-001"},
        )


@pytest.mark.asyncio
async def test_triggers_fire(neo4j_session):
    """APOC triggers automatically set created_at timestamp."""
    await neo4j_session.run(
        """CREATE (e:Experiment {
            exp_id: 'e-e2e-001',
            config_hash: 'h1',
            code_hash: 'h2',
            req_hash: 'h3'
        })"""
    )

    result = await neo4j_session.run(
        """MATCH (e:Experiment {exp_id: 'e-e2e-001'})
           RETURN e.created_at IS NOT NULL AS has_ts"""
    )
    record = await result.single()
    assert record["has_ts"] is True, "Trigger did not set created_at"
