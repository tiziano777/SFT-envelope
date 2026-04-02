"""From-scratch framework adapter: raw PyTorch training with ABC class hierarchy."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from envelope.config.models import EnvelopeConfig, PeftMethod, Quantization
from envelope.frameworks.base import BaseFrameworkAdapter
from envelope.registry import framework_registry

LIB_DIR = Path(__file__).parent / "lib"

# Technique → (module path relative to fromscratch/, class name)
_TRAINER_MAP: dict[str, tuple[str, str]] = {
    # SFT
    "sft": ("sft_trainer", "SFTTrainer"),
    # Preference
    "dpo": ("techniques.dpo", "DPOTrainer"),
    "simpo": ("techniques.simpo", "SimPOTrainer"),
    "kto": ("techniques.kto", "KTOTrainer"),
    "orpo": ("techniques.orpo", "ORPOTrainer"),
    # RL
    "grpo": ("techniques.grpo", "GRPOTrainer"),
    "ppo": ("techniques.ppo", "PPOTrainer"),
    "dapo": ("techniques.dapo", "DAPOTrainer"),
    "vapo": ("techniques.vapo", "VAPOTrainer"),
    "rloo": ("techniques.rloo", "RLOOTrainer"),
    "reinforce_pp": ("techniques.reinforce_pp", "ReinforcePPTrainer"),
    "dr_grpo": ("techniques.dr_grpo", "DrGRPOTrainer"),
    # Flow
    "flowrl": ("techniques.flowrl", "FlowRLTrainer"),
    "prime": ("techniques.prime", "PRIMETrainer"),
}


@framework_registry.register("from_scratch")
class FromScratchAdapter(BaseFrameworkAdapter):
    """Framework adapter that generates raw PyTorch training setups with ABC scaffolding."""

    @property
    def name(self) -> str:
        return "from_scratch"

    @property
    def display_name(self) -> str:
        return "From Scratch (Raw PyTorch)"

    def template_name(self, technique: str) -> str:
        return "train_fromscratch.py.j2"

    def requirements(self, config: EnvelopeConfig) -> list[str]:
        reqs = [
            "torch>=2.1",
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
        if config.framework.triton_kernels:
            reqs.append("triton>=3.0")
        if "tensorboard" in config.output.report_to:
            reqs.append("tensorboard>=2.16")
        if "wandb" in config.output.report_to:
            reqs.append("wandb>=0.16")
        return reqs

    def template_context(self, config: EnvelopeConfig) -> dict[str, Any]:
        technique = config.training.technique.value
        trainer_module, trainer_class = _TRAINER_MAP[technique]
        return {
            "config": config,
            "technique_args": config.training.technique_args,
            "hparam_defaults": getattr(config, "_hparam_defaults", {}),
            "trainer_module": trainer_module,
            "trainer_class": trainer_class,
            "triton_kernels": config.framework.triton_kernels,
        }

    def launch_command(self, config: EnvelopeConfig) -> str:
        if config.hardware.gpu_count > 1 or config.hardware.num_nodes > 1:
            cmd = f"torchrun --nproc_per_node={config.hardware.gpu_count}"
            if config.hardware.num_nodes > 1:
                cmd += f" --nnodes={config.hardware.num_nodes}"
                cmd += " --rdzv_backend=c10d --rdzv_endpoint=$MASTER_ADDR:$MASTER_PORT"
            cmd += " train.py"
            return cmd
        return "python train.py"

    def validate_config(self, config: EnvelopeConfig) -> list[str]:
        errors = []
        technique = config.training.technique.value
        if technique not in _TRAINER_MAP:
            errors.append(
                f"from_scratch does not have a trainer for technique '{technique}'. "
                f"Available: {sorted(_TRAINER_MAP.keys())}"
            )
        return errors

    def extra_setup_files(self, config: EnvelopeConfig, output_dir: Path) -> None:
        """Copy the from-scratch lib/ into the setup as a local 'fromscratch' package."""
        dest = output_dir / "fromscratch"
        shutil.copytree(LIB_DIR, dest, dirs_exist_ok=True)
