"""Unit tests for envelope/middleware/shared/relations.py."""

from __future__ import annotations

import pytest

from envelope.middleware.shared.relations import DerivedFromRel, RelationType


# ---------------------------------------------------------------------------
# RelationType Enum
# ---------------------------------------------------------------------------


class TestRelationType:
    """Validate RelationType enum members and values."""

    def test_member_count(self) -> None:
        assert len(RelationType) == 8

    @pytest.mark.parametrize(
        "member,value",
        [
            (RelationType.USED_FOR, "USED_FOR"),
            (RelationType.SELECTED_FOR, "SELECTED_FOR"),
            (RelationType.BASED_ON, "BASED_ON"),
            (RelationType.PRODUCED, "PRODUCED"),
            (RelationType.DERIVED_FROM, "DERIVED_FROM"),
            (RelationType.STARTED_FROM, "STARTED_FROM"),
            (RelationType.RETRY_OF, "RETRY_OF"),
            (RelationType.MERGED_FROM, "MERGED_FROM"),
        ],
    )
    def test_member_values(self, member: RelationType, value: str) -> None:
        assert member.value == value

    def test_all_values_are_strings(self) -> None:
        for member in RelationType:
            assert isinstance(member.value, str)

    def test_all_values_upper_case(self) -> None:
        for member in RelationType:
            assert member.value == member.value.upper()


# ---------------------------------------------------------------------------
# DerivedFromRel
# ---------------------------------------------------------------------------


class TestDerivedFromRel:
    """Validate DerivedFromRel model."""

    def test_instantiation(self) -> None:
        rel = DerivedFromRel(
            source_exp_id="e1",
            target_exp_id="e2",
            diff_patch={"config": []},
        )
        assert rel.source_exp_id == "e1"
        assert rel.target_exp_id == "e2"
        assert rel.diff_patch == {"config": []}

    def test_default_diff_patch(self) -> None:
        rel = DerivedFromRel(source_exp_id="e1", target_exp_id="e2")
        assert rel.diff_patch == {}

    def test_roundtrip_serialization(self) -> None:
        rel = DerivedFromRel(
            source_exp_id="e1",
            target_exp_id="e2",
            diff_patch={"config": [{"line": 5, "type": "removed", "content": "lr: 1e-4"}]},
        )
        json_str = rel.model_dump_json()
        restored = DerivedFromRel.model_validate_json(json_str)
        assert rel == restored

    def test_complex_diff_patch(self) -> None:
        """Diff patch with config list + rewards dict per Pitfall 7."""
        diff_patch = {
            "config": [
                {"line": 5, "type": "removed", "content": "  lr: 1e-4"},
                {"line": 5, "type": "added", "content": "  lr: 5e-5"},
            ],
            "train": [
                {"line": 47, "type": "removed", "content": "    optimizer = AdamW(lr=1e-4)"},
                {"line": 47, "type": "added", "content": "    optimizer = AdamW(lr=5e-5)"},
            ],
            "requirements": [
                {"line": 8, "type": "added", "content": "mergekit==0.0.5"},
            ],
            "rewards": {
                "math_reward.py": [
                    {"line": 23, "type": "removed", "content": "    return score * 0.8"},
                    {"line": 23, "type": "added", "content": "    return score * 1.0"},
                ],
                "format_reward.py": [],
            },
        }
        rel = DerivedFromRel(
            source_exp_id="e1",
            target_exp_id="e2",
            diff_patch=diff_patch,
        )
        json_str = rel.model_dump_json()
        restored = DerivedFromRel.model_validate_json(json_str)
        assert restored.diff_patch == diff_patch

    def test_source_exp_id_required(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DerivedFromRel(source_exp_id="", target_exp_id="e2")

    def test_target_exp_id_required(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DerivedFromRel(source_exp_id="e1", target_exp_id="")
