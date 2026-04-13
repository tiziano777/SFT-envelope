"""Tests for merge technique plugin."""

from __future__ import annotations

import pytest

from envelope.config.models import Stage
from envelope.registry import discover_plugins, technique_registry
from envelope.techniques.base import BaseTechnique

# Ensure all plugins are discovered before tests run
discover_plugins()


def _get_technique(name: str) -> BaseTechnique:
    cls = technique_registry.get(name)
    return cls()


class TestMergeRegistration:
    """Test merge technique registration."""

    def test_merge_is_registered(self):
        """Merge technique should be registered in the technique registry."""
        assert "merge" in technique_registry

    def test_merge_registry_returns_technique_class(self):
        """technique_registry.get('merge') should return MergeTechnique class."""
        cls = technique_registry.get("merge")
        assert issubclass(cls, BaseTechnique)

    def test_merge_instantiates_correctly(self):
        """MergeTechnique should instantiate without errors."""
        t = _get_technique("merge")
        assert t is not None


class TestMergeProperties:
    """Test merge technique properties."""

    def test_merge_name(self):
        """name property should return 'merge'."""
        t = _get_technique("merge")
        assert t.name == "merge"

    def test_merge_stage(self):
        """stage property should return Stage.MERGE."""
        t = _get_technique("merge")
        assert t.stage == Stage.MERGE

    def test_merge_display_name(self):
        """display_name property should return 'Model Merge'."""
        t = _get_technique("merge")
        assert t.display_name == "Model Merge"

    def test_merge_no_gpu_requirements(self):
        """Merge should not require GPU resources."""
        t = _get_technique("merge")
        assert t.requires_reference_model is False
        assert t.requires_reward is False
        assert t.requires_teacher_model is False


class TestMergeDefaults:
    """Test merge technique default arguments."""

    def test_default_technique_args_returns_dict(self):
        """default_technique_args() should return a dictionary."""
        t = _get_technique("merge")
        defaults = t.default_technique_args()
        assert isinstance(defaults, dict)

    def test_default_technique_args_has_merge_method(self):
        """default_technique_args() should include merge_method."""
        t = _get_technique("merge")
        defaults = t.default_technique_args()
        assert "merge_method" in defaults
        assert defaults["merge_method"] == "ties"

    def test_default_technique_args_has_weights(self):
        """default_technique_args() should include weights."""
        t = _get_technique("merge")
        defaults = t.default_technique_args()
        assert "weights" in defaults
        assert defaults["weights"] == [0.5, 0.5]


class TestMergeValidation:
    """Test merge technique argument validation."""

    def test_validate_invalid_merge_method(self):
        """Invalid merge_method should produce error."""
        t = _get_technique("merge")
        errors = t.validate_technique_args({"merge_method": "invalid"})
        assert len(errors) > 0
        assert "merge_method" in errors[0].lower()

    def test_validate_valid_merge_methods(self):
        """Valid merge methods should not produce errors."""
        t = _get_technique("merge")
        for method in ["ties", "cat", "slerp", "linear"]:
            errors = t.validate_technique_args({"merge_method": method})
            assert len(errors) == 0, f"Method {method} should be valid"

    def test_validate_invalid_weights_wrong_length(self):
        """Weights list with wrong length should produce error."""
        t = _get_technique("merge")
        errors = t.validate_technique_args({"weights": [0.3, 0.3, 0.4]})
        assert len(errors) > 0
        assert "weights" in errors[0].lower()

    def test_validate_invalid_weights_not_list(self):
        """Weights must be a list, not other type."""
        t = _get_technique("merge")
        errors = t.validate_technique_args({"weights": "0.5"})
        assert len(errors) > 0
        assert "weights" in errors[0].lower()

    def test_validate_valid_weights(self):
        """Valid weights should not produce error."""
        t = _get_technique("merge")
        errors = t.validate_technique_args({"weights": [0.3, 0.7]})
        assert len(errors) == 0

    def test_validate_defaults_are_valid(self):
        """Technique's own defaults should pass validation."""
        t = _get_technique("merge")
        defaults = t.default_technique_args()
        errors = t.validate_technique_args(defaults)
        assert errors == []

    def test_validate_empty_args_valid(self):
        """Empty args should be valid (all fields are optional)."""
        t = _get_technique("merge")
        errors = t.validate_technique_args({})
        assert errors == []


class TestMergeDatasetFields:
    """Test merge technique dataset fields."""

    def test_required_dataset_fields_empty(self):
        """Merge doesn't require any dataset fields (no training)."""
        t = _get_technique("merge")
        fields = t.required_dataset_fields()
        assert fields == []
