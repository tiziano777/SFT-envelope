"""Torchtune framework adapter.

Torchtune is PyTorch's native fine-tuning library with composable
recipes and native distributed support via FSDP2.
"""

from __future__ import annotations

from typing import Any

from envelope.config.models import EnvelopeConfig, PeftMethod, Quantization
from envelope.frameworks.base import BaseFrameworkAdapter
from envelope.registry import framework_registry


@framework_registry.register("torchtune")
class TorchtuneAdapter(BaseFrameworkAdapter):
    @property
    def name(self) -> str:
        return "torchtune"

    @property
    def display_name(self) -> str:
        return "Torchtune (PyTorch)"

    def template_name(self, technique: str) -> str:
        return f"train_{technique}_torchtune.yaml.j2"

    def requirements(self, config: EnvelopeConfig) -> list[str]:
        reqs = [
            "torch>=2.4",
            "torchtune>=0.3",
            "torchao>=0.4",
        ]
        if config.training.precision.quantization in (Quantization.NF4, Quantization.INT8):
            reqs.append("bitsandbytes>=0.43")
        if "wandb" in config.output.report_to:
            reqs.append("wandb>=0.16")
        return reqs


    def launch_command(self, config: EnvelopeConfig) -> str:
        recipe = f"lora_finetune" if config.training.peft.method != PeftMethod.NONE else "full_finetune"
        if config.hardware.gpu_count > 1:
            return f"tune run --nproc_per_node {config.hardware.gpu_count} {recipe}_distributed --config config.yaml"
        return f"tune run {recipe}_single_device --config config.yaml"

    def validate_config(self, config: EnvelopeConfig) -> list[str]:
        errors = []
        technique = config.training.technique.value
        supported = {"sft", "dpo"}
        if technique not in supported:
            errors.append(f"Torchtune does not support technique '{technique}'. Supported: {supported}")
        return errors
