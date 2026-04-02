"""YAML configuration loader with default merging and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from envelope.config.defaults import HYPERPARAMETER_DEFAULTS, TECHNIQUE_DEFAULTS
from envelope.config.models import EnvelopeConfig


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
    """Merge technique-specific defaults into technique_args if not already set."""
    technique = data.get("training", {}).get("technique")
    if technique and technique in TECHNIQUE_DEFAULTS:
        defaults = TECHNIQUE_DEFAULTS[technique]
        existing_args = data.get("training", {}).get("technique_args", {})
        merged = {**defaults, **existing_args}
        if "training" not in data:
            data["training"] = {}
        data["training"]["technique_args"] = merged
    return data


def inject_hparam_defaults(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure hyperparameter defaults are available in the config.

    These defaults inform the generated train.py but can be overridden
    at runtime via HPARAM_* environment variables.
    """
    if "_hparam_defaults" not in data:
        data["_hparam_defaults"] = dict(HYPERPARAMETER_DEFAULTS)
    return data


def load_config(path: str | Path) -> EnvelopeConfig:
    """Load, merge defaults, and validate a YAML configuration.

    Returns a fully validated EnvelopeConfig instance.
    """
    raw = load_yaml(path)
    raw = merge_technique_defaults(raw)
    raw = inject_hparam_defaults(raw)

    # Extract hparam defaults before passing to Pydantic (not part of the schema)
    hparam_defaults = raw.pop("_hparam_defaults", None)

    config = EnvelopeConfig.model_validate(raw)

    # Attach hparam defaults as a non-schema attribute for the generator
    config._hparam_defaults = hparam_defaults or HYPERPARAMETER_DEFAULTS  # type: ignore[attr-defined]

    return config


def dump_config(config: EnvelopeConfig, path: str | Path) -> None:
    """Serialize an EnvelopeConfig back to YAML."""
    data = config.model_dump(mode="json", exclude_none=True)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
