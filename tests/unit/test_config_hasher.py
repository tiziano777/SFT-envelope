"""Unit tests for envelope/middleware/shared/config_hasher.py -- deterministic hashing."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from envelope.middleware.shared.config_hasher import ConfigHasher, ConfigSnapshot


class TestConfigSnapshot:
    """ConfigSnapshot instantiation and serialization."""

    def test_instantiation(self) -> None:
        now = datetime.now(tz=timezone.utc)
        snap = ConfigSnapshot(
            snapshot_id="abc",
            files={"config.yaml": "hash1"},
            aggregated_hash="abc",
            created_at=now,
        )
        assert snap.snapshot_id == "abc"
        assert snap.files == {"config.yaml": "hash1"}
        assert snap.aggregated_hash == "abc"
        assert snap.created_at == now

    def test_snapshot_id_equals_aggregated_hash(self) -> None:
        now = datetime.now(tz=timezone.utc)
        snap = ConfigSnapshot(
            snapshot_id="xyz",
            files={},
            aggregated_hash="xyz",
            created_at=now,
        )
        assert snap.snapshot_id == snap.aggregated_hash

    def test_serialization_roundtrip(self) -> None:
        now = datetime.now(tz=timezone.utc)
        snap = ConfigSnapshot(
            snapshot_id="abc",
            files={"config.yaml": "hash1", "train.py": "hash2"},
            aggregated_hash="abc",
            created_at=now,
        )
        json_str = snap.model_dump_json()
        restored = ConfigSnapshot.model_validate_json(json_str)
        assert snap == restored


class TestHashYamlContent:
    """YAML normalization: key order, anchors, empty YAML."""

    def test_key_order_irrelevant(self) -> None:
        yaml_v1 = b"b: 2\na: 1\n"
        yaml_v2 = b"a: 1\nb: 2\n"
        assert ConfigHasher._hash_yaml_content(yaml_v1) == ConfigHasher._hash_yaml_content(yaml_v2)

    def test_yaml_anchors_resolved(self) -> None:
        with_anchors = b"x: &anchor 1\ny: *anchor\n"
        without_anchors = b"x: 1\ny: 1\n"
        assert ConfigHasher._hash_yaml_content(with_anchors) == ConfigHasher._hash_yaml_content(without_anchors)

    def test_empty_yaml(self) -> None:
        result = ConfigHasher._hash_yaml_content(b"")
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex length


class TestHashPythonContent:
    """Python file normalization: line endings, trailing whitespace."""

    def test_line_ending_normalization(self) -> None:
        with_crlf = b"import torch\r\n"
        with_lf = b"import torch\n"
        assert ConfigHasher._hash_python_content(with_crlf) == ConfigHasher._hash_python_content(with_lf)

    def test_trailing_whitespace_stripped(self) -> None:
        with_trailing = b"x = 1   \n"
        without_trailing = b"x = 1\n"
        assert ConfigHasher._hash_python_content(with_trailing) == ConfigHasher._hash_python_content(without_trailing)


class TestHashFile:
    """hash_file dispatches to YAML or Python hashing based on extension."""

    def test_yaml_file(self, tmp_path: pytest.TempPathFactory) -> None:
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_bytes(b"a: 1\nb: 2\n")
        result = ConfigHasher.hash_file(yaml_file)
        expected = ConfigHasher._hash_yaml_content(b"a: 1\nb: 2\n")
        assert result == expected

    def test_yml_extension(self, tmp_path: pytest.TempPathFactory) -> None:
        yml_file = tmp_path / "config.yml"
        yml_file.write_bytes(b"x: 10\n")
        result = ConfigHasher.hash_file(yml_file)
        expected = ConfigHasher._hash_yaml_content(b"x: 10\n")
        assert result == expected

    def test_python_file(self, tmp_path: pytest.TempPathFactory) -> None:
        py_file = tmp_path / "train.py"
        py_file.write_bytes(b"import torch\n")
        result = ConfigHasher.hash_file(py_file)
        expected = ConfigHasher._hash_python_content(b"import torch\n")
        assert result == expected


class TestHashConfig:
    """Full scaffold hashing with tmp_path fixtures."""

    def _make_scaffold(self, tmp_path, *, with_rewards: bool = True, with_requirements: bool = False) -> None:
        (tmp_path / "config.yaml").write_bytes(b"lr: 1e-4\nbatch_size: 8\n")
        (tmp_path / "train.py").write_bytes(b"import torch\nprint('train')\n")
        if with_requirements:
            (tmp_path / "requirements.txt").write_bytes(b"torch>=2.0\n")
        if with_rewards:
            rewards_dir = tmp_path / "rewards"
            rewards_dir.mkdir()
            (rewards_dir / "math_reward.py").write_bytes(b"def reward(): return 1.0\n")

    def test_scaffold_with_rewards(self, tmp_path: pytest.TempPathFactory) -> None:
        self._make_scaffold(tmp_path, with_rewards=True)
        snapshot = ConfigHasher.hash_config(tmp_path)
        assert len(snapshot.files) == 3
        assert "config.yaml" in snapshot.files
        assert "train.py" in snapshot.files
        assert "rewards/math_reward.py" in snapshot.files

    def test_requirements_excluded_from_hash(self, tmp_path: pytest.TempPathFactory) -> None:
        self._make_scaffold(tmp_path, with_rewards=True, with_requirements=True)
        snapshot = ConfigHasher.hash_config(tmp_path)
        assert "requirements.txt" not in snapshot.files

    def test_empty_rewards_dir(self, tmp_path: pytest.TempPathFactory) -> None:
        self._make_scaffold(tmp_path, with_rewards=False)
        rewards_dir = tmp_path / "rewards"
        rewards_dir.mkdir()
        snapshot = ConfigHasher.hash_config(tmp_path)
        assert len(snapshot.files) == 2
        assert "config.yaml" in snapshot.files
        assert "train.py" in snapshot.files

    def test_missing_rewards_dir(self, tmp_path: pytest.TempPathFactory) -> None:
        self._make_scaffold(tmp_path, with_rewards=False)
        snapshot = ConfigHasher.hash_config(tmp_path)
        assert len(snapshot.files) == 2

    def test_deterministic_hash(self, tmp_path: pytest.TempPathFactory) -> None:
        self._make_scaffold(tmp_path, with_rewards=True)
        snap1 = ConfigHasher.hash_config(tmp_path)
        snap2 = ConfigHasher.hash_config(tmp_path)
        assert snap1.aggregated_hash == snap2.aggregated_hash

    def test_files_sorted_by_relative_path(self, tmp_path: pytest.TempPathFactory) -> None:
        self._make_scaffold(tmp_path, with_rewards=True)
        rewards_dir = tmp_path / "rewards"
        (rewards_dir / "z_reward.py").write_bytes(b"def z(): return 0\n")
        (rewards_dir / "a_reward.py").write_bytes(b"def a(): return 0\n")
        snapshot = ConfigHasher.hash_config(tmp_path)
        paths = list(snapshot.files.keys())
        assert paths == sorted(paths)


class TestDiffSnapshots:
    """Snapshot comparison."""

    def _make_snapshot(self, files: dict[str, str]) -> ConfigSnapshot:
        now = datetime.now(tz=timezone.utc)
        agg = "agg_hash"
        return ConfigSnapshot(
            snapshot_id=agg,
            files=files,
            aggregated_hash=agg,
            created_at=now,
        )

    def test_identical_snapshots(self) -> None:
        snap = self._make_snapshot({"config.yaml": "hash1", "train.py": "hash2"})
        result = ConfigHasher.diff_snapshots(snap, snap)
        assert result == {}

    def test_changed_file(self) -> None:
        old = self._make_snapshot({"config.yaml": "old_hash"})
        new = self._make_snapshot({"config.yaml": "new_hash"})
        result = ConfigHasher.diff_snapshots(old, new)
        assert result == {"config.yaml": ("old_hash", "new_hash")}

    def test_added_file(self) -> None:
        old = self._make_snapshot({"config.yaml": "hash1"})
        new = self._make_snapshot({"config.yaml": "hash1", "rewards/new.py": "new_hash"})
        result = ConfigHasher.diff_snapshots(old, new)
        assert result == {"rewards/new.py": (None, "new_hash")}

    def test_removed_file(self) -> None:
        old = self._make_snapshot({"config.yaml": "hash1", "rewards/old.py": "old_hash"})
        new = self._make_snapshot({"config.yaml": "hash1"})
        result = ConfigHasher.diff_snapshots(old, new)
        assert result == {"rewards/old.py": ("old_hash", None)}
