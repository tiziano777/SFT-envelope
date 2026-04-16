"""Scope enumeration for fine-tuning recipes."""

from enum import Enum


class ScopeEnum(str, Enum):
    """Valid scopes for fine-tuning recipes."""

    SFT = "sft"
    PREFERENCE = "preference"
    REWARD_MODEL = "reward_model"
    RL_POLICY = "rl_policy"
    CONTINUAL_FT = "continual_ft"
    PEFT = "peft"
    EVALUATION = "evaluation"
    BENCHMARK = "benchmark"
    UNKNOWN = "unknown"

    @classmethod
    def values(cls) -> list[str]:
        """Return list of all scope values."""
        return [scope.value for scope in cls]
