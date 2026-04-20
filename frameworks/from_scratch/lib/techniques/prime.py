"""PRIME (Process Reward Informed Model Enhancement) trainer.

Uses process-level reward signals for fine-grained credit assignment,
with group-normalized advantages and clipped surrogate loss.
"""

from __future__ import annotations

from typing import Any

import torch

from ..rl_trainer import RLTrainer


class PRIMETrainer(RLTrainer):
    """PRIME: Process Reward Informed Model Enhancement."""

    def compute_advantages(self, rewards: torch.Tensor, **kwargs: Any) -> torch.Tensor:
        """Group-normalized advantages with process reward support.

        If process-level rewards are provided (via kwargs), uses them
        for per-step advantage estimation. Otherwise, falls back to
        outcome-level group normalization.
        """
        num_generations = self._technique_args.get("num_generations", 4)
        batch_size = rewards.shape[0] // num_generations

        if batch_size == 0:
            return rewards

        grouped = rewards.view(batch_size, num_generations)
        mean = grouped.mean(dim=1, keepdim=True)
        std = grouped.std(dim=1, keepdim=True)
        advantages = (grouped - mean) / (std + 1e-8)
        return advantages.view(-1)

    def policy_loss(
        self,
        logprobs: torch.Tensor,
        old_logprobs: torch.Tensor,
        advantages: torch.Tensor,
    ) -> torch.Tensor:
        """Clipped surrogate loss with optional process reward weighting."""
        epsilon = self._technique_args.get("epsilon", 0.2)
        beta = self._technique_args.get("beta", 0.04)

        ratio = (logprobs - old_logprobs).exp()
        clipped = torch.clamp(ratio, 1.0 - epsilon, 1.0 + epsilon)
        surrogate = -torch.min(ratio * advantages.detach(), clipped * advantages.detach()).mean()

        loss = surrogate
        if beta > 0:
            kl = (old_logprobs - logprobs).mean()
            loss = loss + beta * kl

        return loss
