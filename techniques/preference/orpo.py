"""ORPO (Odds Ratio Preference Optimization) technique plugin."""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("orpo")
class ORPOTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "orpo"

    @property
    def stage(self) -> Stage:
        return Stage.PREFERENCE

    @property
    def display_name(self) -> str:
        return "Odds Ratio Preference Optimization"

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "lambda_or": 1.0,
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "lambda_or" in args:
            lam = args["lambda_or"]
            if lam <= 0:
                errors.append(f"ORPO lambda_or must be > 0, got {lam}")
        return errors

    def required_dataset_fields(self) -> list[str]:
        return ["prompt", "chosen", "rejected"]
