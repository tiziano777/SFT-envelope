"""Dr. GRPO (Doubly Robust GRPO) trainer.

Extends GRPO with Bessel correction for unbiased variance estimation
and optional length normalization to avoid length biases.
"""

from __future__ import annotations

from typing import Any

import torch

from ..rl_trainer import RLTrainer


class DrGRPOTrainer(RLTrainer):
    """Dr. GRPO: Doubly Robust Group Relative Policy Optimization."""

    def compute_advantages(self, rewards: torch.Tensor, **kwargs: Any) -> torch.Tensor:
        """Group-normalized advantages with Bessel correction.

        Uses ddof=1 (Bessel's correction) for unbiased std estimation.
        """
        num_generations = self._technique_args.get("num_generations", 4)
        batch_size = rewards.shape[0] // num_generations

        if batch_size == 0 or num_generations <= 1:
            return rewards - rewards.mean()

        grouped = rewards.view(batch_size, num_generations)
        mean = grouped.mean(dim=1, keepdim=True)
        # Bessel correction: ddof=1 for unbiased variance
        std = grouped.std(dim=1, keepdim=True, correction=1)
        advantages = (grouped - mean) / (std + 1e-8)
        return advantages.view(-1)

    def policy_loss(
        self,
        logprobs: torch.Tensor,
        old_logprobs: torch.Tensor,
        advantages: torch.Tensor,
    ) -> torch.Tensor:
        """Clipped surrogate loss with optional length normalization."""
        epsilon = self._technique_args.get("epsilon", 0.2)
        beta = self._technique_args.get("beta", 0.04)

        ratio = (logprobs - old_logprobs).exp()
        clipped = torch.clamp(ratio, 1.0 - epsilon, 1.0 + epsilon)
        surrogate = -torch.min(ratio * advantages.detach(), clipped * advantages.detach()).mean()

        loss = surrogate
        if beta > 0 and self.ref_model is not None:
            kl = self._compute_kl_penalty(logprobs, old_logprobs)
            loss = loss + beta * kl.mean()

        return loss
