"""Test configuration for Streamlit UI."""

from __future__ import annotations

import os
import pytest
from unittest.mock import AsyncMock


@pytest.fixture
def config():
    """Fixture for Config instance."""
    from streamlit_ui.config import Config

    return Config()


@pytest.fixture
def api_token():
    """Fixture for API token."""
    return os.getenv("MASTER_API_TOKEN", "test-token")


@pytest.fixture
def mock_db_client():
    """Fixture for mocked AsyncNeo4jClient."""
    client = AsyncMock()
    client.query = AsyncMock()
    return client


@pytest.fixture
def mock_api_client():
    """Fixture for mocked HTTPXClient."""
    client = AsyncMock()
    client.post = AsyncMock()
    client.get = AsyncMock()
    return client
