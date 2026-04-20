"""HuggingFace TRL framework adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from envelope.config.models import EnvelopeConfig, PeftMethod, Quantization
from envelope.frameworks.base import BaseFrameworkAdapter
from envelope.registry import framework_registry


@framework_registry.register("trl")
class TRLAdapter(BaseFrameworkAdapter):
    @property
    def name(self) -> str:
        return "trl"

    @property
    def display_name(self) -> str:
        return "HuggingFace TRL"

    def template_name(self, technique: str) -> str:
        return f"train_{technique}_trl.py.j2"

    def requirements(self, config: EnvelopeConfig) -> list[str]:
        reqs = [
            "torch>=2.1",
            "transformers>=4.40",
            "trl>=1.0.0",
            "datasets>=2.18",
            "accelerate>=0.30",
        ]
        if config.training.peft.method != PeftMethod.NONE:
            reqs.append("peft>=0.11")
        if config.training.precision.quantization in (Quantization.NF4, Quantization.INT8):
            reqs.append("bitsandbytes>=0.43")
        if config.optimization.flash_attention is not None:
            reqs.append("flash-attn>=2.5")
        if config.optimization.vllm_rollout:
            reqs.append("vllm>=0.4")
        if "tensorboard" in config.output.report_to:
            reqs.append("tensorboard>=2.16")
        if "wandb" in config.output.report_to:
            reqs.append("wandb>=0.16")
        return reqs


    def launch_command(self, config: EnvelopeConfig) -> str:
        if config.hardware.gpu_count > 1:
            if config.optimization.fsdp.enabled:
                return (
                    f"accelerate launch --config_file accelerate_config.yaml "
                    f"--num_processes={config.hardware.gpu_count} "
                    "train.py"
                )
            mixed = "bf16" if config.training.precision.compute_dtype.value == "bf16" else "fp16"
            return (
                f"accelerate launch --num_processes={config.hardware.gpu_count} "
                f"--mixed_precision={mixed} "
                "train.py"
            )
        return "python train.py"

    def validate_config(self, config: EnvelopeConfig) -> list[str]:
        errors = []
        technique = config.training.technique.value
        supported = {"sft", "dpo", "simpo", "kto", "orpo", "grpo", "ppo", "rloo",
                      "gkd", "sdft", "sdpo", "gold", "reward_modeling"}
        if technique not in supported:
            errors.append(f"TRL does not support technique '{technique}'. Supported: {supported}")
        return errors

    def extra_setup_files(self, config: EnvelopeConfig, output_dir: Path) -> None:
        if config.optimization.fsdp.enabled and config.hardware.gpu_count > 1:
            from envelope.frameworks.accelerate_fsdp import write_accelerate_config

            write_accelerate_config(config, output_dir)
