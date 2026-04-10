"""Abstract base class for framework adapters.

Each framework adapter translates an EnvelopeConfig into framework-specific
training scripts, requirements, and launch commands.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from envelope.config.models import EnvelopeConfig


class BaseFrameworkAdapter(ABC):
    """Base class for framework adapters (TRL, Unsloth, veRL, etc.)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Framework identifier (e.g., 'trl')."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name (e.g., 'HuggingFace TRL')."""

    @abstractmethod
    def template_name(self, technique: str) -> str:
        """Return the Jinja2 template filename for the given technique.

        E.g., for technique='grpo' and framework='trl', returns 'train_grpo_trl.py.j2'.
        """

    @abstractmethod
    def requirements(self, config: EnvelopeConfig) -> list[str]:
        """Return pip requirements for this framework + config combination."""

    def template_context(self, config: EnvelopeConfig) -> dict[str, Any]:
        """Return extra context variables for the Jinja2 template.

        Default implementation provides standard context. Override if special handling needed.
        """
        return {
            "config": config,
            "technique_args": config.training.technique_args,
            "hparam_defaults": config.hparam_overrides,
        }

    def launch_command(self, config: EnvelopeConfig) -> str:
        """Return the shell command to launch training. Override for custom launchers."""
        return "python train.py"

    def validate_config(self, config: EnvelopeConfig) -> list[str]:
        """Framework-specific config validation. Returns list of errors."""
        return []

    def extra_setup_files(self, config: EnvelopeConfig, output_dir: Path) -> None:
        """Copy extra files needed by this framework into the setup directory.

        Default: no-op. Override for frameworks that bundle libraries (e.g., from_scratch).
        """
