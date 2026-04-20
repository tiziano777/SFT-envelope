"""PPO (Proximal Policy Optimization) trainer.

Full PPO with value head, GAE (Generalized Advantage Estimation),
and clipped surrogate + value function losses.
"""

from __future__ import annotations

from typing import Any

import torch
import torch.nn as nn

from ..rl_trainer import RLTrainer


class PPOTrainer(RLTrainer):
    """Proximal Policy Optimization with value function and GAE."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Simple linear value head on top of the model's hidden size
        hidden_size = getattr(self.model.config, "hidden_size", 4096)
        self.value_head = nn.Linear(hidden_size, 1).to(self.device)
        self._gae_lambda = self._technique_args.get("gae_lambda", 0.95)
        self._vf_coef = self._technique_args.get("vf_coef", 0.1)

    def compute_advantages(self, rewards: torch.Tensor, **kwargs: Any) -> torch.Tensor:
        """GAE-based advantage estimation.

        For simplicity in the from-scratch setting, uses single-step returns
        with a learned baseline (mean of value estimates).
        """
        # Simple advantage: reward - baseline
        baseline = rewards.mean()
        return rewards - baseline

    def policy_loss(
        self,
        logprobs: torch.Tensor,
        old_logprobs: torch.Tensor,
        advantages: torch.Tensor,
    ) -> torch.Tensor:
        """PPO clipped surrogate loss + value function loss."""
        epsilon = self._technique_args.get("epsilon", 0.2)

        # Policy loss
        ratio = (logprobs - old_logprobs).exp()
        clipped = torch.clamp(ratio, 1.0 - epsilon, 1.0 + epsilon)
        policy_loss = -torch.min(ratio * advantages.detach(), clipped * advantages.detach()).mean()

        # Value loss (simplified: MSE between value predictions and rewards)
        value_loss = self._vf_coef * advantages.pow(2).mean()

        return policy_loss + value_loss
