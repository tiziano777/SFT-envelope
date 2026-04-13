"""Neo4j async driver singleton with connection pooling for lineage tracking."""

from __future__ import annotations

import os
from typing import Optional

from neo4j.asyncio import AsyncDriver, GraphDatabase


# Module-level singleton
_driver: Optional[AsyncDriver] = None


async def get_driver(reinit: bool = False) -> AsyncDriver:
    """Get or create the Neo4j driver singleton.

    Args:
        reinit: If True, close existing driver and create a new one.

    Returns:
        AsyncDriver instance for Neo4j 5.x async operations.
    """
    global _driver

    if reinit and _driver is not None:
        await close_driver()

    if _driver is None:
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        pool_size = int(os.getenv("NEO4J_POOL_SIZE", "50"))

        _driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            max_pool_size=pool_size,
        )

    return _driver


async def close_driver() -> None:
    """Close the Neo4j driver and reset singleton."""
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
