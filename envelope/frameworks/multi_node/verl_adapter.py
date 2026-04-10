"""veRL (ByteDance) framework adapter.

veRL is ByteDance's multi-node RL framework supporting GRPO, DAPO,
VAPO, PRIME, PPO, and other advanced RL techniques with Ray-based
orchestration and vLLM rollout.
"""

from __future__ import annotations

from typing import Any

from envelope.config.models import EnvelopeConfig, PeftMethod, Quantization
from envelope.frameworks.base import BaseFrameworkAdapter
from envelope.registry import framework_registry


@framework_registry.register("verl")
class VeRLAdapter(BaseFrameworkAdapter):
    @property
    def name(self) -> str:
        return "verl"

    @property
    def display_name(self) -> str:
        return "veRL (ByteDance)"

    def template_name(self, technique: str) -> str:
        return f"train_{technique}_verl.sh.j2"

    def requirements(self, config: EnvelopeConfig) -> list[str]:
        reqs = [
            "torch>=2.1",
            "verl>=0.2",
            "vllm>=0.4",
            "ray>=2.30",
            "transformers>=4.40",
            "datasets>=2.18",
        ]
        if config.training.peft.method != PeftMethod.NONE:
            reqs.append("peft>=0.11")
        if config.training.precision.quantization in (Quantization.NF4, Quantization.INT8):
            reqs.append("bitsandbytes>=0.43")
        if config.optimization.flash_attention is not None:
            reqs.append("flash-attn>=2.5")
        if "wandb" in config.output.report_to:
            reqs.append("wandb>=0.16")
        return reqs


    def launch_command(self, config: EnvelopeConfig) -> str:
        return "bash train.sh"

    def validate_config(self, config: EnvelopeConfig) -> list[str]:
        errors = []
        technique = config.training.technique.value
        supported = {"grpo", "dapo", "vapo", "ppo", "reinforce_pp", "dr_grpo", "flowrl", "prime"}
        if technique not in supported:
            errors.append(f"veRL does not support technique '{technique}'. Supported: {supported}")
        return errors
