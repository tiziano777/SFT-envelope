"""Triton kernel support with automatic PyTorch fallback.

Usage:
    from fromscratch.kernels import kernel_registry
    fused_ce = kernel_registry.get("cross_entropy")
    loss = fused_ce(logits, labels)

All kernels work without Triton installed (via PyTorch fallback).
"""

from .registry import KernelRegistry

kernel_registry = KernelRegistry()

# Auto-register bundled kernels
from . import cross_entropy as _ce  # noqa: F401, E402
from . import rms_norm as _rn  # noqa: F401, E402
from . import softmax as _sm  # noqa: F401, E402
