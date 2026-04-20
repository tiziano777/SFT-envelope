"""KTO (Kahneman-Tversky Optimization) technique plugin."""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("kto")
class KTOTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "kto"

    @property
    def stage(self) -> Stage:
        return Stage.PREFERENCE

    @property
    def display_name(self) -> str:
        return "Kahneman-Tversky Optimization"

    @property
    def requires_reference_model(self) -> bool:
        return True

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "lambda_w": 1.0,
            "lambda_l": 1.33,
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "lambda_w" in args:
            lw = args["lambda_w"]
            if lw <= 0:
                errors.append(f"KTO lambda_w must be > 0, got {lw}")
        if "lambda_l" in args:
            ll = args["lambda_l"]
            if ll <= 0:
                errors.append(f"KTO lambda_l must be > 0, got {ll}")
        return errors

    def required_dataset_fields(self) -> list[str]:
        return ["prompt", "label"]
