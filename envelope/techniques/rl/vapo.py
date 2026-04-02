"""VAPO (Value-Augmented Policy Optimization) technique plugin.

VAPO mixes GRPO group advantage with a learned value critic,
combining GRPO's simplicity with PPO-style value guidance.
"""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("vapo")
class VAPOTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "vapo"

    @property
    def stage(self) -> Stage:
        return Stage.RL

    @property
    def display_name(self) -> str:
        return "Value-Augmented Policy Optimization"

    @property
    def requires_reward(self) -> bool:
        return True

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "num_generations": 16,
            "max_completion_length": 512,
            "epsilon": 0.2,
            "beta": 0.04,
            "critic_lambda": 0.5,
            "critic_hidden_size": 256,
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "epsilon" in args:
            eps = args["epsilon"]
            if not (0 < eps < 1):
                errors.append(f"VAPO epsilon must be in (0, 1), got {eps}")
        if "critic_lambda" in args:
            cl = args["critic_lambda"]
            if not (0 <= cl <= 1):
                errors.append(f"VAPO critic_lambda must be in [0, 1], got {cl}")
        if "critic_hidden_size" in args:
            chs = args["critic_hidden_size"]
            if not isinstance(chs, int) or chs < 1:
                errors.append(f"VAPO critic_hidden_size must be int >= 1, got {chs}")
        if "num_generations" in args:
            g = args["num_generations"]
            if not isinstance(g, int) or g < 2:
                errors.append(f"VAPO num_generations must be int >= 2, got {g}")
        return errors

    def required_dataset_fields(self) -> list[str]:
        return ["prompt"]
