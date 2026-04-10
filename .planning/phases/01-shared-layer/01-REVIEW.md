---
phase: 01-shared-layer
reviewed: 2026-04-10T12:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - envelope/middleware/__init__.py
  - envelope/middleware/shared/__init__.py
  - envelope/middleware/shared/nodes.py
  - envelope/middleware/shared/relations.py
  - envelope/middleware/shared/envelopes.py
  - envelope/middleware/shared/config_hasher.py
  - envelope/middleware/shared/diff_engine.py
  - tests/unit/test_nodes.py
  - tests/unit/test_relations.py
  - tests/unit/test_envelopes.py
  - tests/unit/test_config_hasher.py
  - tests/unit/test_diff_engine.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-04-10T12:00:00Z
**Depth:** standard
**Files Reviewed:** 12 (7 source, 5 test)
**Status:** issues_found

## Summary

The Shared Layer implementation is solid and well-structured. All five node types correctly inherit from `BaseNode`, the `RelationType` enum has all 8 members, `Strategy` has 4 members, all four transport envelopes include `headers: dict[str, str]`, and `TRIGGER_FILES` correctly excludes `requirements.txt`. Pydantic v2 patterns are used consistently. `yaml.safe_load` is used correctly for YAML parsing (no security issue). Test coverage is thorough with serialization roundtrips, validation boundary tests, and contract verification.

The issues found are validation gaps where Pydantic models do not enforce invariants that the architecture spec defines, and a type-safety mismatch between `DiffEntry` (the Pydantic model) and the raw dicts actually returned by `DiffEngine.compute_file_diff`.

## Warnings

### WR-01: ConfigSnapshot allows snapshot_id != aggregated_hash

**File:** `envelope/middleware/shared/config_hasher.py:17-29`
**Issue:** The `ConfigSnapshot` model documents that `snapshot_id` equals `aggregated_hash` (line 20: "Equal to aggregated_hash, deterministic"), and `hash_config()` enforces this at construction time (line 107). However, nothing prevents constructing a `ConfigSnapshot` where `snapshot_id != aggregated_hash`. Any downstream consumer (e.g., Phase 2 DB layer deserializing from storage) could produce an inconsistent snapshot. The test at line 28-36 of `test_config_hasher.py` only checks a hand-constructed case where they match; it does not test that mismatched values are rejected.
**Fix:** Add a `model_validator(mode="after")` to enforce the invariant:
```python
from pydantic import model_validator

class ConfigSnapshot(BaseModel):
    # ... existing fields ...

    @model_validator(mode="after")
    def _snapshot_id_matches_aggregated(self) -> "ConfigSnapshot":
        if self.snapshot_id != self.aggregated_hash:
            msg = "snapshot_id must equal aggregated_hash"
            raise ValueError(msg)
        return self
```

### WR-02: DiffEntry.type accepts arbitrary strings

**File:** `envelope/middleware/shared/diff_engine.py:23`
**Issue:** `DiffEntry.type` is typed as `str` with no constraint. The architecture spec (section 4.2) defines only `"added"` and `"removed"` as valid values (with `"context"` as optional, currently unused). A downstream consumer deserializing a diff_patch could construct a `DiffEntry` with any string (e.g., `type="modified"`) without validation error. This weakens the contract.
**Fix:** Use `Literal` to constrain the field:
```python
from typing import Literal

class DiffEntry(BaseModel):
    line: int = Field(..., ge=1)
    type: Literal["added", "removed"] = Field(..., description="'added' or 'removed'")
    content: str = Field(...)
```

### WR-03: DiffEngine.compute_file_diff returns raw dicts, bypassing DiffEntry validation

**File:** `envelope/middleware/shared/diff_engine.py:37-84`
**Issue:** `compute_file_diff` returns `list[dict[str, int | str]]` -- raw dicts that are never validated against the `DiffEntry` model. This means the `ge=1` constraint on `DiffEntry.line` and any future type constraint on `DiffEntry.type` are not enforced on actual diff output. The `DiffEntry` model exists in the same file but is never used by the engine that produces diff data. This creates two parallel representations of the same data that can diverge silently.
**Fix:** Have `compute_file_diff` return `list[DiffEntry]` and construct `DiffEntry` objects internally. Update the return type annotation of `compute_scaffold_diff` accordingly. If raw dict output is needed for JSON serialization into `diff_patch`, callers can use `entry.model_dump()`.

### WR-04: HandshakeRequest does not validate parallel list length

**File:** `envelope/middleware/shared/envelopes.py:27-43`
**Issue:** `rewards_texts` and `rewards_filenames` are documented as parallel lists (architecture spec section 4.1: "lista parallela"). No validation ensures `len(rewards_texts) == len(rewards_filenames)`. A mismatch would cause silent data corruption when the Master populates `ExperimentNode.rewards` and `ExperimentNode.rewards_filenames` with misaligned entries.
**Fix:** Add a `model_validator(mode="after")`:
```python
from pydantic import model_validator

class HandshakeRequest(BaseModel):
    # ... existing fields ...

    @model_validator(mode="after")
    def _rewards_lists_aligned(self) -> "HandshakeRequest":
        if len(self.rewards_texts) != len(self.rewards_filenames):
            msg = f"rewards_texts ({len(self.rewards_texts)}) and rewards_filenames ({len(self.rewards_filenames)}) must have equal length"
            raise ValueError(msg)
        return self
```

## Info

### IN-01: hash_file treats all non-YAML files as Python

**File:** `envelope/middleware/shared/config_hasher.py:65-70`
**Issue:** `hash_file` dispatches to `_hash_yaml_content` for `.yaml`/`.yml` files and falls through to `_hash_python_content` for everything else. Currently safe because only `.yaml` and `.py` files are collected. However, if `TRIGGER_FILES` or `TRIGGER_DIRS` expand to include other file types (e.g., `.json`, `.toml`), those files would get Python-style normalization (line-ending + trailing whitespace stripping) which may not produce correct results.
**Fix:** Add explicit extension checks and raise `ValueError` for unsupported extensions, or document the assumption that only `.yaml`/`.yml`/`.py` files are supported.

### IN-02: compute_scaffold_diff accepts snapshot parameters it does not use

**File:** `envelope/middleware/shared/diff_engine.py:87-92`
**Issue:** `compute_scaffold_diff` accepts `old_snapshot` and `new_snapshot` parameters but never reads their data. The snapshot comparison logic lives in `ConfigHasher.diff_snapshots`, and the diff engine only uses the text dictionaries. The unused parameters add confusion about the method's contract and responsibilities.
**Fix:** Either remove the snapshot parameters (breaking change -- update callers) or document that they are reserved for future use (e.g., to filter diffs to only changed files based on hash comparison).

### IN-03: Test files use pytest.TempPathFactory type hint instead of Path

**File:** `tests/unit/test_config_hasher.py:87,94,101,122,130,135,144,149,155`
**Issue:** Several test methods annotate `tmp_path` as `pytest.TempPathFactory` instead of `pathlib.Path`. The `tmp_path` fixture provides a `pathlib.Path` instance, not a `TempPathFactory`. This is a type annotation error -- it works at runtime because Python does not enforce annotations, but it is misleading for readers and would fail under strict type checking (e.g., mypy with pytest plugin).
**Fix:** Change `tmp_path: pytest.TempPathFactory` to `tmp_path: Path` (importing `from pathlib import Path`).

---

_Reviewed: 2026-04-10T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
