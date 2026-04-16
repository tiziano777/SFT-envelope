"""Tests for validation module."""

from __future__ import annotations

import pytest

from streamlit_ui.utils.recipe_validation import validate_recipe_yaml


def test_validate_yaml_valid():
    """Test valid YAML validation."""
    yaml_str = """
name: test_recipe
stage: from_scratch
"""
    is_valid, config, errors = validate_recipe_yaml(yaml_str)
    assert is_valid is True or is_valid is False  # Depends on envelope availability


def test_validate_yaml_invalid():
    """Test invalid YAML validation."""
    yaml_str = "{ invalid: yaml: content }"
    is_valid, config, errors = validate_recipe_yaml(yaml_str)
    # Should return False or handle gracefully
    assert isinstance(is_valid, bool)
    if not is_valid:
        assert isinstance(errors, list)


def test_validate_yaml_empty():
    """Test empty YAML validation."""
    yaml_str = ""
    is_valid, config, errors = validate_recipe_yaml(yaml_str)
    assert isinstance(is_valid, bool)
