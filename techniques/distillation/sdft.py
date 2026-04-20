"""SDFT (Self-Distilled Fine-Tuning) technique plugin.

Self-distillation where the teacher is the model itself (base weights
or adapter-disabled version for PEFT). Supports privileged context.
"""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("sdft")
class SDFTTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "sdft"

    @property
    def stage(self) -> Stage:
        return Stage.SFT

    @property
    def display_name(self) -> str:
        return "Self-Distilled Fine-Tuning"

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "distillation_alpha": 0.5,
            "distillation_topk": 5,
            "max_completion_length": 64,
            "disable_dropout": True,
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "distillation_alpha" in args and not (0 <= args["distillation_alpha"] <= 1):
            errors.append(f"SDFT distillation_alpha must be in [0, 1], got {args['distillation_alpha']}")
        if "distillation_topk" in args and args["distillation_topk"] < 1:
            errors.append(f"SDFT distillation_topk must be >= 1, got {args['distillation_topk']}")
        if "max_completion_length" in args and args["max_completion_length"] < 1:
            errors.append(f"SDFT max_completion_length must be >= 1, got {args['max_completion_length']}")
        return errors

    def required_dataset_fields(self) -> list[str]:
        return ["prompt"]
