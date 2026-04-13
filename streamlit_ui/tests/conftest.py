"""Test configuration for Streamlit UI."""

from __future__ import annotations

import os
import pytest


@pytest.fixture
def config():
    """Fixture for Config instance."""
    from streamlit_ui.config import Config

    return Config()


@pytest.fixture
def api_token():
    """Fixture for API token."""
    return os.getenv("MASTER_API_TOKEN", "test-token")
