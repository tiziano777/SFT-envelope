"""YAML configuration loader with default merging and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from envelope.config.defaults import HYPERPARAMETER_DEFAULTS
from envelope.config.models import EnvelopeConfig, RecipeConfig, RecipeEntry
from envelope.registry import discover_plugins, technique_registry


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML file and return its contents as a dictionary."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    if not path.suffix in (".yaml", ".yml"):
        raise ValueError(f"Expected .yaml or .yml file, got: {path.suffix}")
    with open(path) as f:
        data = yaml.safe_load(f)
    if data is None:
        raise ValueError(f"Empty config file: {path}")
    return data


def merge_technique_defaults(data: dict[str, Any]) -> dict[str, Any]:
    """Merge technique-specific defaults into technique_args if not already set.

    Technique defaults are loaded from the registered technique plugins via
    BaseTechnique.default_technique_args().
    """
    discover_plugins()  # Ensure plugins are registered

    technique = data.get("training", {}).get("technique")
    if technique:
        try:
            technique_cls = technique_registry.get(technique)
            technique_obj = technique_cls()  # Instantiate the class
            defaults = technique_obj.default_technique_args()
            existing_args = data.get("training", {}).get("technique_args", {})
            merged = {**defaults, **existing_args}
            if "training" not in data:
                data["training"] = {}
            data["training"]["technique_args"] = merged
        except KeyError:
            # Unknown technique, let Pydantic validation handle it
            pass
    return data


def load_config(path: str | Path) -> EnvelopeConfig:
    """Load, merge defaults, and validate a YAML configuration.

    Returns a fully validated EnvelopeConfig instance.
    """
    raw = load_yaml(path)
    raw = merge_technique_defaults(raw)

    # Inject hparam defaults into the config dict
    if "hparam_overrides" not in raw:
        raw["hparam_overrides"] = dict(HYPERPARAMETER_DEFAULTS)

    config = EnvelopeConfig.model_validate(raw)
    return config


def load_yaml_config(yaml_str: str) -> EnvelopeConfig:
    """Load and validate EnvelopeConfig from YAML string.

    Args:
        yaml_str: YAML content as string.

    Returns:
        Validated EnvelopeConfig instance.

    Raises:
        ValueError: If YAML is invalid or empty.
        ValidationError: If config doesn't match schema.
    """
    data = yaml.safe_load(yaml_str)
    if data is None:
        raise ValueError("Empty YAML content")
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML dict, got {type(data).__name__}")

    # Merge defaults and validate
    data = merge_technique_defaults(data)
    if "hparam_overrides" not in data:
        data["hparam_overrides"] = dict(HYPERPARAMETER_DEFAULTS)

    config = EnvelopeConfig.model_validate(data)
    return config


def load_recipe_yaml(yaml_str: str) -> RecipeConfig:
    """Load and validate RecipeConfig (distribution/dataset metadata) from YAML string.

    Args:
        yaml_str: YAML content as string.

    Returns:
        Validated RecipeConfig instance.

    Raises:
        ValueError: If YAML is invalid or empty.
        ValidationError: If format doesn't match schema.
    """
    data = yaml.safe_load(yaml_str)
    if data is None:
        raise ValueError("Empty YAML content")
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML dict, got {type(data).__name__}")

    # Wrap top-level entries in 'entries' key if not already present
    if "entries" not in data:
        # Assume all top-level keys are dataset paths
        data = {"entries": data}

    config = RecipeConfig.model_validate(data)
    return config


def dump_config(config: EnvelopeConfig, path: str | Path) -> None:
    """Serialize an EnvelopeConfig back to YAML."""
    data = config.model_dump(mode="json", exclude_none=True)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
