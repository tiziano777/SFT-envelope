"""Axolotl framework adapter.

Axolotl is a YAML-first fine-tuning framework with extensive
model/dataset support and multi-GPU via DeepSpeed/FSDP.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from envelope.config.models import EnvelopeConfig, PeftMethod, Quantization
from envelope.frameworks.base import BaseFrameworkAdapter
from envelope.registry import framework_registry


@framework_registry.register("axolotl")
class AxolotlAdapter(BaseFrameworkAdapter):
    @property
    def name(self) -> str:
        return "axolotl"

    @property
    def display_name(self) -> str:
        return "Axolotl"

    def template_name(self, technique: str) -> str:
        return f"train_{technique}_axolotl.yaml.j2"

    def requirements(self, config: EnvelopeConfig) -> list[str]:
        reqs = [
            "torch>=2.1",
            "axolotl>=0.4",
            "transformers>=4.40",
            "datasets>=2.18",
            "accelerate>=0.30",
        ]
        if config.training.peft.method != PeftMethod.NONE:
            reqs.append("peft>=0.11")
        if config.training.precision.quantization in (Quantization.NF4, Quantization.INT8):
            reqs.append("bitsandbytes>=0.43")
        if config.optimization.flash_attention is not None:
            reqs.append("flash-attn>=2.5")
        if config.optimization.deepspeed_stage is not None:
            reqs.append("deepspeed>=0.14")
        if "wandb" in config.output.report_to:
            reqs.append("wandb>=0.16")
        return reqs

    def template_context(self, config: EnvelopeConfig) -> dict[str, Any]:
        return {
            "config": config,
            "technique_args": config.training.technique_args,
            "hparam_defaults": config.hparam_overrides,
        }

    def launch_command(self, config: EnvelopeConfig) -> str:
        if config.hardware.gpu_count > 1:
            if config.optimization.fsdp.enabled:
                return "accelerate launch --config_file accelerate_config.yaml -m axolotl.cli.train config.yaml"
            return "accelerate launch -m axolotl.cli.train config.yaml"
        return "python -m axolotl.cli.train config.yaml"

    def validate_config(self, config: EnvelopeConfig) -> list[str]:
        errors = []
        technique = config.training.technique.value
        supported = {"sft", "dpo"}
        if technique not in supported:
            errors.append(f"Axolotl does not support technique '{technique}'. Supported: {supported}")
        return errors

    def extra_setup_files(self, config: EnvelopeConfig, output_dir: Path) -> None:
        if config.optimization.fsdp.enabled and config.hardware.gpu_count > 1:
            from envelope.frameworks.accelerate_fsdp import write_accelerate_config

            write_accelerate_config(config, output_dir)
