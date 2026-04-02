"""GKD (Generalized Knowledge Distillation) technique plugin.

On-policy distillation with a separate teacher model.
Uses JSD loss interpolated between forward and reverse KL.
"""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("gkd")
class GKDTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "gkd"

    @property
    def stage(self) -> Stage:
        return Stage.SFT

    @property
    def display_name(self) -> str:
        return "Generalized Knowledge Distillation"

    @property
    def requires_teacher_model(self) -> bool:
        return True

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "temperature": 0.9,
            "lmbda": 0.5,
            "beta": 0.5,
            "max_new_tokens": 128,
            "disable_dropout": True,
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "temperature" in args and args["temperature"] <= 0:
            errors.append(f"GKD temperature must be > 0, got {args['temperature']}")
        if "lmbda" in args and not (0 <= args["lmbda"] <= 1):
            errors.append(f"GKD lmbda must be in [0, 1], got {args['lmbda']}")
        if "beta" in args and not (0 <= args["beta"] <= 1):
            errors.append(f"GKD beta (JSD interpolation) must be in [0, 1], got {args['beta']}")
        if "max_new_tokens" in args and args["max_new_tokens"] < 1:
            errors.append(f"GKD max_new_tokens must be >= 1, got {args['max_new_tokens']}")
        return errors

    def required_dataset_fields(self) -> list[str]:
        return ["prompt"]
