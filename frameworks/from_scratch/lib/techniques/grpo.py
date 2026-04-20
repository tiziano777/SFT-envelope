"""GRPO (Group Relative Policy Optimization) trainer.

Advantages are computed via group-level normalization:
    advantage_i = (r_i - mean(r_group)) / (std(r_group) + eps)
Policy loss is the clipped surrogate objective.
"""

from __future__ import annotations

from typing import Any

import torch

from ..rl_trainer import RLTrainer


class GRPOTrainer(RLTrainer):
    """Group Relative Policy Optimization with clipped surrogate loss."""

    def compute_advantages(self, rewards: torch.Tensor, **kwargs: Any) -> torch.Tensor:
        """Group-normalized advantages.

        Reshapes rewards into (B, G) groups, normalizes within each group,
        then flattens back to (B*G,).
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
        """Clipped surrogate loss (PPO-style) with GRPO advantages."""
        epsilon = self._technique_args.get("epsilon", 0.2)
        beta = self._technique_args.get("beta", 0.04)

        ratio = (logprobs - old_logprobs).exp()
        clipped = torch.clamp(ratio, 1.0 - epsilon, 1.0 + epsilon)
        surrogate = -torch.min(ratio * advantages, clipped * advantages).mean()

        # Optional KL penalty
        loss = surrogate
        if beta > 0 and self.ref_model is not None:
            kl = self._compute_kl_penalty(logprobs, old_logprobs)
            loss = loss + beta * kl.mean()

        return loss
