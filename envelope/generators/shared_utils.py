"""Shared utilities for generated training scripts.

These utilities are used across multiple adapter templates to provide
common functionality and reduce code duplication.
"""

import os


def resolve_hyperparams(defaults: dict) -> dict:
    """Resolve hyperparameters: YAML defaults overridden by HPARAM_* env vars.

    Each key in defaults can be overridden via an environment variable
    HPARAM_{KEY_UPPER}. Types are preserved based on the default value's type.

    Args:
        defaults: Dict mapping parameter names to default values

    Returns:
        Dict with HPARAM_* env vars merged in, preserving types
    """
    resolved = dict(defaults)
    for key in defaults:
        env_key = f"HPARAM_{key.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            default_val = defaults[key]
            if isinstance(default_val, bool):
                resolved[key] = env_val.lower() in ("true", "1", "yes")
            elif isinstance(default_val, int):
                resolved[key] = int(env_val)
            elif isinstance(default_val, float):
                resolved[key] = float(env_val)
            else:
                resolved[key] = env_val
    return resolved
