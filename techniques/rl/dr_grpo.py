"""Dr. GRPO (bias-corrected GRPO) technique plugin.

Dr. GRPO applies Bessel's correction to the group normalization and
a length-correction term to remove bias from the vanilla GRPO estimator.
"""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("dr_grpo")
class DrGRPOTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "dr_grpo"

    @property
    def stage(self) -> Stage:
        return Stage.RL

    @property
    def display_name(self) -> str:
        return "Dr. GRPO (Bias-Corrected)"

    @property
    def requires_reward(self) -> bool:
        return True

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "num_generations": 16,
            "max_completion_length": 512,
            "epsilon": 0.2,
            "beta": 0.04,
            "bessel_correction": True,
            "length_correction": True,
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "num_generations" in args:
            g = args["num_generations"]
            if not isinstance(g, int) or g < 2:
                errors.append(f"Dr. GRPO num_generations must be int >= 2, got {g}")
        if "epsilon" in args:
            eps = args["epsilon"]
            if not (0 < eps < 1):
                errors.append(f"Dr. GRPO epsilon must be in (0, 1), got {eps}")
        if "beta" in args:
            beta = args["beta"]
            if beta < 0:
                errors.append(f"Dr. GRPO beta must be >= 0, got {beta}")
        return errors

    def required_dataset_fields(self) -> list[str]:
        return ["prompt"]
