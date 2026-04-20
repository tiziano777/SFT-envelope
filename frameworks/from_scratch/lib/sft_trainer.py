"""SFT (Supervised Fine-Tuning) trainer: cross-entropy loss on next-token prediction.

This trainer is functional out of the box. Override collate_fn() for custom
data preprocessing or compute_loss() for custom loss functions.
"""

from __future__ import annotations

from typing import Any

import torch

from .base_trainer import BaseFromScratchTrainer, TrainerConfig


class SFTTrainer(BaseFromScratchTrainer):
    """Supervised fine-tuning with standard causal language model loss."""

    def __init__(
        self,
        model: torch.nn.Module,
        tokenizer: Any,
        config: TrainerConfig,
        train_dataset: Any,
        eval_dataset: Any | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model, tokenizer, config, train_dataset, eval_dataset, **kwargs)
        # Ensure tokenizer has a pad token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

    def compute_loss(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        """Standard causal LM cross-entropy loss with label shifting."""
        outputs = self.model(
            input_ids=batch["input_ids"],
            attention_mask=batch["attention_mask"],
            labels=batch["labels"],
        )
        return outputs.loss

    def collate_fn(self, examples: list[dict]) -> dict[str, torch.Tensor]:
        """Tokenize and pad examples for causal LM training.

        Expects each example to have a 'text' or 'prompt' field (or the field
        configured via dataset.text_field / dataset.prompt_field in the YAML).
        """
        texts = []
        for ex in examples:
            # Try common field names
            text = ex.get("text") or ex.get("prompt") or ex.get("content", "")
            if isinstance(text, list):
                # Chat format: list of messages
                text = self.tokenizer.apply_chat_template(text, tokenize=False, add_generation_prompt=False)
            texts.append(text)

        encodings = self.tokenizer(
            texts,
            max_length=self.config.max_seq_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        # Labels = input_ids with padding tokens set to -100
        labels = encodings["input_ids"].clone()
        labels[labels == self.tokenizer.pad_token_id] = -100

        return {
            "input_ids": encodings["input_ids"],
            "attention_mask": encodings["attention_mask"],
            "labels": labels,
        }
