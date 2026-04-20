"""Fused RMS Normalization: Triton kernel + PyTorch fallback.

RMSNorm(x) = x * weight / sqrt(mean(x^2) + eps)

The Triton kernel fuses the computation to avoid multiple passes over data.
"""

from __future__ import annotations

from typing import Any

import torch

from . import kernel_registry
from .registry import TritonOp, _triton_available


@kernel_registry.register("rms_norm")
class FusedRMSNorm(TritonOp):
    """Fused RMS normalization."""

    def forward_torch(
        self,
        x: torch.Tensor,
        weight: torch.Tensor,
        eps: float = 1e-6,
        **kwargs: Any,
    ) -> torch.Tensor:
        """Standard PyTorch RMSNorm."""
        dtype = x.dtype
        x = x.float()
        rms = torch.sqrt(x.pow(2).mean(dim=-1, keepdim=True) + eps)
        return (x / rms).to(dtype) * weight

    def forward_triton(
        self,
        x: torch.Tensor,
        weight: torch.Tensor,
        eps: float = 1e-6,
        **kwargs: Any,
    ) -> torch.Tensor:
        """Triton fused RMSNorm kernel."""
        if not _triton_available():
            return self.forward_torch(x, weight, eps, **kwargs)

        import triton

        orig_shape = x.shape
        x_2d = x.reshape(-1, orig_shape[-1])
        N, D = x_2d.shape
        output = torch.empty_like(x_2d)

        BLOCK_D = triton.next_power_of_2(D)
        grid = (N,)

        _rms_norm_kernel[grid](
            x_2d, weight, output,
            D, eps, BLOCK_D,
            num_warps=4,
        )

        return output.reshape(orig_shape)


if _triton_available():
    import triton
    import triton.language as tl

    @triton.jit
    def _rms_norm_kernel(
        x_ptr, weight_ptr, output_ptr,
        D: tl.constexpr, eps: tl.constexpr, BLOCK_D: tl.constexpr,
    ):
        row = tl.program_id(0)
        cols = tl.arange(0, BLOCK_D)
        mask = cols < D

        # Load row
        x = tl.load(x_ptr + row * D + cols, mask=mask, other=0.0).to(tl.float32)
        w = tl.load(weight_ptr + cols, mask=mask, other=0.0)

        # RMS
        x_sq = x * x
        mean_sq = tl.sum(x_sq, axis=0) / D
        rms = tl.sqrt(mean_sq + eps)

        # Normalize
        normed = x / rms * w

        tl.store(output_ptr + row * D + cols, normed, mask=mask)
