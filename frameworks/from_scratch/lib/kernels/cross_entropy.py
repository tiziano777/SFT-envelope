"""Fused cross-entropy loss: Triton kernel + PyTorch fallback.

The Triton kernel fuses the softmax and NLL computation to avoid
materializing large intermediate tensors, reducing memory by ~2x.
"""

from __future__ import annotations

from typing import Any

import torch
import torch.nn.functional as F

from . import kernel_registry
from .registry import TritonOp, _triton_available


@kernel_registry.register("cross_entropy")
class FusedCrossEntropy(TritonOp):
    """Fused cross-entropy: softmax + NLL in a single pass."""

    def forward_torch(self, logits: torch.Tensor, labels: torch.Tensor, **kwargs: Any) -> torch.Tensor:
        """Standard PyTorch cross-entropy."""
        # Reshape for cross_entropy: (N, C) and (N,)
        if logits.dim() == 3:
            # (B, T, V) -> (B*T, V)
            B, T, V = logits.shape
            logits = logits.reshape(-1, V)
            labels = labels.reshape(-1)
        return F.cross_entropy(logits, labels, ignore_index=-100)

    def forward_triton(self, logits: torch.Tensor, labels: torch.Tensor, **kwargs: Any) -> torch.Tensor:
        """Triton fused cross-entropy kernel."""
        if not _triton_available():
            return self.forward_torch(logits, labels, **kwargs)

        import triton

        if logits.dim() == 3:
            B, T, V = logits.shape
            logits_2d = logits.reshape(-1, V)
            labels_1d = labels.reshape(-1)
        else:
            logits_2d = logits
            labels_1d = labels

        N, V = logits_2d.shape
        losses = torch.empty(N, device=logits.device, dtype=torch.float32)

        # Triton kernel grid
        BLOCK_V = triton.next_power_of_2(V)
        grid = (N,)

        _fused_ce_kernel[grid](
            logits_2d, labels_1d, losses,
            V, BLOCK_V,
            num_warps=4,
        )

        # Mask out ignored indices
        mask = labels_1d != -100
        if mask.any():
            return losses[mask].mean()
        return losses.mean()


if _triton_available():
    import triton
    import triton.language as tl

    @triton.jit
    def _fused_ce_kernel(
        logits_ptr, labels_ptr, losses_ptr,
        V: tl.constexpr, BLOCK_V: tl.constexpr,
    ):
        row = tl.program_id(0)
        cols = tl.arange(0, BLOCK_V)
        mask = cols < V

        # Load logits for this row
        logits = tl.load(logits_ptr + row * V + cols, mask=mask, other=-float("inf"))

        # Numerically stable softmax
        max_val = tl.max(logits, axis=0)
        logits = logits - max_val
        exp_logits = tl.exp(logits)
        sum_exp = tl.sum(exp_logits, axis=0)
        log_sum_exp = tl.log(sum_exp)

        # Load label
        label = tl.load(labels_ptr + row)

        # Cross-entropy = -logits[label] + log_sum_exp
        # Only compute for valid labels (>= 0)
        label_logit = tl.load(logits_ptr + row * V + label, mask=label >= 0, other=0.0)
        label_logit = label_logit - max_val
        loss = tl.where(label >= 0, -label_logit + log_sum_exp, 0.0)

        tl.store(losses_ptr + row, loss)
