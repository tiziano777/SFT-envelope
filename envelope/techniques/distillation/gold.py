"""GOLD (General Online Logit Distillation) technique plugin.

Online logit distillation with a separate teacher model. Supports
cross-tokenizer distillation via ULD loss (teacher and student can
use different tokenizers).
"""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("gold")
class GOLDTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "gold"

    @property
    def stage(self) -> Stage:
        return Stage.SFT

    @property
    def display_name(self) -> str:
        return "General Online Logit Distillation"

    @property
    def requires_teacher_model(self) -> bool:
        return True

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "temperature": 0.9,
            "lmbda": 0.5,
            "beta": 0.5,
            "max_completion_length": 128,
            "use_uld_loss": False,
            "disable_dropout": True,
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "temperature" in args and args["temperature"] <= 0:
            errors.append(f"GOLD temperature must be > 0, got {args['temperature']}")
        if "lmbda" in args and not (0 <= args["lmbda"] <= 1):
            errors.append(f"GOLD lmbda must be in [0, 1], got {args['lmbda']}")
        if "beta" in args and not (0 <= args["beta"] <= 1):
            errors.append(f"GOLD beta must be in [0, 1], got {args['beta']}")
        if "max_completion_length" in args and args["max_completion_length"] < 1:
            errors.append(f"GOLD max_completion_length must be >= 1, got {args['max_completion_length']}")
        return errors

    def required_dataset_fields(self) -> list[str]:
        return ["prompt"]
