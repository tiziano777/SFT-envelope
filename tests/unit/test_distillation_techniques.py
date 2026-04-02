"""Unit tests for distillation technique plugins (gkd, sdft, sdpo, gold)."""

from __future__ import annotations

import pytest

from envelope.config.models import Stage
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


# ---------------------------------------------------------------------------
# Parametrized metadata checks
# ---------------------------------------------------------------------------

DISTILLATION_TECHNIQUES = [
    ("gkd", Stage.SFT, "Generalized Knowledge Distillation"),
    ("sdft", Stage.SFT, "Self-Distilled Fine-Tuning"),
    ("sdpo", Stage.RL, "Self-Distillation Policy Optimization"),
    ("gold", Stage.SFT, "General Online Logit Distillation"),
]

DISTILLATION_NAMES = [t[0] for t in DISTILLATION_TECHNIQUES]


class TestDistillationMetadata:
    @pytest.mark.parametrize("name,expected_stage,expected_display", DISTILLATION_TECHNIQUES)
    def test_name(self, name, expected_stage, expected_display):
        t = _get_technique(name)
        assert t.name == name

    @pytest.mark.parametrize("name,expected_stage,expected_display", DISTILLATION_TECHNIQUES)
    def test_stage(self, name, expected_stage, expected_display):
        t = _get_technique(name)
        assert t.stage == expected_stage

    @pytest.mark.parametrize("name,expected_stage,expected_display", DISTILLATION_TECHNIQUES)
    def test_display_name(self, name, expected_stage, expected_display):
        t = _get_technique(name)
        assert t.display_name == expected_display


# ---------------------------------------------------------------------------
# requires_teacher_model
# ---------------------------------------------------------------------------


class TestDistillationTeacherModel:
    def test_gkd_requires_teacher(self):
        t = _get_technique("gkd")
        assert t.requires_teacher_model is True

    def test_sdft_no_teacher(self):
        t = _get_technique("sdft")
        assert t.requires_teacher_model is False

    def test_gold_requires_teacher(self):
        t = _get_technique("gold")
        assert t.requires_teacher_model is True

    def test_sdpo_no_teacher(self):
        t = _get_technique("sdpo")
        assert t.requires_teacher_model is False


# ---------------------------------------------------------------------------
# requires_reward
# ---------------------------------------------------------------------------


class TestDistillationReward:
    def test_sdpo_requires_reward(self):
        t = _get_technique("sdpo")
        assert t.requires_reward is True

    @pytest.mark.parametrize("name", ["gkd", "sdft", "gold"])
    def test_no_reward(self, name):
        t = _get_technique(name)
        assert t.requires_reward is False


# ---------------------------------------------------------------------------
# default_technique_args
# ---------------------------------------------------------------------------


class TestDistillationDefaultArgs:
    @pytest.mark.parametrize("name", DISTILLATION_NAMES)
    def test_returns_non_empty_dict(self, name):
        t = _get_technique(name)
        defaults = t.default_technique_args()
        assert isinstance(defaults, dict)
        assert len(defaults) > 0

    def test_gkd_defaults(self):
        t = _get_technique("gkd")
        defaults = t.default_technique_args()
        assert "temperature" in defaults
        assert "lmbda" in defaults
        assert "beta" in defaults
        assert "max_new_tokens" in defaults
        assert "disable_dropout" in defaults

    def test_sdft_defaults(self):
        t = _get_technique("sdft")
        defaults = t.default_technique_args()
        assert "distillation_alpha" in defaults
        assert "distillation_topk" in defaults
        assert "max_completion_length" in defaults
        assert "disable_dropout" in defaults

    def test_sdpo_defaults(self):
        t = _get_technique("sdpo")
        defaults = t.default_technique_args()
        assert "distillation_topk" in defaults
        assert "full_logit_distillation" in defaults
        assert "max_completion_length" in defaults
        assert "num_generations" in defaults

    def test_gold_defaults(self):
        t = _get_technique("gold")
        defaults = t.default_technique_args()
        assert "temperature" in defaults
        assert "lmbda" in defaults
        assert "beta" in defaults
        assert "max_completion_length" in defaults
        assert "use_uld_loss" in defaults
        assert "disable_dropout" in defaults


# ---------------------------------------------------------------------------
# validate_technique_args -- invalid args
# ---------------------------------------------------------------------------


class TestDistillationValidation:
    # GKD validation
    def test_gkd_temperature_zero(self):
        t = _get_technique("gkd")
        errors = t.validate_technique_args({"temperature": 0.0})
        assert len(errors) == 1
        assert "temperature" in errors[0].lower()

    def test_gkd_temperature_negative(self):
        t = _get_technique("gkd")
        errors = t.validate_technique_args({"temperature": -1.0})
        assert len(errors) == 1

    def test_gkd_lmbda_negative(self):
        t = _get_technique("gkd")
        errors = t.validate_technique_args({"lmbda": -0.1})
        assert len(errors) == 1
        assert "lmbda" in errors[0].lower()

    def test_gkd_lmbda_over_one(self):
        t = _get_technique("gkd")
        errors = t.validate_technique_args({"lmbda": 1.5})
        assert len(errors) == 1

    def test_gkd_beta_negative(self):
        t = _get_technique("gkd")
        errors = t.validate_technique_args({"beta": -0.1})
        assert len(errors) == 1
        assert "beta" in errors[0].lower()

    def test_gkd_beta_over_one(self):
        t = _get_technique("gkd")
        errors = t.validate_technique_args({"beta": 1.5})
        assert len(errors) == 1

    def test_gkd_max_new_tokens_zero(self):
        t = _get_technique("gkd")
        errors = t.validate_technique_args({"max_new_tokens": 0})
        assert len(errors) == 1

    # SDFT validation
    def test_sdft_alpha_negative(self):
        t = _get_technique("sdft")
        errors = t.validate_technique_args({"distillation_alpha": -0.1})
        assert len(errors) == 1
        assert "distillation_alpha" in errors[0].lower()

    def test_sdft_alpha_over_one(self):
        t = _get_technique("sdft")
        errors = t.validate_technique_args({"distillation_alpha": 1.5})
        assert len(errors) == 1

    def test_sdft_topk_zero(self):
        t = _get_technique("sdft")
        errors = t.validate_technique_args({"distillation_topk": 0})
        assert len(errors) == 1
        assert "distillation_topk" in errors[0].lower()

    def test_sdft_max_completion_length_zero(self):
        t = _get_technique("sdft")
        errors = t.validate_technique_args({"max_completion_length": 0})
        assert len(errors) == 1

    # SDPO validation
    def test_sdpo_topk_zero(self):
        t = _get_technique("sdpo")
        errors = t.validate_technique_args({"distillation_topk": 0})
        assert len(errors) == 1
        assert "distillation_topk" in errors[0].lower()

    def test_sdpo_max_completion_length_zero(self):
        t = _get_technique("sdpo")
        errors = t.validate_technique_args({"max_completion_length": 0})
        assert len(errors) == 1

    def test_sdpo_num_generations_one(self):
        t = _get_technique("sdpo")
        errors = t.validate_technique_args({"num_generations": 1})
        assert len(errors) == 1
        assert "num_generations" in errors[0].lower()

    # GOLD validation
    def test_gold_temperature_zero(self):
        t = _get_technique("gold")
        errors = t.validate_technique_args({"temperature": 0.0})
        assert len(errors) == 1
        assert "temperature" in errors[0].lower()

    def test_gold_temperature_negative(self):
        t = _get_technique("gold")
        errors = t.validate_technique_args({"temperature": -1.0})
        assert len(errors) == 1

    def test_gold_lmbda_negative(self):
        t = _get_technique("gold")
        errors = t.validate_technique_args({"lmbda": -0.1})
        assert len(errors) == 1
        assert "lmbda" in errors[0].lower()

    def test_gold_lmbda_over_one(self):
        t = _get_technique("gold")
        errors = t.validate_technique_args({"lmbda": 1.5})
        assert len(errors) == 1

    def test_gold_beta_negative(self):
        t = _get_technique("gold")
        errors = t.validate_technique_args({"beta": -0.1})
        assert len(errors) == 1
        assert "beta" in errors[0].lower()

    def test_gold_beta_over_one(self):
        t = _get_technique("gold")
        errors = t.validate_technique_args({"beta": 1.5})
        assert len(errors) == 1

    def test_gold_max_completion_length_zero(self):
        t = _get_technique("gold")
        errors = t.validate_technique_args({"max_completion_length": 0})
        assert len(errors) == 1

    # All defaults pass validation
    @pytest.mark.parametrize("name", DISTILLATION_NAMES)
    def test_default_args_valid(self, name):
        """Each technique's own defaults should pass validation."""
        t = _get_technique(name)
        defaults = t.default_technique_args()
        errors = t.validate_technique_args(defaults)
        assert errors == []

    @pytest.mark.parametrize("name", DISTILLATION_NAMES)
    def test_empty_args_valid(self, name):
        """Empty args should be valid (all fields are optional checks)."""
        t = _get_technique(name)
        errors = t.validate_technique_args({})
        assert errors == []


# ---------------------------------------------------------------------------
# required_dataset_fields
# ---------------------------------------------------------------------------


class TestDistillationDatasetFields:
    @pytest.mark.parametrize("name", DISTILLATION_NAMES)
    def test_requires_prompt(self, name):
        t = _get_technique(name)
        assert "prompt" in t.required_dataset_fields()


# ---------------------------------------------------------------------------
# Registry discovery
# ---------------------------------------------------------------------------


class TestDistillationRegistry:
    @pytest.mark.parametrize("name", DISTILLATION_NAMES)
    def test_discovered(self, name):
        assert name in technique_registry

    @pytest.mark.parametrize("name", DISTILLATION_NAMES)
    def test_get_returns_class(self, name):
        cls = technique_registry.get(name)
        assert issubclass(cls, BaseTechnique)
