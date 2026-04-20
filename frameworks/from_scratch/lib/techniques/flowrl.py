"""FlowRL trainer.

Flow-based RL approach using group-level reward normalization
with continuous flow matching for policy updates.
"""

from __future__ import annotations

from typing import Any

import torch

from ..rl_trainer import RLTrainer


class FlowRLTrainer(RLTrainer):
    """Flow-based Reinforcement Learning trainer."""

    def compute_advantages(self, rewards: torch.Tensor, **kwargs: Any) -> torch.Tensor:
        """Group-normalized advantages (shared with GRPO family)."""
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
        """Flow-weighted policy gradient loss."""
        epsilon = self._technique_args.get("epsilon", 0.2)
        flow_alpha = self._technique_args.get("flow_alpha", 0.5)

        ratio = (logprobs - old_logprobs).exp()
        clipped = torch.clamp(ratio, 1.0 - epsilon, 1.0 + epsilon)

        # Flow weighting: blend ratio-based and direct gradient
        standard_loss = -torch.min(ratio * advantages, clipped * advantages)
        direct_loss = -logprobs * advantages.detach()
        loss = flow_alpha * standard_loss + (1 - flow_alpha) * direct_loss

        return loss.mean()
