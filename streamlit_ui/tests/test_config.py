"""Tests for configuration module."""

from __future__ import annotations

import pytest

from streamlit_ui.config import Config


def test_config_defaults(config):
    """Test Config has default values."""
    assert config.master_api_url is not None
    assert config.neo4j_uri is not None
    assert config.neo4j_user is not None
    assert config.neo4j_password is not None


def test_config_theme(config):
    """Test Config theme is initialized."""
    assert config.streamlit_theme is not None
    assert "primaryColor" in config.streamlit_theme
    assert "backgroundColor" in config.streamlit_theme
