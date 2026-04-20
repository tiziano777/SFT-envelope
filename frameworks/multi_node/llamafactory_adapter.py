"""LlamaFactory framework adapter.

LlamaFactory provides a unified UI/CLI for fine-tuning 100+ LLMs
with support for SFT, DPO, KTO, ORPO, and PPO.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from envelope.config.models import EnvelopeConfig, PeftMethod, Quantization
from envelope.frameworks.base import BaseFrameworkAdapter
from envelope.registry import framework_registry


@framework_registry.register("llamafactory")
class LlamaFactoryAdapter(BaseFrameworkAdapter):
    @property
    def name(self) -> str:
        return "llamafactory"

    @property
    def display_name(self) -> str:
        return "LlamaFactory"

    def template_name(self, technique: str) -> str:
        return f"train_{technique}_llamafactory.yaml.j2"

    def requirements(self, config: EnvelopeConfig) -> list[str]:
        reqs = [
            "torch>=2.1",
            "llamafactory>=0.8",
            "transformers>=4.40",
            "datasets>=2.18",
        ]
        if config.training.peft.method != PeftMethod.NONE:
            reqs.append("peft>=0.11")
        if config.training.precision.quantization in (Quantization.NF4, Quantization.INT8):
            reqs.append("bitsandbytes>=0.43")
        if config.optimization.flash_attention is not None:
            reqs.append("flash-attn>=2.5")
        if config.optimization.deepspeed_stage is not None:
            reqs.append("deepspeed>=0.14")
        if config.optimization.fsdp.enabled:
            reqs.append("accelerate>=0.30")
        if "wandb" in config.output.report_to:
            reqs.append("wandb>=0.16")
        return reqs


    def launch_command(self, config: EnvelopeConfig) -> str:
        if config.optimization.fsdp.enabled and config.hardware.gpu_count > 1:
            return "accelerate launch --config_file accelerate_config.yaml llamafactory-cli train config.yaml"
        return "llamafactory-cli train config.yaml"

    def validate_config(self, config: EnvelopeConfig) -> list[str]:
        errors = []
        technique = config.training.technique.value
        supported = {"sft", "dpo", "kto", "orpo"}
        if technique not in supported:
            errors.append(f"LlamaFactory does not support technique '{technique}'. Supported: {supported}")
        return errors

    def extra_setup_files(self, config: EnvelopeConfig, output_dir: Path) -> None:
        if config.optimization.fsdp.enabled and config.hardware.gpu_count > 1:
            from envelope.frameworks.accelerate_fsdp import write_accelerate_config

            write_accelerate_config(config, output_dir)
