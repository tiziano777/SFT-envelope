"""PRIME (Process Implicit Rewards) technique plugin.

PRIME builds an implicit process reward model (PRM) from outcome labels
and uses it to provide denser credit assignment in RL training.
"""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("prime")
class PRIMETechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "prime"

    @property
    def stage(self) -> Stage:
        return Stage.RL

    @property
    def display_name(self) -> str:
        return "PRIME (Process Implicit Rewards)"

    @property
    def requires_reward(self) -> bool:
        return True

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "num_generations": 16,
            "max_completion_length": 512,
            "epsilon": 0.2,
            "beta": 0.04,
            "alpha_process": 0.1,
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "epsilon" in args:
            eps = args["epsilon"]
            if not (0 < eps < 1):
                errors.append(f"PRIME epsilon must be in (0, 1), got {eps}")
        if "beta" in args:
            beta = args["beta"]
            if beta < 0:
                errors.append(f"PRIME beta must be >= 0, got {beta}")
        if "alpha_process" in args:
            ap = args["alpha_process"]
            if not (0 <= ap <= 1):
                errors.append(f"PRIME alpha_process must be in [0, 1], got {ap}")
        if "num_generations" in args:
            g = args["num_generations"]
            if not isinstance(g, int) or g < 2:
                errors.append(f"PRIME num_generations must be int >= 2, got {g}")
        return errors

    def required_dataset_fields(self) -> list[str]:
        return ["prompt"]
