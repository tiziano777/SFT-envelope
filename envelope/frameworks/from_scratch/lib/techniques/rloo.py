"""RLOO (REINFORCE Leave-One-Out) trainer.

Uses a leave-one-out baseline: for each generation, the baseline is
the mean reward of all OTHER generations in the group.
"""

from __future__ import annotations

from typing import Any

import torch

from ..rl_trainer import RLTrainer


class RLOOTrainer(RLTrainer):
    """REINFORCE with Leave-One-Out baseline."""

    def compute_advantages(self, rewards: torch.Tensor, **kwargs: Any) -> torch.Tensor:
        """Leave-one-out baseline.

        For each sample i in a group of G, baseline_i = mean(r_j for j != i).
        advantage_i = r_i - baseline_i
        """
        num_generations = self._technique_args.get("num_generations", 4)
        batch_size = rewards.shape[0] // num_generations

        if batch_size == 0 or num_generations <= 1:
            return rewards - rewards.mean()

        grouped = rewards.view(batch_size, num_generations)
        group_sum = grouped.sum(dim=1, keepdim=True)

        # Leave-one-out mean: (sum - self) / (G - 1)
        baselines = (group_sum - grouped) / (num_generations - 1)
        advantages = grouped - baselines
        return advantages.view(-1)

    def policy_loss(
        self,
        logprobs: torch.Tensor,
        old_logprobs: torch.Tensor,
        advantages: torch.Tensor,
    ) -> torch.Tensor:
        """REINFORCE loss: -logprob * advantage."""
        return -(logprobs * advantages.detach()).mean()
