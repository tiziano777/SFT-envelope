"""Shared utility for generating Accelerate FSDP configuration files.

Used by TRL, Axolotl, and LlamaFactory adapters to produce a consistent
accelerate_config.yaml when FSDP is enabled.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from envelope.config.models import EnvelopeConfig


_SHARDING_MAP: dict[str, str] = {
    "full_shard": "FULL_SHARD",
    "shard_grad_op": "SHARD_GRAD_OP",
    "no_shard": "NO_SHARD",
    "hybrid_shard": "HYBRID_SHARD",
}

_BACKWARD_PREFETCH_MAP: dict[str, str] = {
    "backward_pre": "BACKWARD_PRE",
    "backward_post": "BACKWARD_POST",
}


def build_accelerate_fsdp_config(config: EnvelopeConfig) -> dict[str, Any]:
    """Build an Accelerate YAML config dict with FSDP settings.

    Returns a dict suitable for writing as accelerate_config.yaml.
    """
    fsdp = config.optimization.fsdp

    return {
        "compute_environment": "LOCAL_MACHINE",
        "distributed_type": "FSDP",
        "fsdp_config": {
            "fsdp_sharding_strategy": _SHARDING_MAP[fsdp.sharding_strategy.value],
            "fsdp_auto_wrap_policy": fsdp.auto_wrap_policy.value.upper(),
            "fsdp_min_num_params": fsdp.min_num_params,
            "fsdp_offload_params": fsdp.cpu_offload,
            "fsdp_forward_prefetch": fsdp.forward_prefetch,
            "fsdp_backward_prefetch": _BACKWARD_PREFETCH_MAP[fsdp.backward_prefetch.value],
            "fsdp_sync_module_states": fsdp.sync_module_states,
            "fsdp_use_orig_params": fsdp.use_orig_params,
            "fsdp_activation_checkpointing": fsdp.activation_checkpointing,
            "fsdp_limit_all_gathers": fsdp.limit_all_gathers,
            "fsdp_cpu_ram_efficient_loading": True,
            "fsdp_state_dict_type": "SHARDED_STATE_DICT",
        },
        "mixed_precision": fsdp.mixed_precision.value if fsdp.mixed_precision.value != "none" else "no",
        "num_processes": config.hardware.gpu_count * config.hardware.num_nodes,
        "machine_rank": 0,
        "num_machines": config.hardware.num_nodes,
    }


def write_accelerate_config(config: EnvelopeConfig, output_dir: str | Path) -> None:
    """Write accelerate_config.yaml to the setup output directory."""
    import yaml

    accel_config = build_accelerate_fsdp_config(config)
    accel_path = Path(output_dir) / "accelerate_config.yaml"
    accel_path.write_text(yaml.dump(accel_config, default_flow_style=False, sort_keys=False))
