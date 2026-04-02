"""Preference trainer base: ABC for DPO, SimPO, KTO, ORPO, etc.

Manages reference model, computes per-token log-probabilities for
chosen/rejected pairs, and delegates to abstract preference_loss().
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F

from .base_trainer import BaseFromScratchTrainer, TrainerConfig


class PreferenceTrainer(BaseFromScratchTrainer):
    """Abstract base for preference-based alignment techniques.

    Subclasses implement preference_loss() with their specific loss formula.
    """

    def __init__(
        self,
        model: nn.Module,
        tokenizer: Any,
        config: TrainerConfig,
        train_dataset: Any,
        eval_dataset: Any | None = None,
        ref_model: nn.Module | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model, tokenizer, config, train_dataset, eval_dataset, **kwargs)
        self.ref_model = ref_model
        if self.ref_model is not None:
            self.ref_model.to(self.device)
            self.ref_model.eval()
            for param in self.ref_model.parameters():
                param.requires_grad = False

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

    @abstractmethod
    def preference_loss(
        self,
        policy_logps_chosen: torch.Tensor,
        policy_logps_rejected: torch.Tensor,
        ref_logps_chosen: torch.Tensor | None,
        ref_logps_rejected: torch.Tensor | None,
    ) -> torch.Tensor:
        """Compute the preference alignment loss.

        Args:
            policy_logps_chosen: Sum of log-probs for chosen responses under the policy. Shape (B,).
            policy_logps_rejected: Sum of log-probs for rejected responses under the policy. Shape (B,).
            ref_logps_chosen: Sum of log-probs for chosen under reference model. Shape (B,) or None.
            ref_logps_rejected: Sum of log-probs for rejected under reference. Shape (B,) or None.

        Returns:
            Scalar loss tensor.
        """

    def compute_loss(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        """Compute preference loss over chosen/rejected pairs."""
        # Policy log-probs
        policy_logps_chosen = self._compute_logprobs(
            self.model, batch["chosen_input_ids"], batch["chosen_attention_mask"], batch["chosen_labels"]
        )
        policy_logps_rejected = self._compute_logprobs(
            self.model, batch["rejected_input_ids"], batch["rejected_attention_mask"], batch["rejected_labels"]
        )

        # Reference log-probs
        ref_logps_chosen = None
        ref_logps_rejected = None
        if self.ref_model is not None:
            with torch.no_grad():
                ref_logps_chosen = self._compute_logprobs(
                    self.ref_model, batch["chosen_input_ids"], batch["chosen_attention_mask"], batch["chosen_labels"]
                )
                ref_logps_rejected = self._compute_logprobs(
                    self.ref_model, batch["rejected_input_ids"], batch["rejected_attention_mask"], batch["rejected_labels"]
                )

        return self.preference_loss(
            policy_logps_chosen, policy_logps_rejected, ref_logps_chosen, ref_logps_rejected
        )

    def _compute_logprobs(
        self,
        model: nn.Module,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        labels: torch.Tensor,
    ) -> torch.Tensor:
        """Compute sum of per-token log-probabilities for the labeled tokens.

        Returns shape (B,) — one scalar per example in the batch.
        """
        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        logits = outputs.logits[:, :-1, :]  # Shift: predict next token
        target = labels[:, 1:]  # Shift: target is next token

        log_probs = F.log_softmax(logits, dim=-1)
        token_logps = log_probs.gather(dim=-1, index=target.unsqueeze(-1)).squeeze(-1)

        # Mask out padding (-100)
        mask = target != -100
        token_logps = token_logps * mask.float()

        return token_logps.sum(dim=-1)  # (B,)

    def collate_fn(self, examples: list[dict]) -> dict[str, torch.Tensor]:
        """Tokenize chosen and rejected pairs.

        Expects each example to have 'chosen' and 'rejected' fields (text or chat messages),
        and optionally a 'prompt' field.
        """
        chosen_texts = []
        rejected_texts = []

        for ex in examples:
            prompt = ex.get("prompt", "")
            chosen = ex.get("chosen", "")
            rejected = ex.get("rejected", "")

            # Handle chat format (list of messages)
            if isinstance(chosen, list):
                chosen = self.tokenizer.apply_chat_template(chosen, tokenize=False)
            elif prompt:
                chosen = prompt + chosen

            if isinstance(rejected, list):
                rejected = self.tokenizer.apply_chat_template(rejected, tokenize=False)
            elif prompt:
                rejected = prompt + rejected

            chosen_texts.append(chosen)
            rejected_texts.append(rejected)

        chosen_enc = self.tokenizer(
            chosen_texts, max_length=self.config.max_seq_length, padding="max_length", truncation=True, return_tensors="pt"
        )
        rejected_enc = self.tokenizer(
            rejected_texts, max_length=self.config.max_seq_length, padding="max_length", truncation=True, return_tensors="pt"
        )

        # Labels with -100 for padding
        chosen_labels = chosen_enc["input_ids"].clone()
        chosen_labels[chosen_labels == self.tokenizer.pad_token_id] = -100

        rejected_labels = rejected_enc["input_ids"].clone()
        rejected_labels[rejected_labels == self.tokenizer.pad_token_id] = -100

        return {
            "chosen_input_ids": chosen_enc["input_ids"],
            "chosen_attention_mask": chosen_enc["attention_mask"],
            "chosen_labels": chosen_labels,
            "rejected_input_ids": rejected_enc["input_ids"],
            "rejected_attention_mask": rejected_enc["attention_mask"],
            "rejected_labels": rejected_labels,
        }
