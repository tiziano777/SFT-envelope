"""Pytest fixtures for API integration tests."""

from __future__ import annotations

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    os.environ.setdefault("PHOENIX_ENDPOINT", "http://localhost:4317")
    os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
    os.environ.setdefault("NEO4J_USER", "neo4j")
    os.environ.setdefault("NEO4J_PASSWORD", "password")
    os.environ.setdefault("STORAGE_BACKENDS", "")


@pytest.fixture
def auth_headers():
    """Valid API key headers for authenticated requests."""
    return {
        "X-API-Key": "test-api-key-12345",
    }


@pytest.fixture
def invalid_auth_headers():
    """Invalid API key headers."""
    return {
        "X-API-Key": "invalid-key",
    }
