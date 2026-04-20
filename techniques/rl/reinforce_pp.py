"""REINFORCE++ technique plugin.

REINFORCE++ extends REINFORCE with PPO-style clipping and a KL penalty
but without requiring a value network (critic-free).
"""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("reinforce_pp")
class REINFORCEPPTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "reinforce_pp"

    @property
    def stage(self) -> Stage:
        return Stage.RL

    @property
    def display_name(self) -> str:
        return "REINFORCE++"

    @property
    def requires_reward(self) -> bool:
        return True

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "clip_range": 0.2,
            "beta": 0.01,
            "max_completion_length": 256,
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "clip_range" in args:
            cr = args["clip_range"]
            if not (0 < cr < 1):
                errors.append(f"REINFORCE++ clip_range must be in (0, 1), got {cr}")
        if "beta" in args:
            beta = args["beta"]
            if beta < 0:
                errors.append(f"REINFORCE++ beta (KL coeff) must be >= 0, got {beta}")
        return errors

    def required_dataset_fields(self) -> list[str]:
        return ["prompt"]
