"""GPU specifications database for hardware-aware optimization."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GPUSpec:
    name: str
    vram_gb: int
    compute_capability: tuple[int, int]
    fp16_tflops: float
    bf16_tflops: float
    fp8_supported: bool
    memory_bandwidth_gbps: int


GPU_DATABASE: dict[str, GPUSpec] = {
    "A100-40GB": GPUSpec("A100-40GB", 40, (8, 0), 312, 312, False, 1555),
    "A100-80GB": GPUSpec("A100-80GB", 80, (8, 0), 312, 312, False, 2039),
    "H100-80GB": GPUSpec("H100-80GB", 80, (9, 0), 989, 989, True, 3350),
    "H200": GPUSpec("H200", 141, (9, 0), 989, 989, True, 4800),
    "L40S": GPUSpec("L40S", 48, (8, 9), 362, 362, True, 864),
    "L4": GPUSpec("L4", 24, (8, 9), 121, 121, True, 300),
    "A10G": GPUSpec("A10G", 24, (8, 6), 125, 125, False, 600),
    "T4": GPUSpec("T4", 16, (7, 5), 65, 0, False, 320),
    "V100-16GB": GPUSpec("V100-16GB", 16, (7, 0), 125, 0, False, 900),
    "V100-32GB": GPUSpec("V100-32GB", 32, (7, 0), 125, 0, False, 900),
    "RTX4090": GPUSpec("RTX 4090", 24, (8, 9), 165, 165, True, 1008),
    "RTX3090": GPUSpec("RTX 3090", 24, (8, 6), 71, 71, False, 936),
}


def get_gpu_spec(gpu_type: str) -> GPUSpec | None:
    """Look up GPU spec by name. Case-insensitive, partial match."""
    normalized = gpu_type.upper().replace(" ", "").replace("-", "")
    for key, spec in GPU_DATABASE.items():
        if normalized in key.upper().replace(" ", "").replace("-", ""):
            return spec
    return None


def supports_bf16(gpu_type: str) -> bool:
    spec = get_gpu_spec(gpu_type)
    return spec is not None and spec.compute_capability >= (8, 0)


def supports_fp8(gpu_type: str) -> bool:
    spec = get_gpu_spec(gpu_type)
    return spec is not None and spec.fp8_supported
