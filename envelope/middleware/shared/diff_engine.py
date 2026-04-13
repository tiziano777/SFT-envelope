"""Git-style diff engine for comparing config snapshots in the lineage system."""

from __future__ import annotations

import difflib
import re
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from envelope.middleware.shared.config_hasher import ConfigSnapshot


# --- Diff Entry ---


class DiffEntry(BaseModel):
    """Structured diff entry with line number, change type, and content."""

    line: int = Field(..., ge=1, description="Line number in old file (removed) or new file (added)")
    type: Literal["added", "removed"] = Field(..., description="'added' or 'removed'")
    content: str = Field(..., description="Line content without trailing newline")


# --- DiffEngine ---


class DiffEngine:
    """Static utility for computing git-style diffs between file versions.

    Uses difflib.unified_diff with n=0 (no context lines) and parses @@
    headers to extract accurate line numbers for each change.
    """

    @staticmethod
    def compute_file_diff(
        old_text: str,
        new_text: str,
    ) -> list[DiffEntry]:
        """Compute a list of diff entries between two text versions.

        Each entry is a DiffEntry with line number (int), type (str: 'added'/'removed'), and content (str).
        Uses difflib.unified_diff with n=0 context lines and parses @@ headers
        for line number extraction.
        """
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()

        if old_lines == new_lines:
            return []

        result: list[DiffEntry] = []
        old_ln = 0
        new_ln = 0

        for line in difflib.unified_diff(old_lines, new_lines, lineterm="", n=0):
            if line.startswith("---") or line.startswith("+++"):
                continue
            if line.startswith("@@"):
                m = re.match(
                    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@",
                    line,
                )
                if m:
                    old_ln = int(m.group(1)) - 1
                    new_ln = int(m.group(3)) - 1
                continue
            if line.startswith("-"):
                old_ln += 1
                result.append(DiffEntry(
                    line=old_ln,
                    type="removed",
                    content=line[1:],
                ))
            elif line.startswith("+"):
                new_ln += 1
                result.append(DiffEntry(
                    line=new_ln,
                    type="added",
                    content=line[1:],
                ))

        return result

    @staticmethod
    def compute_scaffold_diff(
        old_snapshot: ConfigSnapshot,
        new_snapshot: ConfigSnapshot,
        old_texts: dict[str, str],
        new_texts: dict[str, str],
    ) -> dict[str, list[dict[str, int | str]] | dict[str, list[dict[str, int | str]]]]:
        """Compute the full diff_patch structure for a DERIVED_FROM relationship.

        Maps file categories to their diffs:
        - config: list of diff entries for config.yaml
        - train: list of diff entries for train.py
        - requirements: list of diff entries for requirements.txt
        - hyperparams: always empty list (placeholder for Phase 4)
        - rewards: dict of {filename: list of diff entries} for rewards/*.py

        Note: requirements.txt IS included per SHRD-09 even though
        excluded from trigger hash.
        """
        file_category_map: dict[str, str] = {
            "config.yaml": "config",
            "train.py": "train",
            "requirements.txt": "requirements",
        }

        result: dict[str, list[dict[str, int | str]] | dict[str, list[dict[str, int | str]]]] = {
            "config": [],
            "train": [],
            "requirements": [],
            "hyperparams": [],
            "rewards": {},
        }

        # Compute diffs for config, train, requirements
        for filename, category in file_category_map.items():
            old_content = old_texts.get(filename, "")
            new_content = new_texts.get(filename, "")
            result[category] = DiffEngine.compute_file_diff(old_content, new_content)

        # Compute rewards diffs (dict keyed by filename)
        reward_files: set[str] = set()
        for key in list(old_texts.keys()) + list(new_texts.keys()):
            if key.startswith("rewards/"):
                reward_files.add(key)

        rewards_result: dict[str, list[dict[str, int | str]]] = {}
        for reward_path in sorted(reward_files):
            # Strip rewards/ prefix for the key
            filename = reward_path.removeprefix("rewards/")
            old_content = old_texts.get(reward_path, "")
            new_content = new_texts.get(reward_path, "")
            diff = DiffEngine.compute_file_diff(old_content, new_content)
            if diff:
                rewards_result[filename] = diff

        result["rewards"] = rewards_result

        return result
