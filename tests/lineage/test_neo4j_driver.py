"""Tests for Neo4jDriver singleton and async connection pooling."""

import os

import pytest

from master.neo4j.client import close_driver, get_driver


@pytest.mark.asyncio
async def test_driver_singleton():
    """Calling get_driver() twice returns same instance."""
    driver1 = await get_driver()
    driver2 = await get_driver()
    assert driver1 is driver2, "get_driver() should return singleton"


@pytest.mark.asyncio
async def test_driver_pool_size_from_env():
    """Driver pool size configurable via NEO4J_POOL_SIZE environment variable."""
    os.environ["NEO4J_POOL_SIZE"] = "20"
    driver = await get_driver(reinit=True)

    # Verify pool size is 20 (internal driver attribute)
    assert driver._pool_size == 20, f"Expected pool size 20, got {driver._pool_size}"

    await close_driver()


@pytest.mark.asyncio
async def test_async_session_management():
    """Sessions acquired and released correctly via async context manager."""
    driver = await get_driver()

    async with driver.session() as session:
        result = await session.run("RETURN 1 AS value")
        record = await result.single()
        assert record["value"] == 1

    # Session should be released back to pool (no exception)


@pytest.mark.asyncio
async def test_close_driver():
    """close_driver() closes connection and resets singleton."""
    driver1 = await get_driver()
    await close_driver()

    driver2 = await get_driver()
    assert driver1 is not driver2, "After close_driver(), next get_driver() should return new instance"

    await close_driver()
