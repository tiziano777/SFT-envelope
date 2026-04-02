"""DAPO (Dual-clip Advantage Policy Optimization) trainer.

Extends PPO with dual-clipping: clips both above and below,
and uses dynamic sampling to filter low-quality generations.
"""

from __future__ import annotations

from typing import Any

import torch

from ..rl_trainer import RLTrainer


class DAPOTrainer(RLTrainer):
    """Dual-clip Advantage Policy Optimization with dynamic sampling."""

    def compute_advantages(self, rewards: torch.Tensor, **kwargs: Any) -> torch.Tensor:
        """Group-normalized advantages (same as GRPO)."""
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
        """Dual-clipped surrogate loss.

        Clips ratio above at (1+ε) for positive advantages and below
        at (1-ε) for both, plus a lower bound clip at c for negative advantages.
        """
        epsilon = self._technique_args.get("epsilon", 0.2)
        clip_lower = self._technique_args.get("clip_lower", 0.5)

        ratio = (logprobs - old_logprobs).exp()

        # Standard PPO clipping
        clipped = torch.clamp(ratio, 1.0 - epsilon, 1.0 + epsilon)
        surrogate = torch.min(ratio * advantages, clipped * advantages)

        # DAPO dual clip: for negative advantages, add a lower bound
        neg_mask = advantages < 0
        if neg_mask.any():
            lower_bound = clip_lower * advantages[neg_mask]
            surrogate[neg_mask] = torch.max(surrogate[neg_mask], lower_bound)

        return -surrogate.mean()
