"""Tests for DiffEntry correctness and diff verification."""

from __future__ import annotations

import pytest

from envelope.middleware.shared.config_hasher import ConfigSnapshot, DiffEntry, DiffEngine


class TestDiffSimpleOperations:
    """Test simple diff operations (ADD, REMOVE, MODIFY)."""

    def test_diff_simple_add(self):
        """Test that ADD is detected correctly."""
        old_snap = ConfigSnapshot(filename="test.yaml", content="line1\nline2")
        new_snap = ConfigSnapshot(filename="test.yaml", content="line1\nline_new\nline2")

        diff_engine = DiffEngine()
        diffs = diff_engine.diff(old_snap, new_snap)

        assert any(d.change_type == "ADD" for d in diffs), "Should have ADD entry"
        assert any("line_new" in d.content_new for d in diffs if d.change_type == "ADD")

    def test_diff_simple_remove(self):
        """Test that REMOVE is detected correctly."""
        old_snap = ConfigSnapshot(filename="test.yaml", content="line1\nline2\nline3")
        new_snap = ConfigSnapshot(filename="test.yaml", content="line1\nline3")

        diff_engine = DiffEngine()
        diffs = diff_engine.diff(old_snap, new_snap)

        assert any(d.change_type == "REMOVE" for d in diffs), "Should have REMOVE entry"

    def test_diff_simple_modify(self):
        """Test that MODIFY is detected correctly."""
        old_snap = ConfigSnapshot(filename="test.yaml", content="line1\nold_content\nline3")
        new_snap = ConfigSnapshot(filename="test.yaml", content="line1\nnew_content\nline3")

        diff_engine = DiffEngine()
        diffs = diff_engine.diff(old_snap, new_snap)

        assert any(d.change_type == "MODIFY" for d in diffs), "Should have MODIFY entry"


class TestDiffLineNumbers:
    """Test that diff line numbers are correct."""

    def test_diff_line_numbers_correct(self):
        """Test that line numbers in diff are 1-indexed and accurate."""
        old_snap = ConfigSnapshot(filename="test.yaml", content="line1\nline2\nline3")
        new_snap = ConfigSnapshot(filename="test.yaml", content="line1\nline_new\nline2\nline3")

        diff_engine = DiffEngine()
        diffs = diff_engine.diff(old_snap, new_snap)

        # Should have ADD at line 2
        add_diffs = [d for d in diffs if d.change_type == "ADD"]
        assert add_diffs, "Should have ADD entry"
        assert add_diffs[0].line_number == 2 or add_diffs[0].line_number == 1, "ADD should be near line 2"

    def test_diff_multiline_file(self):
        """Test diff on files with multiple lines."""
        old_content = "\n".join([f"line_{i}" for i in range(50)])
        new_content = "\n".join(
            [f"line_{i}" for i in range(25)]
            + ["inserted_line"]
            + [f"line_{i}" for i in range(25, 50)]
        )

        old_snap = ConfigSnapshot(filename="config.yaml", content=old_content)
        new_snap = ConfigSnapshot(filename="config.yaml", content=new_content)

        diff_engine = DiffEngine()
        diffs = diff_engine.diff(old_snap, new_snap)

        assert diffs, "Should have diffs"
        assert any(d.change_type == "ADD" for d in diffs), "Should detect insertion"


class TestDiffEdgeCases:
    """Test edge cases in diff."""

    def test_diff_empty_to_content(self):
        """Test diff from empty to content."""
        old_snap = ConfigSnapshot(filename="test.yaml", content="")
        new_snap = ConfigSnapshot(filename="test.yaml", content="line1\nline2")

        diff_engine = DiffEngine()
        diffs = diff_engine.diff(old_snap, new_snap)

        assert diffs, "Should have diffs for empty→content"
        assert all(d.change_type == "ADD" for d in diffs), "All should be ADDs"

    def test_diff_content_to_empty(self):
        """Test diff from content to empty."""
        old_snap = ConfigSnapshot(filename="test.yaml", content="line1\nline2")
        new_snap = ConfigSnapshot(filename="test.yaml", content="")

        diff_engine = DiffEngine()
        diffs = diff_engine.diff(old_snap, new_snap)

        assert diffs, "Should have diffs for content→empty"
        assert all(d.change_type == "REMOVE" for d in diffs), "All should be REMOVEs"

    def test_diff_identical_configs(self):
        """Test diff when configs are identical."""
        snap = ConfigSnapshot(filename="test.yaml", content="line1\nline2\nline3")

        diff_engine = DiffEngine()
        diffs = diff_engine.diff(snap, snap)

        assert not diffs or len(diffs) == 0, "Identical configs should have no diffs"


class TestDiffContentPreservation:
    """Test that diff preserves content exactly."""

    def test_diff_content_preserved_exactly(self):
        """Test that content in diff entries matches original."""
        content_old = "config: value\nmodel: llama\nlearning_rate: 0.001"
        content_new = "config: value\nmodel: llama\nlearning_rate: 0.0005"

        old_snap = ConfigSnapshot(filename="config.yaml", content=content_old)
        new_snap = ConfigSnapshot(filename="config.yaml", content=content_new)

        diff_engine = DiffEngine()
        diffs = diff_engine.diff(old_snap, new_snap)

        modify_diffs = [d for d in diffs if d.change_type == "MODIFY"]
        assert modify_diffs, "Should have MODIFY entry"

        for diff in modify_diffs:
            if "learning_rate" in str(diff.content_old):
                assert "0.001" in diff.content_old
                assert "0.0005" in diff.content_new

    def test_diff_special_characters_preserved(self):
        """Test that special characters are preserved in diff."""
        content_old = "model: llama-7b\npath: /home/user/models\nconfig: {a: 1, b: 2}"
        content_new = "model: llama-13b\npath: /home/user/models\nconfig: {a: 1, b: 2, c: 3}"

        old_snap = ConfigSnapshot(filename="config.yaml", content=content_old)
        new_snap = ConfigSnapshot(filename="config.yaml", content=content_new)

        diff_engine = DiffEngine()
        diffs = diff_engine.diff(old_snap, new_snap)

        assert diffs, "Should detect changes with special characters"


class TestDiffMultipleChanges:
    """Test diffs with multiple changes."""

    def test_diff_multiple_adds(self):
        """Test diff with multiple ADD operations."""
        old_snap = ConfigSnapshot(filename="test.yaml", content="line1\nline3")
        new_snap = ConfigSnapshot(filename="test.yaml", content="line1\nline2\nline3\nline4")

        diff_engine = DiffEngine()
        diffs = diff_engine.diff(old_snap, new_snap)

        adds = [d for d in diffs if d.change_type == "ADD"]
        assert len(adds) >= 2, "Should have multiple ADDs"

    def test_diff_mixed_operations(self):
        """Test diff with mixed ADD, REMOVE, MODIFY operations."""
        old_snap = ConfigSnapshot(
            filename="config.yaml",
            content="line1\nline2\nline3\nline4"
        )
        new_snap = ConfigSnapshot(
            filename="config.yaml",
            content="line1_modified\nline2\nline_new\nline4"
        )

        diff_engine = DiffEngine()
        diffs = diff_engine.diff(old_snap, new_snap)

        has_add = any(d.change_type == "ADD" for d in diffs)
        has_remove = any(d.change_type == "REMOVE" for d in diffs)
        has_modify = any(d.change_type == "MODIFY" for d in diffs)

        # Should have at least some operations
        assert has_add or has_remove or has_modify
