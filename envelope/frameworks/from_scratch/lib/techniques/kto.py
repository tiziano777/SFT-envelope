"""KTO (Kahneman-Tversky Optimization) trainer.

Separate losses for desirable and undesirable examples, weighted by
a prospect-theory-inspired loss function.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F

from ..preference_trainer import PreferenceTrainer


class KTOTrainer(PreferenceTrainer):
    """Kahneman-Tversky Optimization with asymmetric desirable/undesirable losses."""

    def preference_loss(
        self,
        policy_logps_chosen: torch.Tensor,
        policy_logps_rejected: torch.Tensor,
        ref_logps_chosen: torch.Tensor | None,
        ref_logps_rejected: torch.Tensor | None,
    ) -> torch.Tensor:
        beta = self.config.technique_args.get("beta", 0.1)
        desirable_weight = self.config.technique_args.get("desirable_weight", 1.0)
        undesirable_weight = self.config.technique_args.get("undesirable_weight", 1.0)

        # KL from reference
        ref_chosen = ref_logps_chosen if ref_logps_chosen is not None else torch.zeros_like(policy_logps_chosen)
        ref_rejected = ref_logps_rejected if ref_logps_rejected is not None else torch.zeros_like(policy_logps_rejected)

        chosen_kl = policy_logps_chosen - ref_chosen
        rejected_kl = policy_logps_rejected - ref_rejected

        # KTO implicit KL baseline
        kl_baseline = (chosen_kl.mean() + rejected_kl.mean()) / 2.0

        # Desirable loss: 1 - sigmoid(β * (chosen_kl - baseline))
        desirable_loss = 1.0 - F.sigmoid(beta * (chosen_kl - kl_baseline))

        # Undesirable loss: 1 - sigmoid(β * (baseline - rejected_kl))
        undesirable_loss = 1.0 - F.sigmoid(beta * (kl_baseline - rejected_kl))

        loss = desirable_weight * desirable_loss.mean() + undesirable_weight * undesirable_loss.mean()
        return loss
