"""Unit tests for the reward_modeling technique plugin."""

from __future__ import annotations

from envelope.config.models import (
    EnvelopeConfig,
    REFERENCE_FREE_TECHNIQUES,
    Stage,
    Technique,
)
from envelope.config.validators import validate_config
from envelope.frameworks.capability_matrix import is_compatible, get_compatible_frameworks
from envelope.registry import discover_plugins, technique_registry
from envelope.techniques.base import BaseTechnique

# Ensure all plugins are registered before tests run
discover_plugins()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_technique(name: str) -> BaseTechnique:
    cls = technique_registry.get(name)
    return cls()


def _make_config(**overrides) -> EnvelopeConfig:
    """Build a minimal valid EnvelopeConfig with optional overrides."""
    base = {
        "experiment": {"name": "val-test"},
        "model": {"name_or_path": "meta-llama/Llama-3.1-8B"},
        "dataset": {"train_uri": "tatsu-lab/alpaca"},
    }
    base.update(overrides)
    return EnvelopeConfig.model_validate(base)


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestRewardModelingMetadata:
    def test_name(self):
        t = _get_technique("reward_modeling")
        assert t.name == "reward_modeling"

    def test_stage(self):
        t = _get_technique("reward_modeling")
        assert t.stage == Stage.PREFERENCE

    def test_display_name(self):
        t = _get_technique("reward_modeling")
        assert t.display_name == "Reward Model Training"

    def test_requires_reward(self):
        t = _get_technique("reward_modeling")
        assert t.requires_reward is False

    def test_requires_teacher_model(self):
        t = _get_technique("reward_modeling")
        assert t.requires_teacher_model is False

    def test_requires_reference_model(self):
        t = _get_technique("reward_modeling")
        assert t.requires_reference_model is False


# ---------------------------------------------------------------------------
# default_technique_args
# ---------------------------------------------------------------------------


class TestRewardModelingDefaultArgs:
    def test_returns_dict(self):
        t = _get_technique("reward_modeling")
        defaults = t.default_technique_args()
        assert isinstance(defaults, dict)

    def test_has_center_rewards_coefficient(self):
        t = _get_technique("reward_modeling")
        defaults = t.default_technique_args()
        assert "center_rewards_coefficient" in defaults


# ---------------------------------------------------------------------------
# validate_technique_args
# ---------------------------------------------------------------------------


class TestRewardModelingValidation:
    def test_negative_coefficient_errors(self):
        t = _get_technique("reward_modeling")
        errors = t.validate_technique_args({"center_rewards_coefficient": -1.0})
        assert len(errors) == 1
        assert "center_rewards_coefficient" in errors[0].lower()

    def test_defaults_pass_validation(self):
        t = _get_technique("reward_modeling")
        defaults = t.default_technique_args()
        errors = t.validate_technique_args(defaults)
        assert errors == []

    def test_empty_args_valid(self):
        t = _get_technique("reward_modeling")
        errors = t.validate_technique_args({})
        assert errors == []


# ---------------------------------------------------------------------------
# required_dataset_fields
# ---------------------------------------------------------------------------


class TestRewardModelingDatasetFields:
    def test_requires_prompt(self):
        t = _get_technique("reward_modeling")
        fields = t.required_dataset_fields()
        assert "prompt" in fields

    def test_requires_chosen(self):
        t = _get_technique("reward_modeling")
        fields = t.required_dataset_fields()
        assert "chosen" in fields

    def test_requires_rejected(self):
        t = _get_technique("reward_modeling")
        fields = t.required_dataset_fields()
        assert "rejected" in fields


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRewardModelingRegistry:
    def test_discovered(self):
        assert "reward_modeling" in technique_registry

    def test_get_returns_class(self):
        cls = technique_registry.get("reward_modeling")
        assert issubclass(cls, BaseTechnique)


# ---------------------------------------------------------------------------
# Capability matrix
# ---------------------------------------------------------------------------


class TestRewardModelingCapability:
    def test_compatible_with_trl(self):
        assert is_compatible("reward_modeling", "trl") is True

    def test_not_compatible_with_unsloth(self):
        assert is_compatible("reward_modeling", "unsloth") is False

    def test_compatible_frameworks(self):
        frameworks = get_compatible_frameworks("reward_modeling")
        assert frameworks == ["trl"]


# ---------------------------------------------------------------------------
# Config integration
# ---------------------------------------------------------------------------


class TestRewardModelingConfig:
    def test_stage_is_preference(self):
        config = _make_config(
            training={"technique": "reward_modeling"},
            framework={"backend": "trl"},
            dataset={
                "train_uri": "ds",
                "chosen_field": "chosen",
                "rejected_field": "rejected",
            },
        )
        assert config.training.stage == Stage.PREFERENCE

    def test_is_reference_free(self):
        assert Technique.REWARD_MODELING in REFERENCE_FREE_TECHNIQUES

    def test_preference_dataset_requires_chosen_rejected(self):
        """reward_modeling without chosen/rejected fields should produce validation error."""
        config = _make_config(
            training={"technique": "reward_modeling"},
            framework={"backend": "trl"},
            dataset={
                "train_uri": "ds",
                "chosen_field": "",
                "rejected_field": "",
            },
        )
        errors = validate_config(config)
        pref_errors = [e for e in errors if "preference" in e.lower() or "chosen" in e.lower()]
        assert len(pref_errors) > 0

    def test_preference_dataset_with_fields_ok(self):
        """reward_modeling with chosen/rejected fields should pass preference validation."""
        config = _make_config(
            training={"technique": "reward_modeling"},
            framework={"backend": "trl"},
            dataset={
                "train_uri": "ds",
                "chosen_field": "chosen",
                "rejected_field": "rejected",
            },
        )
        errors = validate_config(config)
        pref_errors = [e for e in errors if "preference" in e.lower()]
        assert len(pref_errors) == 0
