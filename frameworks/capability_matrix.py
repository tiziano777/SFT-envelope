"""Compatibility matrix: which technique×framework combinations are supported.

Returns True if the combination is known to work, False if known to not work,
or raises if the combination has not been tested.
"""

from __future__ import annotations

# (technique, framework) -> supported
_MATRIX: dict[tuple[str, str], bool] = {
    # SFT
    ("sft", "trl"): True,
    ("sft", "unsloth"): True,
    ("sft", "axolotl"): True,
    ("sft", "torchtune"): True,
    ("sft", "verl"): False,
    ("sft", "openrlhf"): True,
    ("sft", "llamafactory"): True,
    ("sft", "nemo"): True,
    # DPO
    ("dpo", "trl"): True,
    ("dpo", "unsloth"): True,
    ("dpo", "axolotl"): True,
    ("dpo", "torchtune"): True,
    ("dpo", "llamafactory"): True,
    ("dpo", "openrlhf"): True,
    ("dpo", "nemo"): True,
    # SimPO
    ("simpo", "trl"): True,
    ("simpo", "unsloth"): True,
    # KTO
    ("kto", "trl"): True,
    ("kto", "llamafactory"): True,
    # ORPO
    ("orpo", "trl"): True,
    ("orpo", "unsloth"): True,
    ("orpo", "llamafactory"): True,
    # GRPO
    ("grpo", "trl"): True,
    ("grpo", "unsloth"): True,
    ("grpo", "verl"): True,
    ("grpo", "openrlhf"): True,
    # PPO
    ("ppo", "trl"): True,
    ("ppo", "verl"): True,
    ("ppo", "openrlhf"): True,
    ("ppo", "nemo"): True,
    # DAPO — veRL only
    ("dapo", "verl"): True,
    # VAPO — veRL only
    ("vapo", "verl"): True,
    # RLOO
    ("rloo", "trl"): True,
    ("rloo", "openrlhf"): True,
    # REINFORCE++
    ("reinforce_pp", "openrlhf"): True,
    ("reinforce_pp", "verl"): True,
    # Dr. GRPO
    ("dr_grpo", "verl"): True,
    # FlowRL
    ("flowrl", "verl"): True,
    # PRIME
    ("prime", "verl"): True,
    # Distillation — TRL only
    ("gkd", "trl"): True,
    ("sdft", "trl"): True,
    ("sdpo", "trl"): True,
    ("gold", "trl"): True,
    # Reward modeling — TRL only
    ("reward_modeling", "trl"): True,
    # Merge — no-GPU, compatible with from_scratch only
    ("merge", "from_scratch"): True,
    # from_scratch — supports ALL techniques
    ("sft", "from_scratch"): True,
    ("dpo", "from_scratch"): True,
    ("simpo", "from_scratch"): True,
    ("kto", "from_scratch"): True,
    ("orpo", "from_scratch"): True,
    ("grpo", "from_scratch"): True,
    ("ppo", "from_scratch"): True,
    ("dapo", "from_scratch"): True,
    ("vapo", "from_scratch"): True,
    ("rloo", "from_scratch"): True,
    ("reinforce_pp", "from_scratch"): True,
    ("dr_grpo", "from_scratch"): True,
    ("flowrl", "from_scratch"): True,
    ("prime", "from_scratch"): True,
}


def is_compatible(technique: str, framework: str) -> bool:
    """Check if a technique×framework combination is supported."""
    return _MATRIX.get((technique, framework), False)


def get_compatible_frameworks(technique: str) -> list[str]:
    """Return all frameworks compatible with a given technique."""
    return sorted({fw for (tech, fw), ok in _MATRIX.items() if tech == technique and ok})


def get_compatible_techniques(framework: str) -> list[str]:
    """Return all techniques compatible with a given framework."""
    return sorted({tech for (tech, fw), ok in _MATRIX.items() if fw == framework and ok})


def check_or_raise(technique: str, framework: str) -> None:
    """Raise ValueError if the combination is not supported."""
    if not is_compatible(technique, framework):
        compatible = get_compatible_frameworks(technique)
        raise ValueError(
            f"Framework '{framework}' does not support technique '{technique}'. "
            f"Compatible frameworks for '{technique}': {compatible}"
        )


# ─── Infrastructure capability matrix ───
# (capability, framework) -> support level
# Levels: "native" (built-in, first-class), "full" (via config/wrapper),
#          "partial" (limited), "none" (not supported), "internal" (handled internally)
_INFRA_MATRIX: dict[tuple[str, str], str] = {
    # FSDP
    ("fsdp", "trl"): "full",
    ("fsdp", "unsloth"): "none",
    ("fsdp", "axolotl"): "full",
    ("fsdp", "torchtune"): "internal",
    ("fsdp", "verl"): "internal",
    ("fsdp", "openrlhf"): "none",
    ("fsdp", "llamafactory"): "full",
    ("fsdp", "from_scratch"): "full",
    # Triton
    ("triton", "trl"): "partial",
    ("triton", "unsloth"): "native",
    ("triton", "axolotl"): "partial",
    ("triton", "torchtune"): "native",
    ("triton", "verl"): "partial",
    ("triton", "openrlhf"): "partial",
    ("triton", "llamafactory"): "partial",
    ("triton", "from_scratch"): "native",
    # SkyPilot
    ("skypilot", "trl"): "full",
    ("skypilot", "unsloth"): "full",
    ("skypilot", "axolotl"): "full",
    ("skypilot", "torchtune"): "full",
    ("skypilot", "verl"): "partial",
    ("skypilot", "openrlhf"): "full",
    ("skypilot", "llamafactory"): "full",
    ("skypilot", "from_scratch"): "full",
}


def get_infra_support(capability: str, framework: str) -> str:
    """Get infrastructure support level for a (capability, framework) pair.

    Returns: "native", "full", "partial", "none", "internal", or "unknown".
    """
    return _INFRA_MATRIX.get((capability, framework), "unknown")


def get_fsdp_frameworks() -> list[str]:
    """Return frameworks that support FSDP (full or native level)."""
    return sorted({fw for (cap, fw), level in _INFRA_MATRIX.items() if cap == "fsdp" and level in ("full", "native")})

