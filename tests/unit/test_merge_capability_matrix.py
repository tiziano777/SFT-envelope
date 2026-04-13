"""Tests for merge technique in capability matrix."""

from __future__ import annotations

import pytest

from envelope.frameworks.capability_matrix import (
    get_compatible_frameworks,
    get_compatible_techniques,
    is_compatible,
)


class TestMergeCapabilityMatrix:
    """Test merge technique compatibility in capability matrix."""

    def test_merge_from_scratch_compatible(self):
        """merge should be compatible with from_scratch framework."""
        assert is_compatible("merge", "from_scratch") is True

    def test_merge_trl_incompatible(self):
        """merge should NOT be compatible with trl framework."""
        assert is_compatible("merge", "trl") is False

    def test_merge_unsloth_incompatible(self):
        """merge should NOT be compatible with unsloth framework."""
        assert is_compatible("merge", "unsloth") is False

    def test_merge_axolotl_incompatible(self):
        """merge should NOT be compatible with axolotl framework."""
        assert is_compatible("merge", "axolotl") is False

    def test_merge_torchtune_incompatible(self):
        """merge should NOT be compatible with torchtune framework."""
        assert is_compatible("merge", "torchtune") is False

    def test_merge_verl_incompatible(self):
        """merge should NOT be compatible with verl framework."""
        assert is_compatible("merge", "verl") is False

    def test_merge_openrlhf_incompatible(self):
        """merge should NOT be compatible with openrlhf framework."""
        assert is_compatible("merge", "openrlhf") is False

    def test_merge_llamafactory_incompatible(self):
        """merge should NOT be compatible with llamafactory framework."""
        assert is_compatible("merge", "llamafactory") is False

    def test_merge_nemo_incompatible(self):
        """merge should NOT be compatible with nemo framework."""
        assert is_compatible("merge", "nemo") is False

    def test_get_compatible_frameworks_merge(self):
        """get_compatible_frameworks('merge') should return ['from_scratch']."""
        frameworks = get_compatible_frameworks("merge")
        assert frameworks == ["from_scratch"]

    def test_get_compatible_techniques_from_scratch_includes_merge(self):
        """Merge should appear in techniques compatible with from_scratch."""
        techniques = get_compatible_techniques("from_scratch")
        assert "merge" in techniques

    def test_merge_is_only_from_scratch_technique(self):
        """Merge should only be in from_scratch compatible techniques."""
        frameworks = get_compatible_frameworks("merge")
        assert len(frameworks) == 1
        assert frameworks[0] == "from_scratch"
