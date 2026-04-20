"""Hardware-aware optimization suggestions.

Given an EnvelopeConfig, suggests optimization flags based on GPU specs and model size.
"""

from __future__ import annotations

import re
from typing import Any

from envelope.config.models import EnvelopeConfig, PeftMethod
from envelope.hardware.gpu_specs import get_gpu_spec, supports_bf16, supports_fp8


def estimate_model_memory_gb(model_name: str) -> float:
    """Estimate model memory in GB from model name heuristics (bf16)."""
    match = re.search(r"(\d+\.?\d*)[bB]", model_name)
    if match:
        billions = float(match.group(1))
        return billions * 2.0  # bf16: 2 bytes per param
    return 14.0  # Default: assume 7B model at bf16


def suggest_optimizations(config: EnvelopeConfig) -> dict[str, Any]:
    """Given a EnvelopeConfig, suggest optimization flags.

    Returns a dict of suggested overrides (not applied automatically).
    The CLI can display these and let the user decide.
    """
    suggestions: dict[str, Any] = {}
    gpu_spec = get_gpu_spec(config.hardware.gpu_type)
    if gpu_spec is None:
        return suggestions

    model_mem = estimate_model_memory_gb(config.model.name_or_path)
    total_vram = gpu_spec.vram_gb * config.hardware.gpu_count

    # Precision suggestions
    if not supports_bf16(config.hardware.gpu_type):
        suggestions["precision.compute_dtype"] = "fp16"
        suggestions["_reason_dtype"] = f"GPU {config.hardware.gpu_type} does not support BF16."

    # FP8 suggestion for Hopper
    if supports_fp8(config.hardware.gpu_type) and model_mem > total_vram * 0.5:
        suggestions["precision.quantization"] = "fp8"
        suggestions["_reason_fp8"] = "Hopper GPU detected. FP8 can double throughput."

    # Quantization suggestion
    if model_mem > total_vram * 0.6 and config.training.peft.method != PeftMethod.NONE:
        suggestions["precision.quantization"] = "nf4"
        suggestions["_reason_quantization"] = (
            f"Model ~{model_mem:.0f}GB exceeds 60% of total VRAM "
            f"({total_vram}GB). Suggest NF4 quantization with PEFT."
        )

    # Gradient checkpointing
    if model_mem > total_vram * 0.3:
        suggestions["optimization.gradient_checkpointing"] = True

    # Flash attention
    if gpu_spec.compute_capability >= (8, 0):
        suggestions["optimization.flash_attention"] = "v2"

    # Sequence packing for SFT
    if config.training.stage.value == 1:
        suggestions["optimization.sequence_packing"] = True

    # Multi-GPU with FSDP/DeepSpeed
    if config.hardware.gpu_count > 1 and config.hardware.num_nodes == 1:
        if model_mem > total_vram * 0.4:
            # Prefer FSDP for PyTorch-native frameworks, DeepSpeed for others
            fsdp_backends = {"trl", "axolotl", "llamafactory", "from_scratch"}
            backend = config.framework.backend.value
            if backend in fsdp_backends:
                suggestions["optimization.fsdp.enabled"] = True
                suggestions["optimization.fsdp.sharding_strategy"] = "full_shard"
                suggestions["_reason_fsdp"] = (
                    f"Model ~{model_mem:.0f}GB with {config.hardware.gpu_count} GPUs. "
                    "FSDP FULL_SHARD recommended for memory-efficient distributed training."
                )
            else:
                suggestions["optimization.deepspeed_stage"] = 2
                suggestions["_reason_deepspeed"] = (
                    f"Model ~{model_mem:.0f}GB with {config.hardware.gpu_count} GPUs. "
                    "DeepSpeed ZeRO-2 recommended for this framework."
                )
        elif model_mem > total_vram * 0.2:
            fsdp_backends = {"trl", "axolotl", "llamafactory", "from_scratch"}
            backend = config.framework.backend.value
            if backend in fsdp_backends:
                suggestions["optimization.fsdp.enabled"] = True
                suggestions["optimization.fsdp.sharding_strategy"] = "shard_grad_op"
                suggestions["_reason_fsdp"] = (
                    f"Model ~{model_mem:.0f}GB fits in VRAM. "
                    "FSDP SHARD_GRAD_OP recommended for faster multi-GPU training."
                )

    # Multi-node: always suggest full sharding for compatible frameworks
    if config.hardware.num_nodes > 1:
        fsdp_backends = {"trl", "axolotl", "llamafactory", "from_scratch"}
        backend = config.framework.backend.value
        if backend in fsdp_backends:
            suggestions["optimization.fsdp.enabled"] = True
            suggestions["optimization.fsdp.sharding_strategy"] = "full_shard"
            suggestions["_reason_fsdp_multinode"] = (
                f"Multi-node ({config.hardware.num_nodes} nodes). "
                "FSDP FULL_SHARD with sync_module_states recommended."
            )

    return suggestions
