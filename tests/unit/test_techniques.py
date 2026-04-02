"""Unit tests for technique plugins in envelope/techniques/."""

from __future__ import annotations

import pytest

from envelope.config.models import Stage
from envelope.registry import discover_plugins, technique_registry
from envelope.techniques.base import BaseTechnique

# Ensure all plugins are registered before tests run
discover_plugins()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _get_technique(name: str) -> BaseTechnique:
    cls = technique_registry.get(name)
    return cls()


# ---------------------------------------------------------------------------
# Parametrized metadata checks
# ---------------------------------------------------------------------------

ALL_TECHNIQUES = [
    ("sft", Stage.SFT, "Supervised Fine-Tuning"),
    ("dpo", Stage.PREFERENCE, "Direct Preference Optimization"),
    ("simpo", Stage.PREFERENCE, "Simple Preference Optimization"),
    ("kto", Stage.PREFERENCE, "Kahneman-Tversky Optimization"),
    ("orpo", Stage.PREFERENCE, "Odds Ratio Preference Optimization"),
    ("ppo", Stage.RL, "Proximal Policy Optimization"),
    ("grpo", Stage.RL, "Group Relative Policy Optimization"),
    ("dapo", Stage.RL, "Decoupled Alignment via Policy Optimization"),
    ("vapo", Stage.RL, "Value-Augmented Policy Optimization"),
    ("rloo", Stage.RL, "REINFORCE Leave-One-Out"),
    ("reinforce_pp", Stage.RL, "REINFORCE++"),
    ("dr_grpo", Stage.RL, "Dr. GRPO (Bias-Corrected)"),
    ("flowrl", Stage.RL, "FlowRL (Distribution Matching)"),
    ("prime", Stage.RL, "PRIME (Process Implicit Rewards)"),
    ("gkd", Stage.SFT, "Generalized Knowledge Distillation"),
    ("sdft", Stage.SFT, "Self-Distilled Fine-Tuning"),
    ("sdpo", Stage.RL, "Self-Distillation Policy Optimization"),
    ("gold", Stage.SFT, "General Online Logit Distillation"),
    ("reward_modeling", Stage.PREFERENCE, "Reward Model Training"),
]

ALL_TECHNIQUE_NAMES = [t[0] for t in ALL_TECHNIQUES]


class TestTechniqueMetadata:
    @pytest.mark.parametrize("name,expected_stage,expected_display", ALL_TECHNIQUES)
    def test_name(self, name, expected_stage, expected_display):
        t = _get_technique(name)
        assert t.name == name

    @pytest.mark.parametrize("name,expected_stage,expected_display", ALL_TECHNIQUES)
    def test_stage(self, name, expected_stage, expected_display):
        t = _get_technique(name)
        assert t.stage == expected_stage

    @pytest.mark.parametrize("name,expected_stage,expected_display", ALL_TECHNIQUES)
    def test_display_name(self, name, expected_stage, expected_display):
        t = _get_technique(name)
        assert t.display_name == expected_display


# ---------------------------------------------------------------------------
# default_technique_args
# ---------------------------------------------------------------------------


class TestDefaultTechniqueArgs:
    @pytest.mark.parametrize("name", ALL_TECHNIQUE_NAMES)
    def test_returns_dict(self, name):
        t = _get_technique(name)
        result = t.default_technique_args()
        assert isinstance(result, dict)

    def test_sft_defaults_empty(self):
        t = _get_technique("sft")
        assert t.default_technique_args() == {}

    def test_grpo_defaults_non_empty(self):
        t = _get_technique("grpo")
        defaults = t.default_technique_args()
        assert "num_generations" in defaults
        assert "beta" in defaults
        assert "epsilon" in defaults
        assert defaults["num_generations"] == 16

    def test_dpo_defaults(self):
        t = _get_technique("dpo")
        defaults = t.default_technique_args()
        assert "beta" in defaults
        assert defaults["beta"] == 0.1

    def test_dapo_defaults(self):
        t = _get_technique("dapo")
        defaults = t.default_technique_args()
        assert "epsilon_low" in defaults
        assert "epsilon_high" in defaults
        assert defaults["dynamic_sampling"] is True

    def test_ppo_defaults(self):
        t = _get_technique("ppo")
        defaults = t.default_technique_args()
        assert "clip_range" in defaults
        assert "gae_lambda" in defaults
        assert "vf_coef" in defaults


# ---------------------------------------------------------------------------
# validate_technique_args -- valid args
# ---------------------------------------------------------------------------


class TestValidateTechniqueArgsValid:
    @pytest.mark.parametrize("name", ALL_TECHNIQUE_NAMES)
    def test_default_args_valid(self, name):
        """Each technique's own defaults should pass validation."""
        t = _get_technique(name)
        defaults = t.default_technique_args()
        errors = t.validate_technique_args(defaults)
        assert errors == []

    @pytest.mark.parametrize("name", ALL_TECHNIQUE_NAMES)
    def test_empty_args_valid(self, name):
        """Empty args should be valid (all fields are optional checks)."""
        t = _get_technique(name)
        errors = t.validate_technique_args({})
        assert errors == []


# ---------------------------------------------------------------------------
# validate_technique_args -- invalid args
# ---------------------------------------------------------------------------


class TestValidateTechniqueArgsInvalid:
    def test_grpo_negative_beta(self):
        t = _get_technique("grpo")
        errors = t.validate_technique_args({"beta": -1.0})
        assert len(errors) == 1
        assert "beta" in errors[0].lower()

    def test_grpo_zero_temperature(self):
        t = _get_technique("grpo")
        errors = t.validate_technique_args({"temperature": 0.0})
        assert len(errors) == 1
        assert "temperature" in errors[0].lower()

    def test_grpo_epsilon_out_of_range(self):
        t = _get_technique("grpo")
        errors = t.validate_technique_args({"epsilon": 1.5})
        assert len(errors) == 1
        assert "epsilon" in errors[0].lower()

    def test_grpo_num_generations_too_small(self):
        t = _get_technique("grpo")
        errors = t.validate_technique_args({"num_generations": 1})
        assert len(errors) == 1

    def test_dpo_negative_beta(self):
        t = _get_technique("dpo")
        errors = t.validate_technique_args({"beta": -0.5})
        assert len(errors) == 1
        assert "beta" in errors[0].lower()

    def test_dpo_invalid_variant(self):
        t = _get_technique("dpo")
        errors = t.validate_technique_args({"dpo_variant": "invalid"})
        assert len(errors) == 1
        assert "variant" in errors[0].lower()

    def test_simpo_negative_beta(self):
        t = _get_technique("simpo")
        errors = t.validate_technique_args({"beta": -1.0})
        assert len(errors) == 1

    def test_simpo_negative_gamma(self):
        t = _get_technique("simpo")
        errors = t.validate_technique_args({"gamma": -0.5})
        assert len(errors) == 1

    def test_kto_negative_lambda_w(self):
        t = _get_technique("kto")
        errors = t.validate_technique_args({"lambda_w": -1.0})
        assert len(errors) == 1

    def test_kto_negative_lambda_l(self):
        t = _get_technique("kto")
        errors = t.validate_technique_args({"lambda_l": -1.0})
        assert len(errors) == 1

    def test_orpo_negative_lambda_or(self):
        t = _get_technique("orpo")
        errors = t.validate_technique_args({"lambda_or": 0.0})
        assert len(errors) == 1

    def test_ppo_clip_range_out_of_range(self):
        t = _get_technique("ppo")
        errors = t.validate_technique_args({"clip_range": 1.5})
        assert len(errors) == 1

    def test_ppo_negative_vf_coef(self):
        t = _get_technique("ppo")
        errors = t.validate_technique_args({"vf_coef": -0.1})
        assert len(errors) == 1

    def test_dapo_epsilon_low_gte_epsilon_high(self):
        t = _get_technique("dapo")
        errors = t.validate_technique_args({"epsilon_low": 0.3, "epsilon_high": 0.2})
        assert any("epsilon_low" in e for e in errors)

    def test_dapo_negative_temperature(self):
        t = _get_technique("dapo")
        errors = t.validate_technique_args({"temperature": -1.0})
        assert len(errors) == 1

    def test_vapo_epsilon_out_of_range(self):
        t = _get_technique("vapo")
        errors = t.validate_technique_args({"epsilon": 2.0})
        assert len(errors) == 1

    def test_vapo_critic_lambda_out_of_range(self):
        t = _get_technique("vapo")
        errors = t.validate_technique_args({"critic_lambda": 1.5})
        assert len(errors) == 1

    def test_rloo_num_generations_too_small(self):
        t = _get_technique("rloo")
        errors = t.validate_technique_args({"num_generations": 0})
        assert len(errors) == 1

    def test_reinforce_pp_clip_range_out_of_range(self):
        t = _get_technique("reinforce_pp")
        errors = t.validate_technique_args({"clip_range": 0.0})
        assert len(errors) == 1

    def test_reinforce_pp_negative_beta(self):
        t = _get_technique("reinforce_pp")
        errors = t.validate_technique_args({"beta": -1.0})
        assert len(errors) == 1

    def test_dr_grpo_negative_beta(self):
        t = _get_technique("dr_grpo")
        errors = t.validate_technique_args({"beta": -0.01})
        assert len(errors) == 1

    def test_dr_grpo_epsilon_out_of_range(self):
        t = _get_technique("dr_grpo")
        errors = t.validate_technique_args({"epsilon": 0.0})
        assert len(errors) == 1

    def test_flowrl_negative_beta_flow(self):
        t = _get_technique("flowrl")
        errors = t.validate_technique_args({"beta_flow": 0.0})
        assert len(errors) == 1

    def test_prime_alpha_process_out_of_range(self):
        t = _get_technique("prime")
        errors = t.validate_technique_args({"alpha_process": 1.5})
        assert len(errors) == 1

    def test_prime_negative_beta(self):
        t = _get_technique("prime")
        errors = t.validate_technique_args({"beta": -0.01})
        assert len(errors) == 1

    def test_multiple_errors(self):
        """Passing multiple invalid args should produce multiple errors."""
        t = _get_technique("grpo")
        errors = t.validate_technique_args({
            "beta": -1.0,
            "epsilon": 2.0,
            "temperature": 0.0,
            "num_generations": 0,
        })
        assert len(errors) == 4


# ---------------------------------------------------------------------------
# required_dataset_fields
# ---------------------------------------------------------------------------


class TestRequiredDatasetFields:
    @pytest.mark.parametrize("name", ALL_TECHNIQUE_NAMES)
    def test_returns_non_empty_list(self, name):
        t = _get_technique(name)
        fields = t.required_dataset_fields()
        assert isinstance(fields, list)
        assert len(fields) >= 1

    def test_sft_needs_prompt(self):
        t = _get_technique("sft")
        assert "prompt" in t.required_dataset_fields()

    def test_dpo_needs_chosen_rejected(self):
        t = _get_technique("dpo")
        fields = t.required_dataset_fields()
        assert "chosen" in fields
        assert "rejected" in fields

    def test_kto_needs_label(self):
        t = _get_technique("kto")
        fields = t.required_dataset_fields()
        assert "label" in fields

    def test_grpo_needs_prompt(self):
        t = _get_technique("grpo")
        assert "prompt" in t.required_dataset_fields()


# ---------------------------------------------------------------------------
# requires_reward / requires_reference_model
# ---------------------------------------------------------------------------


REWARD_REQUIRED = {"grpo", "dapo", "vapo", "ppo", "rloo", "reinforce_pp", "dr_grpo", "flowrl", "prime", "sdpo"}
REFERENCE_REQUIRED = {"dpo", "ppo", "kto"}


class TestRequiresFlags:
    @pytest.mark.parametrize("name", ALL_TECHNIQUE_NAMES)
    def test_requires_reward(self, name):
        t = _get_technique(name)
        if name in REWARD_REQUIRED:
            assert t.requires_reward is True, f"{name} should require reward"
        else:
            assert t.requires_reward is False, f"{name} should NOT require reward"

    @pytest.mark.parametrize("name", ALL_TECHNIQUE_NAMES)
    def test_requires_reference_model(self, name):
        t = _get_technique(name)
        if name in REFERENCE_REQUIRED:
            assert t.requires_reference_model is True, f"{name} should require reference model"
        else:
            assert t.requires_reference_model is False, f"{name} should NOT require reference model"
