"""DPO (Direct Preference Optimization) technique plugin."""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("dpo")
class DPOTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "dpo"

    @property
    def stage(self) -> Stage:
        return Stage.PREFERENCE

    @property
    def display_name(self) -> str:
        return "Direct Preference Optimization"

    @property
    def requires_reference_model(self) -> bool:
        return True

    def default_technique_args(self) -> dict[str, Any]:
        return {
            "beta": 0.1,
            "dpo_variant": "standard",
        }

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "beta" in args:
            beta = args["beta"]
            if beta <= 0:
                errors.append(f"DPO beta must be > 0, got {beta}")
        if "dpo_variant" in args:
            valid = {"standard", "ipo", "cdpo", "tdpo"}
            if args["dpo_variant"] not in valid:
                errors.append(f"DPO variant must be one of {valid}, got '{args['dpo_variant']}'")
        return errors

    def required_dataset_fields(self) -> list[str]:
        return ["prompt", "chosen", "rejected"]
