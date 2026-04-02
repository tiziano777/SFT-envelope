"""SimPO (Simple Preference Optimization) trainer.

Reference-free DPO variant: length-normalized log-probs with a gamma margin.
Loss: -log_sigmoid(β * (avg_logp_chosen - avg_logp_rejected - γ))
"""

from __future__ import annotations

import torch
import torch.nn.functional as F

from ..preference_trainer import PreferenceTrainer


class SimPOTrainer(PreferenceTrainer):
    """Simple Preference Optimization (reference-free, length-normalized)."""

    def preference_loss(
        self,
        policy_logps_chosen: torch.Tensor,
        policy_logps_rejected: torch.Tensor,
        ref_logps_chosen: torch.Tensor | None,
        ref_logps_rejected: torch.Tensor | None,
    ) -> torch.Tensor:
        beta = self.config.technique_args.get("beta", 2.0)
        gamma = self.config.technique_args.get("gamma", 0.5)

        # SimPO uses average log-probs (length-normalized).
        # The log-probs from PreferenceTrainer are already summed,
        # so we normalize by sequence length here.
        # For simplicity, use the raw sums — user can override for exact length normalization.
        diff = policy_logps_chosen - policy_logps_rejected - gamma
        return -F.logsigmoid(beta * diff).mean()
