"""Centralized default values for envelope configuration.

These defaults are used when a YAML field is omitted. They are also referenced
by the auto-optimizer to suggest hardware-aware overrides.
"""

from __future__ import annotations

# Hyperparameter defaults — injected into generated train.py
# and overridable at runtime via HPARAM_* environment variables.
HYPERPARAMETER_DEFAULTS: dict[str, int | float | str] = {
    "learning_rate": 1e-5,
    "per_device_train_batch_size": 2,
    "warmup_ratio": 0.1,
    "weight_decay": 0.01,
    "num_train_epochs": 3,
    "gradient_accumulation_steps": 4,
    "lr_scheduler_type": "cosine",
    "max_grad_norm": 1.0,
}

# Default technique_args per technique
TECHNIQUE_DEFAULTS: dict[str, dict[str, int | float | str | bool]] = {
    "sft": {},
    "dpo": {
        "beta": 0.1,
        "dpo_variant": "standard",
    },
    "simpo": {
        "beta": 2.0,
        "gamma": 1.0,
    },
    "kto": {
        "lambda_w": 1.0,
        "lambda_l": 1.33,
    },
    "orpo": {
        "lambda_or": 1.0,
    },
    "ppo": {
        "clip_range": 0.2,
        "gae_lambda": 0.95,
        "vf_coef": 0.5,
        "num_generations": 8,
        "max_completion_length": 256,
    },
    "grpo": {
        "num_generations": 16,
        "max_completion_length": 512,
        "epsilon": 0.2,
        "beta": 0.04,
        "temperature": 1.0,
        "num_iterations": 1,
        "scale_rewards": "group",
    },
    "dapo": {
        "num_generations": 16,
        "max_completion_length": 512,
        "epsilon_low": 0.2,
        "epsilon_high": 0.28,
        "beta": 0.0,
        "temperature": 1.0,
        "dynamic_sampling": True,
        "overlong_filtering": True,
        "token_level_pg": True,
    },
    "vapo": {
        "num_generations": 16,
        "max_completion_length": 512,
        "epsilon": 0.2,
        "beta": 0.04,
        "critic_lambda": 0.5,
        "critic_hidden_size": 256,
    },
    "rloo": {
        "num_generations": 8,
        "max_completion_length": 256,
    },
    "reinforce_pp": {
        "clip_range": 0.2,
        "beta": 0.01,
        "max_completion_length": 256,
    },
    "dr_grpo": {
        "num_generations": 16,
        "max_completion_length": 512,
        "epsilon": 0.2,
        "beta": 0.04,
        "bessel_correction": True,
        "length_correction": True,
    },
    "flowrl": {
        "num_generations": 16,
        "max_completion_length": 512,
        "beta_flow": 1.0,
    },
    "prime": {
        "num_generations": 16,
        "max_completion_length": 512,
        "epsilon": 0.2,
        "beta": 0.04,
        "alpha_process": 0.1,
    },
    # Distillation techniques
    "gkd": {
        "temperature": 0.9,
        "lmbda": 0.5,
        "beta": 0.5,
        "max_new_tokens": 128,
        "disable_dropout": True,
    },
    "sdft": {
        "distillation_alpha": 0.5,
        "distillation_topk": 5,
        "max_completion_length": 64,
        "disable_dropout": True,
    },
    "sdpo": {
        "distillation_topk": 100,
        "full_logit_distillation": True,
        "max_completion_length": 512,
        "num_generations": 16,
    },
    "gold": {
        "temperature": 0.9,
        "lmbda": 0.5,
        "beta": 0.5,
        "max_completion_length": 128,
        "use_uld_loss": False,
        "disable_dropout": True,
    },
    # Reward modeling
    "reward_modeling": {
        "center_rewards_coefficient": 0.0,
    },
}
