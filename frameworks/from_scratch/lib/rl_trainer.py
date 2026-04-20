"""RL trainer base: ABC for GRPO, PPO, DAPO, RLOO, etc.

Manages generation, reward scoring, and advantage estimation.
Subclasses implement compute_advantages() and policy_loss().
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Callable

import torch
import torch.nn as nn
import torch.nn.functional as F

from .base_trainer import BaseFromScratchTrainer, TrainerConfig


class RLTrainer(BaseFromScratchTrainer):
    """Abstract base for reinforcement learning alignment techniques.

    Subclasses implement:
        - compute_advantages(rewards, ...) -> advantages tensor
        - policy_loss(logprobs, old_logprobs, advantages) -> scalar loss
    """

    def __init__(
        self,
        model: nn.Module,
        tokenizer: Any,
        config: TrainerConfig,
        train_dataset: Any,
        eval_dataset: Any | None = None,
        reward_fns: list[Callable] | None = None,
        ref_model: nn.Module | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model, tokenizer, config, train_dataset, eval_dataset, **kwargs)
        self.reward_fns = reward_fns or []
        self.ref_model = ref_model
        if self.ref_model is not None:
            self.ref_model.to(self.device)
            self.ref_model.eval()
            for param in self.ref_model.parameters():
                param.requires_grad = False

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        self._technique_args = config.technique_args

    @abstractmethod
    def compute_advantages(
        self,
        rewards: torch.Tensor,
        **kwargs: Any,
    ) -> torch.Tensor:
        """Compute advantages from reward scores.

        Args:
            rewards: Reward scores. Shape depends on technique (e.g., (B,) or (B, G)).
            **kwargs: Additional context (e.g., values for GAE, old_logprobs for baselines).

        Returns:
            Advantages tensor, same shape as rewards.
        """

    @abstractmethod
    def policy_loss(
        self,
        logprobs: torch.Tensor,
        old_logprobs: torch.Tensor,
        advantages: torch.Tensor,
    ) -> torch.Tensor:
        """Compute the policy gradient loss.

        Args:
            logprobs: Log-probabilities under current policy. Shape (B,) or (B, G).
            old_logprobs: Log-probabilities under the old (generating) policy.
            advantages: Advantage estimates.

        Returns:
            Scalar loss tensor.
        """

    def compute_loss(self, batch: dict[str, torch.Tensor]) -> torch.Tensor:
        """RL training step: generate, score, compute advantages, return policy loss.

        This orchestrates the full RL inner loop. Override for custom flows.
        """
        prompts = batch.get("prompts", [])
        num_generations = self._technique_args.get("num_generations", 4)
        max_completion_length = self._technique_args.get("max_completion_length", 512)
        temperature = self._technique_args.get("temperature", 1.0)

        # Generate completions
        completions, old_logprobs = self._generate_with_logprobs(
            prompts, num_generations=num_generations,
            max_new_tokens=max_completion_length, temperature=temperature,
        )

        # Score with reward functions
        rewards = self._score_completions(prompts, completions, num_generations)

        # Compute advantages
        advantages = self.compute_advantages(rewards)

        # Compute current log-probs
        current_logprobs = self._recompute_logprobs(prompts, completions)

        # Policy loss
        return self.policy_loss(current_logprobs, old_logprobs, advantages)

    def _generate_with_logprobs(
        self,
        prompts: list[str],
        num_generations: int = 4,
        max_new_tokens: int = 512,
        temperature: float = 1.0,
    ) -> tuple[list[str], torch.Tensor]:
        """Generate completions and collect their log-probabilities.

        Returns:
            completions: List of generated text strings (B * num_generations).
            logprobs: Sum of per-token log-probs, shape (B * num_generations,).
        """
        all_completions: list[str] = []
        all_logprobs: list[torch.Tensor] = []

        self.model.eval()
        with torch.no_grad():
            for prompt in prompts:
                for _ in range(num_generations):
                    inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=self.config.max_seq_length)
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    prompt_len = inputs["input_ids"].shape[1]

                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=max_new_tokens,
                        temperature=temperature,
                        do_sample=True,
                        return_dict_in_generate=True,
                        output_scores=True,
                    )

                    generated_ids = outputs.sequences[0, prompt_len:]
                    completion_text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
                    all_completions.append(completion_text)

                    # Compute log-probs from scores
                    if outputs.scores:
                        token_logprobs = []
                        for i, score in enumerate(outputs.scores):
                            lp = F.log_softmax(score[0] / temperature, dim=-1)
                            if i < len(generated_ids):
                                token_logprobs.append(lp[generated_ids[i]])
                        all_logprobs.append(torch.stack(token_logprobs).sum())
                    else:
                        all_logprobs.append(torch.tensor(0.0, device=self.device))

        self.model.train()
        logprobs_tensor = torch.stack(all_logprobs)
        return all_completions, logprobs_tensor

    def _score_completions(
        self,
        prompts: list[str],
        completions: list[str],
        num_generations: int,
    ) -> torch.Tensor:
        """Score completions using reward functions.

        Returns:
            Rewards tensor of shape (B * num_generations,).
        """
        if not self.reward_fns:
            return torch.zeros(len(completions), device=self.device)

        total_rewards = torch.zeros(len(completions), device=self.device)
        # Expand prompts to match completions: each prompt repeated num_generations times
        expanded_prompts = []
        for p in prompts:
            expanded_prompts.extend([p] * num_generations)

        for reward_fn in self.reward_fns:
            scores = reward_fn(completions, prompts=expanded_prompts)
            if isinstance(scores, list):
                scores = torch.tensor(scores, dtype=torch.float32, device=self.device)
            total_rewards += scores

        return total_rewards

    def _recompute_logprobs(
        self,
        prompts: list[str],
        completions: list[str],
    ) -> torch.Tensor:
        """Recompute log-probs for completions under the current policy.

        Returns:
            Log-probs tensor of shape (len(completions),).
        """
        logprobs_list: list[torch.Tensor] = []

        for prompt, completion in zip(prompts * (len(completions) // max(len(prompts), 1)), completions):
            full_text = prompt + completion
            inputs = self.tokenizer(full_text, return_tensors="pt", truncation=True, max_length=self.config.max_seq_length)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            prompt_enc = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=self.config.max_seq_length)
            prompt_len = prompt_enc["input_ids"].shape[1]

            outputs = self.model(**inputs)
            logits = outputs.logits[0, prompt_len - 1:-1, :]
            target = inputs["input_ids"][0, prompt_len:]

            if logits.shape[0] == 0 or target.shape[0] == 0:
                logprobs_list.append(torch.tensor(0.0, device=self.device))
                continue

            log_probs = F.log_softmax(logits, dim=-1)
            min_len = min(log_probs.shape[0], target.shape[0])
            token_lp = log_probs[:min_len].gather(dim=-1, index=target[:min_len].unsqueeze(-1)).squeeze(-1)
            logprobs_list.append(token_lp.sum())

        return torch.stack(logprobs_list)

    def collate_fn(self, examples: list[dict]) -> dict[str, Any]:
        """Collate for RL: just extract prompts as text.

        The actual tokenization happens during generation in compute_loss().
        """
        prompts = [ex.get("prompt", ex.get("text", "")) for ex in examples]
        return {"prompts": prompts}

    def _compute_kl_penalty(
        self,
        logprobs: torch.Tensor,
        ref_logprobs: torch.Tensor,
    ) -> torch.Tensor:
        """Compute KL divergence penalty: log(π/π_ref) = logprobs - ref_logprobs."""
        return logprobs - ref_logprobs
