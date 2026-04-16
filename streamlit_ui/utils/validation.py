"""Validation module for Streamlit UI."""

from __future__ import annotations

from typing import Optional

import yaml
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)

# Envelope imports - only for training config validation (not for CRUD recipes)
try:
    from envelope.config.loader import load_yaml_config
    from envelope.config.models import EnvelopeConfig
except ImportError:
    EnvelopeConfig = None
    load_yaml_config = None

# Recipe validation is now in recipe_validation.py (no envelope deps)
from streamlit_ui.utils.recipe_validation import validate_recipe_yaml as validate_recipe_yaml_local


def validate_recipe_yaml(yaml_str: str, filename: str | None = None) -> tuple[bool, Optional[object], list[str]]:
    """Validate YAML recipe (delegates to recipe_validation.py).

    Args:
        yaml_str: YAML content as string.
        filename: Optional filename (unused, kept for backward compat).

    Returns:
        Tuple of (is_valid, config_obj, error_list).
    """
    return validate_recipe_yaml_local(yaml_str)
