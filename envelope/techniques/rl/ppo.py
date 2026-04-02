"""PPO (Proximal Policy Optimization) technique plugin."""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("ppo")
class PPOTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "ppo"

    @property
    def stage(self) -> Stage:
        return Stage.RL

    @property
    def display_name(self) -> str:
        return "Proximal Policy Optimization"

    @property
    def requires_reference_model(self) -> bool:
        return True

    @property
    def requires_reward(self) -> bool:
        return True

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "clip_range": 0.2,
            "gae_lambda": 0.95,
            "vf_coef": 0.5,
            "num_generations": 8,
            "max_completion_length": 256,
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "clip_range" in args:
            cr = args["clip_range"]
            if not (0 < cr < 1):
                errors.append(f"PPO clip_range must be in (0, 1), got {cr}")
        if "gae_lambda" in args:
            gl = args["gae_lambda"]
            if not (0 < gl <= 1):
                errors.append(f"PPO gae_lambda must be in (0, 1], got {gl}")
        if "vf_coef" in args:
            vf = args["vf_coef"]
            if vf < 0:
                errors.append(f"PPO vf_coef must be >= 0, got {vf}")
        return errors

    def required_dataset_fields(self) -> list[str]:
        return ["prompt"]
