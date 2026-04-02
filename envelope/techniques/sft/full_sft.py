"""SFT (Supervised Fine-Tuning) technique plugin."""

from __future__ import annotations

from typing import Any

from envelope.config.models import Stage
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique


@technique_registry.register("sft")
class SFTTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "sft"

    @property
    def stage(self) -> Stage:
        return Stage.SFT

    @property
    def display_name(self) -> str:
        return "Supervised Fine-Tuning"

    def default_technique_args(self) -> dict[str, Any]:
        return {}

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        return []

    def required_dataset_fields(self) -> list[str]:
        return ["prompt"]
