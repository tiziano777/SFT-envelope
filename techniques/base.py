"""Abstract base class for all training techniques.

Each technique plugin must implement this interface and register itself
via @technique_registry.register("name").
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from envelope.config.models import EnvelopeConfig, Stage


class BaseTechnique(ABC):
    """Base class for training technique plugins (GRPO, DPO, SFT, etc.)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this technique (e.g., 'grpo')."""

    @property
    @abstractmethod
    def stage(self) -> Stage:
        """Which training stage this technique belongs to."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name (e.g., 'Group Relative Policy Optimization')."""

    @abstractmethod
    def default_technique_args(self) -> dict[str, Any]:
        """Return default technique-specific arguments."""

    @abstractmethod
    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        """Validate technique-specific arguments. Returns list of errors."""

    @abstractmethod
    def required_dataset_fields(self) -> list[str]:
        """Dataset fields required by this technique (e.g., ['prompt', 'chosen', 'rejected'] for DPO)."""

    @property
    def requires_reference_model(self) -> bool:
        """Whether this technique needs a reference model."""
        return False

    @property
    def requires_reward(self) -> bool:
        """Whether this technique needs reward configuration."""
        return False

    @property
    def requires_teacher_model(self) -> bool:
        """Whether this technique needs a teacher model configuration."""
        return False

    def validate_config(self, config: EnvelopeConfig) -> list[str]:
        """Validate the full config from this technique's perspective. Override for custom checks."""
        return self.validate_technique_args(config.training.technique_args)
