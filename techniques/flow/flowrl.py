"""FlowRL (Flow-based RL) technique plugin.

FlowRL replaces the on-policy RLHF objective with a distribution-matching
(flow) objective, enabling more stable training.
"""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("flowrl")
class FlowRLTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "flowrl"

    @property
    def stage(self) -> Stage:
        return Stage.RL

    @property
    def display_name(self) -> str:
        return "FlowRL (Distribution Matching)"

    @property
    def requires_reward(self) -> bool:
        return True

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "num_generations": 16,
            "max_completion_length": 512,
            "beta_flow": 1.0,
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "beta_flow" in args:
            bf = args["beta_flow"]
            if bf <= 0:
                errors.append(f"FlowRL beta_flow must be > 0, got {bf}")
        if "num_generations" in args:
            g = args["num_generations"]
            if not isinstance(g, int) or g < 2:
                errors.append(f"FlowRL num_generations must be int >= 2, got {g}")
        return errors

    def required_dataset_fields(self) -> list[str]:
        return ["prompt"]
