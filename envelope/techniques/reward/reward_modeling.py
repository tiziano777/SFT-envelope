"""Reward Modeling technique plugin.

Trains a scalar reward model from preference data using
AutoModelForSequenceClassification (num_labels=1).
"""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("reward_modeling")
class RewardModelingTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "reward_modeling"

    @property
    def stage(self) -> Stage:
        return Stage.PREFERENCE

    @property
    def display_name(self) -> str:
        return "Reward Model Training"

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "center_rewards_coefficient": 0.0,
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "center_rewards_coefficient" in args:
            coeff = args["center_rewards_coefficient"]
            if coeff < 0:
                errors.append(f"center_rewards_coefficient must be >= 0, got {coeff}")
        return errors

    def required_dataset_fields(self) -> list[str]:
        return ["prompt", "chosen", "rejected"]
