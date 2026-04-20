"""DPO (Direct Preference Optimization) trainer.

Loss: -log_sigmoid(β * ((π_chosen - π_rejected) - (ref_chosen - ref_rejected)))
"""

from __future__ import annotations

import torch
import torch.nn.functional as F

from ..preference_trainer import PreferenceTrainer


class DPOTrainer(PreferenceTrainer):
    """Direct Preference Optimization."""

    def preference_loss(
        self,
        policy_logps_chosen: torch.Tensor,
        policy_logps_rejected: torch.Tensor,
        ref_logps_chosen: torch.Tensor | None,
        ref_logps_rejected: torch.Tensor | None,
    ) -> torch.Tensor:
        beta = self.config.technique_args.get("beta", 0.1)

        pi_diff = policy_logps_chosen - policy_logps_rejected

        ref_diff = torch.zeros_like(pi_diff)
        if ref_logps_chosen is not None and ref_logps_rejected is not None:
            ref_diff = ref_logps_chosen - ref_logps_rejected

        return -F.logsigmoid(beta * (pi_diff - ref_diff)).mean()
