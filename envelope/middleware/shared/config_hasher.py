"""Deterministic config hashing and snapshot management for lineage tracking."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


# --- ConfigSnapshot ---


class ConfigSnapshot(BaseModel):
    """Serializable hash manifest for a scaffold directory snapshot."""

    snapshot_id: str = Field(..., description="Equal to aggregated_hash, deterministic")
    files: dict[str, str] = Field(
        default_factory=dict,
        description="{relative_path: sha256_hash}",
    )
    aggregated_hash: str = Field(
        ...,
        description="SHA256 of sorted concatenated file hashes",
    )
    created_at: datetime


# --- ConfigHasher ---


class ConfigHasher:
    """Static utility for deterministic SHA256 hashing of scaffold trigger files.

    Trigger files determine whether a new experiment (NEW strategy) or a branch
    (BRANCH strategy) should be created. requirements.txt is intentionally
    excluded from trigger hashing per SHRD-09 but included in textual diffs.
    """

    TRIGGER_FILES: list[str] = ["config.yaml", "train.py"]
    TRIGGER_DIRS: list[str] = ["rewards"]

    @staticmethod
    def _hash_yaml_content(content: bytes) -> str:
        """Parse YAML, normalize to sorted JSON, then SHA256 (D-03)."""
        data = yaml.safe_load(content)
        if data is None:
            normalized = ""
        else:
            normalized = json.dumps(data, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_python_content(content: bytes) -> str:
        """Normalize line endings and strip trailing whitespace, then SHA256 (D-03)."""
        text = content.decode("utf-8")
        lines = [line.rstrip() for line in text.splitlines()]
        normalized = "\n".join(lines)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_file(path: Path) -> str:
        """Hash a single file, dispatching by extension."""
        raw = path.read_bytes()
        if path.suffix in (".yaml", ".yml"):
            return ConfigHasher._hash_yaml_content(raw)
        return ConfigHasher._hash_python_content(raw)

    @staticmethod
    def hash_config(scaffold_dir: Path) -> ConfigSnapshot:
        """Hash all trigger files in a scaffold directory into a ConfigSnapshot.

        Collects files from TRIGGER_FILES and TRIGGER_DIRS, sorts by relative
        path, hashes each, then computes an aggregated SHA256 of all hashes.
        """
        discovered: list[Path] = []

        # Collect trigger files
        for filename in ConfigHasher.TRIGGER_FILES:
            candidate = scaffold_dir / filename
            if candidate.is_file():
                discovered.append(candidate)

        # Collect trigger directory files
        for dirname in ConfigHasher.TRIGGER_DIRS:
            dir_path = scaffold_dir / dirname
            if dir_path.is_dir():
                discovered.extend(sorted(dir_path.glob("*.py")))

        # Sort all discovered files by relative path for determinism
        discovered.sort(key=lambda p: str(p.relative_to(scaffold_dir)))

        # Hash each file
        files: dict[str, str] = {}
        for file_path in discovered:
            rel = str(file_path.relative_to(scaffold_dir))
            files[rel] = ConfigHasher.hash_file(file_path)

        # Compute aggregated hash from sorted file hashes
        concatenated = "".join(files[k] for k in sorted(files.keys()))
        aggregated_hash = hashlib.sha256(concatenated.encode("utf-8")).hexdigest()

        return ConfigSnapshot(
            snapshot_id=aggregated_hash,
            files=files,
            aggregated_hash=aggregated_hash,
            created_at=datetime.now(tz=timezone.utc),
        )

    @staticmethod
    def diff_snapshots(
        old: ConfigSnapshot,
        new: ConfigSnapshot,
    ) -> dict[str, tuple[str | None, str | None]]:
        """Compare two snapshots, returning only changed files.

        Returns a dict mapping relative paths to (old_hash, new_hash) tuples.
        None indicates a file was absent in that snapshot.
        """
        result: dict[str, tuple[str | None, str | None]] = {}
        all_keys = set(old.files.keys()) | set(new.files.keys())

        for key in sorted(all_keys):
            old_hash = old.files.get(key)
            new_hash = new.files.get(key)
            if old_hash != new_hash:
                result[key] = (old_hash, new_hash)

        return result
