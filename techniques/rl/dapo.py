"""DAPO (Decoupled Alignment via Policy Optimization) technique plugin.

DAPO extends GRPO with 4 key ingredients:
1. Decoupled clip (epsilon_low, epsilon_high)
2. Dynamic sampling (filter all-correct/all-wrong prompts)
3. Overlong filtering
4. Token-level policy gradient
"""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("dapo")
class DAPOTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "dapo"

    @property
    def stage(self) -> Stage:
        return Stage.RL

    @property
    def display_name(self) -> str:
        return "Decoupled Alignment via Policy Optimization"

    @property
    def requires_reward(self) -> bool:
        return True

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "num_generations": 16,
            "max_completion_length": 512,
            "epsilon_low": 0.2,
            "epsilon_high": 0.28,
            "beta": 0.0,
            "temperature": 1.0,
            "dynamic_sampling": True,
            "overlong_filtering": True,
            "token_level_pg": True,
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "epsilon_low" in args and "epsilon_high" in args:
            lo, hi = args["epsilon_low"], args["epsilon_high"]
            if lo >= hi:
                errors.append(f"DAPO epsilon_low ({lo}) must be < epsilon_high ({hi})")
        if "epsilon_low" in args:
            el = args["epsilon_low"]
            if not (0 < el < 1):
                errors.append(f"DAPO epsilon_low must be in (0, 1), got {el}")
        if "epsilon_high" in args:
            eh = args["epsilon_high"]
            if not (0 < eh < 1):
                errors.append(f"DAPO epsilon_high must be in (0, 1), got {eh}")
        if "num_generations" in args:
            g = args["num_generations"]
            if not isinstance(g, int) or g < 2:
                errors.append(f"DAPO num_generations must be int >= 2, got {g}")
        if "temperature" in args:
            t = args["temperature"]
            if t <= 0:
                errors.append(f"DAPO temperature must be > 0, got {t}")
        return errors

    def required_dataset_fields(self) -> list[str]:
        return ["prompt"]
