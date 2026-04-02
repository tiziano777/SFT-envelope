"""SDPO (Self-Distillation Policy Optimization) technique plugin.

Combines online RL with self-distillation. Requires reward functions.
The teacher is the model itself conditioned on successful rollouts.
"""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("sdpo")
class SDPOTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "sdpo"

    @property
    def stage(self) -> Stage:
        return Stage.RL

    @property
    def display_name(self) -> str:
        return "Self-Distillation Policy Optimization"

    @property
    def requires_reward(self) -> bool:
        return True

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "distillation_topk": 100,
            "full_logit_distillation": True,
            "max_completion_length": 512,
            "num_generations": 16,
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "distillation_topk" in args and args["distillation_topk"] < 1:
            errors.append(f"SDPO distillation_topk must be >= 1, got {args['distillation_topk']}")
        if "max_completion_length" in args and args["max_completion_length"] < 1:
            errors.append(f"SDPO max_completion_length must be >= 1, got {args['max_completion_length']}")
        if "num_generations" in args and args["num_generations"] < 2:
            errors.append(f"SDPO num_generations must be >= 2, got {args['num_generations']}")
        return errors

    def required_dataset_fields(self) -> list[str]:
        return ["prompt"]
