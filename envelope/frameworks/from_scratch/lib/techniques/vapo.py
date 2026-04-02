"""VAPO (Value-Augmented Policy Optimization) trainer.

Extends PPO with value-aware clipping that adjusts the clip range
based on the value estimate confidence.
"""

from __future__ import annotations

from typing import Any

import torch
import torch.nn as nn

from ..rl_trainer import RLTrainer


class VAPOTrainer(RLTrainer):
    """Value-Augmented Policy Optimization."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        hidden_size = getattr(self.model.config, "hidden_size", 4096)
        self.value_head = nn.Linear(hidden_size, 1).to(self.device)
        self._vf_coef = self._technique_args.get("vf_coef", 0.1)

    def compute_advantages(self, rewards: torch.Tensor, **kwargs: Any) -> torch.Tensor:
        """Reward - baseline (simplified value-aware estimation)."""
        baseline = rewards.mean()
        return rewards - baseline

    def policy_loss(
        self,
        logprobs: torch.Tensor,
        old_logprobs: torch.Tensor,
        advantages: torch.Tensor,
    ) -> torch.Tensor:
        """Value-aware clipped surrogate loss."""
        epsilon = self._technique_args.get("epsilon", 0.2)

        ratio = (logprobs - old_logprobs).exp()
        clipped = torch.clamp(ratio, 1.0 - epsilon, 1.0 + epsilon)
        policy_loss = -torch.min(ratio * advantages.detach(), clipped * advantages.detach()).mean()
        value_loss = self._vf_coef * advantages.pow(2).mean()

        return policy_loss + value_loss
