"""Root conftest.py for E2E testing — Neo4j Docker, Master process, and utilities."""

from __future__ import annotations

import os
import subprocess
import time
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from neo4j import AsyncDriver, AsyncSession, GraphDatabase
from testcontainers.neo4j import Neo4jContainer

from master.api import create_app
from tests.utils.simulate_master import find_free_port, start_master, stop_master
from tests.utils.simulate_worker import WorkerSimulator


# === Environment Setup ===


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    os.environ.setdefault("PHOENIX_ENDPOINT", "http://localhost:4317")
    os.environ.setdefault("STORAGE_BACKENDS", "")
    # Neo4j URI will be overridden by neo4j_container fixture


# === Neo4j Docker Fixture ===


@pytest.fixture(scope="session")
def neo4j_container() -> Generator[Neo4jContainer, None, None]:
    """Start Neo4j Docker container for testing.

    Yields:
        Neo4jContainer instance
    """
    container = Neo4jContainer(image="neo4j:5.10-community")
    container.start()

    # Wait for container to be ready
    max_retries = 30
    for attempt in range(max_retries):
        try:
            driver = GraphDatabase.driver(
                container.get_connection_url(),
                auth=(container.NEO4J_USER, container.NEO4J_PASSWORD),
            )
            with driver.session() as session:
                session.run("RETURN 1")
            driver.close()
            break
        except Exception:
            if attempt == max_retries - 1:
                container.stop()
                raise RuntimeError("Neo4j container failed to start")
            time.sleep(1)

    # Set environment variables for tests
    os.environ["NEO4J_URI"] = container.get_connection_url()
    os.environ["NEO4J_USER"] = container.NEO4J_USER
    os.environ["NEO4J_PASSWORD"] = container.NEO4J_PASSWORD

    yield container
    container.stop()


@pytest.fixture
def neo4j_session(neo4j_container):
    """Provide a Neo4j session for tests with cleanup.

    Args:
        neo4j_container: Session-scoped Neo4j container

    Yields:
        Neo4j Session object
    """
    driver = GraphDatabase.driver(
        neo4j_container.get_connection_url(),
        auth=(neo4j_container.NEO4J_USER, neo4j_container.NEO4J_PASSWORD),
    )
    session = driver.session()

    yield session

    # Cleanup: Remove all _TEST nodes
    try:
        session.run("MATCH (n:_TEST) DETACH DELETE n")
    except Exception:
        pass
    finally:
        session.close()
        driver.close()


# === FastAPI Test Client Fixtures ===


@pytest.fixture
def app():
    """Create test FastAPI app."""
    return create_app()


@pytest.fixture
def app_client(app, neo4j_container):
    """FastAPI test client with Neo4j configured.

    Args:
        app: FastAPI application
        neo4j_container: Session-scoped Neo4j container

    Returns:
        TestClient instance
    """
    return TestClient(app)


# === Master Process Fixture ===


@pytest.fixture
def master_process() -> Generator[tuple[subprocess.Popen, int], None, None]:
    """Start Master API subprocess for E2E testing.

    Yields:
        Tuple of (subprocess.Popen, port)
    """
    port = find_free_port()
    proc, assigned_port = start_master(port=port, timeout=10)

    yield proc, assigned_port

    # Cleanup
    stop_master(proc, timeout=5)


# === Worker Simulator Fixture ===


@pytest.fixture
def worker_simulator(master_process) -> WorkerSimulator:
    """Provide a configured WorkerSimulator.

    Args:
        master_process: Tuple of (proc, port) from master_process fixture

    Returns:
        WorkerSimulator instance
    """
    _, port = master_process
    return WorkerSimulator(base_url=f"http://localhost:{port}")


# === Test Data Fixtures ===


@pytest.fixture
def valid_config() -> dict[str, str]:
    """Valid configuration for handshake tests."""
    return {
        "config_hash": "hash_config_test_abc",
        "req_hash": "hash_req_test_xyz",
        "code_hash": "hash_code_test_def",
        "scaffold_path": "/tmp/setup_test",
        "recipe_id": "recipe_test_123",
        "model_id": "model_test_llama7b",
        "config_text": "test_config_content",
        "train_text": "test_train_content",
        "requirements_text": "torch==2.0\nnumpy>=1.20",
        "rewards_texts": [],
        "rewards_filenames": [],
    }


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Valid API key headers for authenticated requests."""
    return {
        "X-API-Key": "test-api-key-12345",
    }


@pytest.fixture
def invalid_auth_headers() -> dict[str, str]:
    """Invalid API key headers."""
    return {
        "X-API-Key": "invalid-key-xyz",
    }
