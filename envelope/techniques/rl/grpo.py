"""GRPO (Group Relative Policy Optimization) technique plugin."""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("grpo")
class GRPOTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "grpo"

    @property
    def stage(self) -> Stage:
        return Stage.RL

    @property
    def display_name(self) -> str:
        return "Group Relative Policy Optimization"

    @property
    def requires_reward(self) -> bool:
        return True

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "num_generations": 16,
            "max_completion_length": 512,
            "epsilon": 0.2,
            "beta": 0.04,
            "temperature": 1.0,
            "num_iterations": 1,
            "scale_rewards": "group",
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "num_generations" in args:
            g = args["num_generations"]
            if not isinstance(g, int) or g < 2:
                errors.append(f"GRPO num_generations must be int >= 2, got {g}")
        if "epsilon" in args:
            eps = args["epsilon"]
            if not (0 < eps < 1):
                errors.append(f"GRPO epsilon must be in (0, 1), got {eps}")
        if "beta" in args:
            beta = args["beta"]
            if beta < 0:
                errors.append(f"GRPO beta (KL coeff) must be >= 0, got {beta}")
        if "temperature" in args:
            temp = args["temperature"]
            if temp <= 0:
                errors.append(f"GRPO temperature must be > 0, got {temp}")
        return errors

    def required_dataset_fields(self) -> list[str]:
        return ["prompt"]
