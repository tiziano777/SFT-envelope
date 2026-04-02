"""Unsloth framework adapter.

Unsloth provides 2-5x faster training via custom CUDA kernels,
with native support for SFT, DPO, GRPO, SimPO, ORPO.
"""

from __future__ import annotations

from typing import Any

from envelope.config.models import EnvelopeConfig, PeftMethod, Quantization
from envelope.frameworks.base import BaseFrameworkAdapter
from envelope.registry import framework_registry


@framework_registry.register("unsloth")
class UnslothAdapter(BaseFrameworkAdapter):
    @property
    def name(self) -> str:
        return "unsloth"

    @property
    def display_name(self) -> str:
        return "Unsloth"

    def template_name(self, technique: str) -> str:
        return f"train_{technique}_unsloth.py.j2"

    def requirements(self, config: EnvelopeConfig) -> list[str]:
        reqs = [
            "torch>=2.1",
            "unsloth>=2024.8",
            "transformers>=4.40",
            "trl>=0.12",
            "datasets>=2.18",
        ]
        if config.training.peft.method != PeftMethod.NONE:
            reqs.append("peft>=0.11")
        if config.training.precision.quantization in (Quantization.NF4, Quantization.INT8):
            reqs.append("bitsandbytes>=0.43")
        if "tensorboard" in config.output.report_to:
            reqs.append("tensorboard>=2.16")
        if "wandb" in config.output.report_to:
            reqs.append("wandb>=0.16")
        return reqs

    def template_context(self, config: EnvelopeConfig) -> dict[str, Any]:
        return {
            "config": config,
            "technique_args": config.training.technique_args,
            "hparam_defaults": getattr(config, "_hparam_defaults", {}),
        }

    def launch_command(self, config: EnvelopeConfig) -> str:
        return "python train.py"

    def validate_config(self, config: EnvelopeConfig) -> list[str]:
        errors = []
        technique = config.training.technique.value
        supported = {"sft", "dpo", "simpo", "orpo", "grpo"}
        if technique not in supported:
            errors.append(f"Unsloth does not support technique '{technique}'. Supported: {supported}")
        if config.hardware.gpu_count > 1:
            errors.append("Unsloth is single-GPU only. Use TRL or veRL for multi-GPU.")
        return errors
