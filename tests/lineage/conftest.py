"""Pytest fixtures for lineage integration tests with Neo4j Docker container."""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

import docker
import pytest
from neo4j.asyncio import AsyncDriver, GraphDatabase
from neo4j.exceptions import ServiceUnavailable


@pytest.fixture(scope="session")
def docker_client() -> docker.DockerClient:
    """Docker client for container management."""
    return docker.from_env()


@pytest.fixture(scope="session")
def neo4j_container(docker_client: docker.DockerClient):
    """Start Neo4j 5.22 container with APOC plugin enabled.

    Yields the container; handles cleanup on teardown.
    """
    container = docker_client.containers.run(
        "neo4j:5.22",
        environment={
            "NEO4J_PLUGINS": '["apoc"]',
            "NEO4J_apoc_trigger_enabled": "true",
            "NEO4J_AUTH": "neo4j/password",
            "NEO4J_server_memory_heap_max_size": "1G",
        },
        ports={"7687/tcp": 7687},
        detach=True,
        remove=False,
    )

    # Wait for Neo4j to be ready (max 30s)
    max_retries = 30
    for attempt in range(max_retries):
        try:
            driver = GraphDatabase.driver(
                "bolt://localhost:7687",
                auth=("neo4j", "password"),
            )
            with driver.session() as session:
                session.run("RETURN 1")
            driver.close()
            break
        except (ServiceUnavailable, Exception):
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                container.stop(timeout=5)
                container.remove()
                raise RuntimeError("Neo4j container did not start in time")

    yield container

    # Cleanup
    try:
        container.stop(timeout=5)
    except Exception:
        pass
    try:
        container.remove()
    except Exception:
        pass


@pytest.fixture
async def neo4j_driver(neo4j_container) -> AsyncDriver:
    """AsyncDriver connected to test Neo4j container."""
    driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "password"),
    )
    yield driver
    await driver.close()


@pytest.fixture
async def neo4j_session(neo4j_driver: AsyncDriver):
    """Test session with schema loaded.

    Loads schema.cypher and triggers.cypher on setup,
    cleans up test data on teardown.
    """
    async with neo4j_driver.session() as session:
        # Load schema constraints and indexes
        schema_file = Path(__file__).parent.parent.parent / "master" / "neo4j" / "schema.cypher"
        if schema_file.exists():
            schema_cypher = schema_file.read_text()
            await session.run(schema_cypher)

        # Load APOC triggers
        triggers_file = Path(__file__).parent.parent.parent / "master" / "neo4j" / "triggers.cypher"
        if triggers_file.exists():
            triggers_cypher = triggers_file.read_text()
            await session.run(triggers_cypher)

        yield session

        # Cleanup: delete all test nodes
        try:
            await session.run("MATCH (n) DETACH DELETE n;")
        except Exception:
            pass


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


def pytest_collection_modifyitems(config, items):
    """Mark all tests in this module as asyncio tests."""
    for item in items:
        if "lineage" in str(item.fspath):
            item.add_marker(pytest.mark.asyncio)
