"""SimPO (Simple Preference Optimization) technique plugin."""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("simpo")
class SimPOTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "simpo"

    @property
    def stage(self) -> Stage:
        return Stage.PREFERENCE

    @property
    def display_name(self) -> str:
        return "Simple Preference Optimization"

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "beta": 2.0,
            "gamma": 1.0,
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "beta" in args:
            beta = args["beta"]
            if beta <= 0:
                errors.append(f"SimPO beta must be > 0, got {beta}")
        if "gamma" in args:
            gamma = args["gamma"]
            if gamma < 0:
                errors.append(f"SimPO gamma (reward margin) must be >= 0, got {gamma}")
        return errors

    def required_dataset_fields(self) -> list[str]:
        return ["prompt", "chosen", "rejected"]
