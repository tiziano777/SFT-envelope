"""Validation module for Streamlit UI."""

from __future__ import annotations

from typing import Optional

from pydantic import ValidationError

try:
    from envelope.config.loader import load_yaml_config
    from envelope.config.models import EnvelopeConfig
except ImportError:
    # Fallback for testing when envelope is not available
    EnvelopeConfig = None
    load_yaml_config = None


def validate_recipe_yaml(yaml_str: str) -> tuple[bool, Optional[object], list[str]]:
    """Validate YAML recipe against EnvelopeConfig schema.

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
