---
phase: 01-shared-layer
plan: 02
subsystem: utilities
tags: [sha256, hashing, difflib, pydantic, deterministic, lineage]

# Dependency graph
requires:
  - "01-01: Data Contracts (BaseNode, envelopes, relations, Strategy, shared/__init__.py)"
provides:
  - "ConfigHasher with deterministic SHA256 via parse+normalize (D-03)"
  - "ConfigSnapshot Pydantic model (serializable hash manifest)"
  - "DiffEngine with git-style diff computation via difflib.unified_diff"
  - "DiffEntry Pydantic model (structured diff entry)"
  - "shared/__init__.py re-exports all 17 public types"
affects: [02-db-layer, 03-worker-layer, 06-worker-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Parse+normalize for deterministic hashing: YAML via safe_load+json.dumps(sort_keys=True), Python via line-ending normalization"
    - "Static utility classes (ConfigHasher, DiffEngine) with @staticmethod methods"
    - "difflib.unified_diff with n=0 and @@ header regex parsing for line numbers"
    - "TYPE_CHECKING import guard to avoid circular imports"

key-files:
  created:
    - envelope/middleware/shared/config_hasher.py
    - envelope/middleware/shared/diff_engine.py
    - tests/unit/test_config_hasher.py
    - tests/unit/test_diff_engine.py
  modified:
    - envelope/middleware/shared/__init__.py

key-decisions:
  - "ConfigHasher uses static methods (no instantiation) -- pure utility class with no state"
  - "DiffEntry formalized as Pydantic model for type safety (Claude's discretion per CONTEXT.md)"
  - "hyperparams key in scaffold diff is always empty list -- placeholder for Phase 4"
  - "rewards diff keyed by filename (strip rewards/ prefix) per architecture doc"

patterns-established:
  - "Static utility class pattern: ConfigHasher and DiffEngine as collections of @staticmethod methods"
  - "Scaffold diff structure: dict with config/train/requirements/hyperparams (list[dict]) + rewards (dict[str, list[dict]])"
  - "File hash dispatch by extension: .yaml/.yml -> YAML normalization, everything else -> Python normalization"

requirements-completed: [SHRD-06, SHRD-07, SHRD-08, SHRD-09]

# Metrics
duration: 3min
completed: 2026-04-10
---

# Phase 1 Plan 2: Utilities Summary

**Deterministic SHA256 ConfigHasher with parse+normalize strategy, ConfigSnapshot manifest, and git-style DiffEngine using difflib.unified_diff with @@ header parsing**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-10T15:33:40Z
- **Completed:** 2026-04-10T15:37:00Z
- **Tasks:** 2
- **Files created:** 4
- **Files modified:** 1

## Accomplishments
- ConfigHasher with deterministic SHA256 hashing: YAML normalized via safe_load + json.dumps(sort_keys=True), Python via line-ending + trailing-whitespace normalization (D-03)
- ConfigSnapshot Pydantic model with snapshot_id, files dict, aggregated_hash, and created_at for serialization roundtrip
- DiffEngine producing git-style diff entries with line/type/content fields via difflib.unified_diff parsing
- requirements.txt excluded from trigger hash (TRIGGER_FILES) but included in scaffold diff output per SHRD-09
- shared/__init__.py now re-exports all 17 public types from the complete shared package
- 36 new tests passing (21 ConfigHasher + 15 DiffEngine), 108 total phase tests green

## Task Commits

Each task was committed atomically with TDD:

1. **Task 1: ConfigHasher + ConfigSnapshot** - RED `f918c51` (test) -> GREEN `d2f899f` (feat)
2. **Task 2: DiffEngine + DiffEntry + __init__.py** - RED `e612ca7` (test) -> GREEN `15851de` (feat)

_TDD workflow: RED tests committed before implementation, GREEN on passing._

## Files Created/Modified
- `envelope/middleware/shared/config_hasher.py` - ConfigHasher (static SHA256 utility) + ConfigSnapshot (Pydantic hash manifest)
- `envelope/middleware/shared/diff_engine.py` - DiffEngine (static diff utility) + DiffEntry (Pydantic diff entry model)
- `envelope/middleware/shared/__init__.py` - Updated with 4 new re-exports (17 total in __all__)
- `tests/unit/test_config_hasher.py` - 21 tests: snapshot, YAML/Python normalization, scaffold hashing, requirements exclusion, diff_snapshots
- `tests/unit/test_diff_engine.py` - 15 tests: DiffEntry model, file diff computation, scaffold diff structure

## Decisions Made
- ConfigHasher and DiffEngine as static utility classes (no instantiation needed) -- these are pure function collections with no internal state
- DiffEntry formalized as a Pydantic BaseModel rather than plain dict for type safety at API boundaries (Claude's discretion per CONTEXT.md)
- hyperparams key in compute_scaffold_diff always returns empty list -- intentional placeholder for Phase 4 (Master API)
- rewards diff dict keyed by filename without the rewards/ prefix (e.g., "math_reward.py" not "rewards/math_reward.py")

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All shared data contracts and utilities are complete (17 types, 108 tests passing)
- Phase 2 (DB Layer) can import all node/relation models from `envelope.middleware.shared`
- Phase 3 (Worker Layer) can import ConfigHasher + DiffEngine for config change detection
- Phase 4 (Master API) can import transport envelopes for request/response schemas
- Complete shared package is: nodes (6 types), relations (2 types), envelopes (5 types), utilities (4 types)

## Self-Check: PASSED

All 6 files verified present. All 4 task commits (f918c51, d2f899f, e612ca7, 15851de) verified in git log. 108 phase tests passing.

---
*Phase: 01-shared-layer*
*Completed: 2026-04-10*
