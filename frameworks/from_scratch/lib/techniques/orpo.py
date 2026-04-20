"""ORPO (Odds Ratio Preference Optimization) trainer.

Combines SFT loss with an odds-ratio penalty on preference pairs.
Loss: -log(p_chosen) + λ * log(1 + odds_rejected / odds_chosen)
"""

from __future__ import annotations

import torch
import torch.nn.functional as F

from ..preference_trainer import PreferenceTrainer


class ORPOTrainer(PreferenceTrainer):
    """Odds Ratio Preference Optimization (reference-free)."""

    def preference_loss(
        self,
        policy_logps_chosen: torch.Tensor,
        policy_logps_rejected: torch.Tensor,
        ref_logps_chosen: torch.Tensor | None,
        ref_logps_rejected: torch.Tensor | None,
    ) -> torch.Tensor:
        lambda_weight = self.config.technique_args.get("lambda", 1.0)

        # SFT component: maximize log-prob of chosen
        sft_loss = -policy_logps_chosen.mean()

        # Odds ratio: odds = p / (1 - p), in log space
        log_odds_chosen = policy_logps_chosen - torch.log1p(-policy_logps_chosen.exp().clamp(max=1.0 - 1e-7))
        log_odds_rejected = policy_logps_rejected - torch.log1p(-policy_logps_rejected.exp().clamp(max=1.0 - 1e-7))

        # ORPO loss: -log_sigmoid(log_odds_chosen - log_odds_rejected)
        orpo_loss = -F.logsigmoid(log_odds_chosen - log_odds_rejected).mean()

        return sft_loss + lambda_weight * orpo_loss
