"""Merge technique: combine checkpoints from two experiments (no-GPU operation)."""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("merge")
class MergeTechnique(BaseTechnique):
    """Merge technique for combining model checkpoints from two experiments.

    Merge is not training, but a post-hoc lineage operation that:
    - Takes two checkpoint paths as inputs
    - Creates a merged model output
    - Runs without GPU
    - Uses daemon --one-shot mode for Master coordination
    """

    @property
    def name(self) -> str:
        return "merge"

    @property
    def stage(self) -> Stage:
        # Create or use existing Stage.MERGE enum value
        return Stage.MERGE

    @property
    def display_name(self) -> str:
        return "Model Merge"

    @property
    def requires_reference_model(self) -> bool:
        return False

    @property
    def requires_reward(self) -> bool:
        return False

    @property
    def requires_teacher_model(self) -> bool:
        return False

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "merge_method": "ties",  # ties, cat, slerp, linear
            "weights": [0.5, 0.5],  # Blend weights for each checkpoint
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "merge_method" in args:
            valid_methods = ["ties", "cat", "slerp", "linear"]
            if args["merge_method"] not in valid_methods:
                errors.append(f"merge_method must be one of {valid_methods}")
        if "weights" in args:
            if not isinstance(args["weights"], list) or len(args["weights"]) != 2:
                errors.append("weights must be a list of exactly 2 floats")
        return errors

    def required_dataset_fields(self) -> list[str]:
        # Merge doesn't need dataset fields (no training)
        return []
