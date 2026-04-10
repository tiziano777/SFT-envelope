"""OpenRLHF framework adapter.

OpenRLHF is a Ray-based open-source RLHF framework supporting PPO,
GRPO, RLOO, REINFORCE++, DPO, and SFT with multi-node scaling.
"""

from __future__ import annotations

from typing import Any

from envelope.config.models import EnvelopeConfig, PeftMethod, Quantization
from envelope.frameworks.base import BaseFrameworkAdapter
from envelope.registry import framework_registry


@framework_registry.register("openrlhf")
class OpenRLHFAdapter(BaseFrameworkAdapter):
    @property
    def name(self) -> str:
        return "openrlhf"

    @property
    def display_name(self) -> str:
        return "OpenRLHF"

    def template_name(self, technique: str) -> str:
        return f"train_{technique}_openrlhf.sh.j2"

    def requirements(self, config: EnvelopeConfig) -> list[str]:
        reqs = [
            "torch>=2.1",
            "openrlhf>=0.4",
            "vllm>=0.4",
            "ray>=2.30",
            "transformers>=4.40",
            "datasets>=2.18",
            "deepspeed>=0.14",
        ]
        if config.training.peft.method != PeftMethod.NONE:
            reqs.append("peft>=0.11")
        if config.optimization.flash_attention is not None:
            reqs.append("flash-attn>=2.5")
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
        return "bash train.sh"

    def validate_config(self, config: EnvelopeConfig) -> list[str]:
        errors = []
        technique = config.training.technique.value
        supported = {"sft", "dpo", "grpo", "ppo", "rloo", "reinforce_pp"}
        if technique not in supported:
            errors.append(f"OpenRLHF does not support technique '{technique}'. Supported: {supported}")
        return errors
