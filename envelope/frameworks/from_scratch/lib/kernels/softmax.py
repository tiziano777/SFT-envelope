"""Fused softmax: Triton kernel + PyTorch fallback.

Online softmax that computes the result in a single pass,
avoiding materialization of intermediate max/exp tensors.
"""

from __future__ import annotations

from typing import Any

import torch
import torch.nn.functional as F

from . import kernel_registry
from .registry import TritonOp, _triton_available


@kernel_registry.register("softmax")
class FusedSoftmax(TritonOp):
    """Fused online softmax."""

    def forward_torch(self, x: torch.Tensor, dim: int = -1, **kwargs: Any) -> torch.Tensor:
        """Standard PyTorch softmax."""
        return F.softmax(x, dim=dim)

    def forward_triton(self, x: torch.Tensor, dim: int = -1, **kwargs: Any) -> torch.Tensor:
        """Triton fused softmax kernel (operates on last dimension)."""
        if not _triton_available() or dim != -1:
            return self.forward_torch(x, dim, **kwargs)

        import triton

        orig_shape = x.shape
        x_2d = x.reshape(-1, orig_shape[-1])
        N, D = x_2d.shape
        output = torch.empty_like(x_2d)

        BLOCK_D = triton.next_power_of_2(D)
        grid = (N,)

        _softmax_kernel[grid](
            x_2d, output,
            D, BLOCK_D,
            num_warps=4,
        )

        return output.reshape(orig_shape)


if _triton_available():
    import triton
    import triton.language as tl

    @triton.jit
    def _softmax_kernel(
        x_ptr, output_ptr,
        D: tl.constexpr, BLOCK_D: tl.constexpr,
    ):
        row = tl.program_id(0)
        cols = tl.arange(0, BLOCK_D)
        mask = cols < D

        # Load
        x = tl.load(x_ptr + row * D + cols, mask=mask, other=-float("inf"))

        # Stable softmax
        max_val = tl.max(x, axis=0)
        x = x - max_val
        exp_x = tl.exp(x)
        sum_exp = tl.sum(exp_x, axis=0)
        result = exp_x / sum_exp

        tl.store(output_ptr + row * D + cols, result, mask=mask)
