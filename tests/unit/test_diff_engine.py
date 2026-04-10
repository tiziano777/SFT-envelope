"""Unit tests for envelope/middleware/shared/diff_engine.py -- git-style diff computation."""

from __future__ import annotations

from datetime import datetime, timezone

from envelope.middleware.shared.config_hasher import ConfigSnapshot
from envelope.middleware.shared.diff_engine import DiffEngine, DiffEntry


class TestDiffEntry:
    """DiffEntry instantiation and serialization."""

    def test_instantiation(self) -> None:
        entry = DiffEntry(line=5, type="added", content="  lr: 5e-5")
        assert entry.line == 5
        assert entry.type == "added"
        assert entry.content == "  lr: 5e-5"

    def test_model_dump(self) -> None:
        entry = DiffEntry(line=5, type="added", content="  lr: 5e-5")
        dumped = entry.model_dump()
        assert dumped == {"line": 5, "type": "added", "content": "  lr: 5e-5"}

    def test_serialization_roundtrip(self) -> None:
        entry = DiffEntry(line=10, type="removed", content="old line")
        json_str = entry.model_dump_json()
        restored = DiffEntry.model_validate_json(json_str)
        assert entry == restored


class TestComputeFileDiff:
    """Core diff logic tests."""

    def test_both_empty(self) -> None:
        result = DiffEngine.compute_file_diff("", "")
        assert result == []

    def test_identical(self) -> None:
        text = "line 1\nline 2\nline 3"
        result = DiffEngine.compute_file_diff(text, text)
        assert result == []

    def test_single_line_added(self) -> None:
        result = DiffEngine.compute_file_diff("", "new line")
        assert len(result) == 1
        assert result[0] == {"line": 1, "type": "added", "content": "new line"}

    def test_single_line_removed(self) -> None:
        result = DiffEngine.compute_file_diff("old line", "")
        assert len(result) == 1
        assert result[0] == {"line": 1, "type": "removed", "content": "old line"}

    def test_single_line_changed(self) -> None:
        result = DiffEngine.compute_file_diff("old", "new")
        assert len(result) == 2
        removed = [e for e in result if e["type"] == "removed"]
        added = [e for e in result if e["type"] == "added"]
        assert len(removed) == 1
        assert len(added) == 1
        assert removed[0]["content"] == "old"
        assert added[0]["content"] == "new"

    def test_multi_line_change_at_different_positions(self) -> None:
        old_text = "line 1\nline 2\nline 3\nline 4\nline 5"
        new_text = "line 1\nMODIFIED\nline 3\nline 4\nCHANGED"
        result = DiffEngine.compute_file_diff(old_text, new_text)
        # Should have changes at line 2 and line 5
        removed_lines = [e["line"] for e in result if e["type"] == "removed"]
        added_lines = [e["line"] for e in result if e["type"] == "added"]
        assert 2 in removed_lines
        assert 2 in added_lines
        assert 5 in removed_lines
        assert 5 in added_lines

    def test_at_header_without_count(self) -> None:
        """Test case that produces @@ -N +M @@ (count=1 omitted)."""
        old_text = "a\nb\nc"
        new_text = "a\nB\nc"
        result = DiffEngine.compute_file_diff(old_text, new_text)
        assert len(result) == 2  # one removed, one added
        removed = [e for e in result if e["type"] == "removed"]
        added = [e for e in result if e["type"] == "added"]
        assert removed[0]["content"] == "b"
        assert added[0]["content"] == "B"
        assert removed[0]["line"] == 2
        assert added[0]["line"] == 2


class TestComputeScaffoldDiff:
    """Integration-level diff with ConfigSnapshot objects."""

    @staticmethod
    def _make_snapshot(files: dict[str, str]) -> ConfigSnapshot:
        return ConfigSnapshot(
            snapshot_id="test",
            files=files,
            aggregated_hash="test",
            created_at=datetime.now(tz=timezone.utc),
        )

    def test_structure_keys(self) -> None:
        snap = self._make_snapshot({})
        result = DiffEngine.compute_scaffold_diff(snap, snap, {}, {})
        assert "config" in result
        assert "train" in result
        assert "requirements" in result
        assert "rewards" in result
        assert "hyperparams" in result

    def test_config_change(self) -> None:
        old_snap = self._make_snapshot({"config.yaml": "old_hash"})
        new_snap = self._make_snapshot({"config.yaml": "new_hash"})
        old_texts = {"config.yaml": "lr: 1e-4"}
        new_texts = {"config.yaml": "lr: 5e-5"}
        result = DiffEngine.compute_scaffold_diff(old_snap, new_snap, old_texts, new_texts)
        assert len(result["config"]) > 0

    def test_requirements_included(self) -> None:
        old_snap = self._make_snapshot({})
        new_snap = self._make_snapshot({})
        old_texts = {"requirements.txt": "torch>=2.0"}
        new_texts = {"requirements.txt": "torch>=2.1"}
        result = DiffEngine.compute_scaffold_diff(old_snap, new_snap, old_texts, new_texts)
        assert len(result["requirements"]) > 0

    def test_rewards_structure(self) -> None:
        old_snap = self._make_snapshot({})
        new_snap = self._make_snapshot({})
        old_texts = {"rewards/math_reward.py": "def old(): pass"}
        new_texts = {"rewards/math_reward.py": "def new(): pass"}
        result = DiffEngine.compute_scaffold_diff(old_snap, new_snap, old_texts, new_texts)
        rewards = result["rewards"]
        assert isinstance(rewards, dict)
        assert "math_reward.py" in rewards
        assert isinstance(rewards["math_reward.py"], list)

    def test_no_changes(self) -> None:
        snap = self._make_snapshot({"config.yaml": "hash1"})
        texts = {"config.yaml": "lr: 1e-4", "train.py": "import torch"}
        result = DiffEngine.compute_scaffold_diff(snap, snap, texts, texts)
        assert result["config"] == []
        assert result["train"] == []
        assert result["requirements"] == []
        assert result["hyperparams"] == []
        assert result["rewards"] == {}
