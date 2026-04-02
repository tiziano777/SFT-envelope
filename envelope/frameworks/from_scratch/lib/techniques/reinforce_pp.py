"""REINFORCE++ trainer.

Clipped REINFORCE with an exponential moving average baseline
and optional entropy bonus.
"""

from __future__ import annotations

from typing import Any

import torch

from ..rl_trainer import RLTrainer


class ReinforcePPTrainer(RLTrainer):
    """Clipped REINFORCE++ with EMA baseline."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._ema_baseline = 0.0
        self._ema_decay = self._technique_args.get("ema_decay", 0.99)

    def compute_advantages(self, rewards: torch.Tensor, **kwargs: Any) -> torch.Tensor:
        """Advantages with EMA baseline."""
        # Update EMA
        batch_mean = rewards.mean().item()
        self._ema_baseline = self._ema_decay * self._ema_baseline + (1 - self._ema_decay) * batch_mean

        advantages = rewards - self._ema_baseline

        # Normalize
        std = advantages.std()
        if std > 1e-8:
            advantages = advantages / std

        return advantages

    def policy_loss(
        self,
        logprobs: torch.Tensor,
        old_logprobs: torch.Tensor,
        advantages: torch.Tensor,
    ) -> torch.Tensor:
        """Clipped REINFORCE loss."""
        epsilon = self._technique_args.get("epsilon", 0.2)

        ratio = (logprobs - old_logprobs).exp()
        clipped = torch.clamp(ratio, 1.0 - epsilon, 1.0 + epsilon)
        return -torch.min(ratio * advantages.detach(), clipped * advantages.detach()).mean()
