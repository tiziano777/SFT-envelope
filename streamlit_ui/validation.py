"""Validation module for Streamlit UI."""

from __future__ import annotations

from typing import Optional

import yaml
from pydantic import ValidationError

try:
    from envelope.config.loader import load_yaml_config, load_recipe_yaml
    from envelope.config.models import EnvelopeConfig, RecipeConfig
except ImportError:
    # Fallback for testing when envelope is not available
    EnvelopeConfig = None
    RecipeConfig = None
    load_yaml_config = None
    load_recipe_yaml = None


def _detect_config_type(data: dict) -> str:
    """Detect if YAML is recipe metadata or training config.

    Args:
        data: Parsed YAML data.

    Returns:
        "recipe" if it's distribution metadata, "envelope" if it's training config.
    """
    # Recipe has dist_id, dist_name, dist_uri in first-level entries
    # Training config has experiment, model, dataset, training at top level
    top_keys = set(data.keys())

    # Check for recipe markers (distribution metadata)
    recipe_markers = {"dist_id", "dist_name", "dist_uri", "samples", "tokens"}
    if any(key in recipe_markers for value in data.values() if isinstance(value, dict) for key in value.keys()):
        return "recipe"

    # Check for envelope/training config markers
    envelope_markers = {"experiment", "model", "dataset", "training"}
    if any(key in envelope_markers for key in top_keys):
        return "envelope"

    # Default: if all values are dicts (potential recipe entries), assume recipe
    if all(isinstance(v, dict) for v in data.values()):
        return "recipe"

    return "envelope"


def validate_recipe_yaml(yaml_str: str) -> tuple[bool, Optional[object], list[str]]:
    """Validate YAML recipe (supports both EnvelopeConfig and RecipeConfig formats).

    Args:
        yaml_str: YAML content as string.

    Returns:
        Tuple of (is_valid, config_obj, error_list).
    """
    if not EnvelopeConfig or not load_yaml_config:
        return False, None, [
            "EnvelopeConfig module not available",
            "Ensure envelope package is properly installed"
        ]

    try:
        # Parse YAML to detect format
        data = yaml.safe_load(yaml_str)
        if data is None:
            raise ValueError("Empty YAML content")
        if not isinstance(data, dict):
            raise ValueError(f"Expected YAML dict, got {type(data).__name__}")

        # Detect config type and load with appropriate validator
        config_type = _detect_config_type(data)

        if config_type == "recipe":
            if not load_recipe_yaml:
                return False, None, ["RecipeConfig loader not available"]
            config = load_recipe_yaml(yaml_str)
        else:
            config = load_yaml_config(yaml_str)

        return True, config, []
    except ValueError as e:
        return False, None, [f"Invalid YAML format: {str(e)}"]
    except ValidationError as e:
        errors = []
        for err in e.errors():
            field = ".".join(str(x) for x in err["loc"])
            msg = err["msg"]
            errors.append(f"{field}: {msg}")
        return False, None, errors
    except Exception as e:
        return False, None, [f"Validation error: {str(e)}"]
