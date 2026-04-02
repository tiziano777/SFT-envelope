"""RLOO (REINFORCE Leave-One-Out) technique plugin."""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("rloo")
class RLOOTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "rloo"

    @property
    def stage(self) -> Stage:
        return Stage.RL

    @property
    def display_name(self) -> str:
        return "REINFORCE Leave-One-Out"

    @property
    def requires_reward(self) -> bool:
        return True

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "num_generations": 8,
            "max_completion_length": 256,
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "num_generations" in args:
            g = args["num_generations"]
            if not isinstance(g, int) or g < 2:
                errors.append(f"RLOO num_generations must be int >= 2, got {g}")
        if "max_completion_length" in args:
            mcl = args["max_completion_length"]
            if not isinstance(mcl, int) or mcl < 1:
                errors.append(f"RLOO max_completion_length must be int >= 1, got {mcl}")
        return errors

    def required_dataset_fields(self) -> list[str]:
        return ["prompt"]
