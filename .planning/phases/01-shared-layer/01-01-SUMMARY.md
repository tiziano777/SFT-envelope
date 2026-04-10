---
phase: 01-shared-layer
plan: 01
subsystem: data-contracts
tags: [pydantic, neo4j, enums, serialization, lineage]

# Dependency graph
requires: []
provides:
  - "BaseNode + 5 Neo4j node types (RecipeNode, ModelNode, ExperimentNode, CheckpointNode, ComponentNode)"
  - "RelationType enum with 8 members"
  - "DerivedFromRel model with diff_patch structure"
  - "Strategy enum (NEW, RESUME, BRANCH, RETRY)"
  - "4 transport envelopes (HandshakeRequest, HandshakeResponse, CheckpointPush, SyncEvent)"
  - "shared/__init__.py re-exports 13 public types"
affects: [02-db-layer, 03-worker-layer, 04-master-api, 01-02-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "BaseNode inheritance for Neo4j node types"
    - "UPPER_CASE enum values for protocol constants (RelationType, Strategy)"
    - "headers: dict[str, str] on all transport envelopes for extensibility (D-04)"
    - "TDD workflow: RED tests before implementation, GREEN to pass"

key-files:
  created:
    - envelope/middleware/__init__.py
    - envelope/middleware/shared/__init__.py
    - envelope/middleware/shared/nodes.py
    - envelope/middleware/shared/relations.py
    - envelope/middleware/shared/envelopes.py
    - tests/unit/test_nodes.py
    - tests/unit/test_relations.py
    - tests/unit/test_envelopes.py
  modified: []

key-decisions:
  - "BaseNode carries id + created_at + updated_at per D-02; all 5 node types inherit"
  - "RelationType and Strategy enums use UPPER_CASE values (protocol constants, not YAML config)"
  - "diff_patch typed as dict[str, Any] for flexibility with rewards dict-of-lists structure"

patterns-established:
  - "BaseNode inheritance: all Neo4j node types extend BaseNode(BaseModel)"
  - "Transport envelope pattern: headers as last field with Field(default_factory=dict)"
  - "Module layout: nodes.py, relations.py, envelopes.py with __init__.py re-exports"

requirements-completed: [SHRD-01, SHRD-02, SHRD-03, SHRD-04, SHRD-05]

# Metrics
duration: 4min
completed: 2026-04-10
---

# Phase 1 Plan 1: Data Contracts Summary

**Pydantic v2 data contracts: 5 Neo4j node types with BaseNode inheritance, 8 relation types, Strategy enum, and 4 transport envelopes with extensibility headers**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-10T15:27:19Z
- **Completed:** 2026-04-10T15:31:00Z
- **Tasks:** 2
- **Files created:** 8

## Accomplishments
- All 5 Neo4j node types (RecipeNode, ModelNode, ExperimentNode, CheckpointNode, ComponentNode) as Pydantic v2 models inheriting from BaseNode
- RelationType enum with 8 members + DerivedFromRel model with structured diff_patch
- Strategy enum (NEW, RESUME, BRANCH, RETRY) + 4 transport envelopes with headers field per D-04
- 72 unit tests passing: instantiation, field validation, inheritance, serialization roundtrip
- shared/__init__.py with __all__ re-exporting all 13 public types

## Task Commits

Each task was committed atomically:

1. **Task 1: Create package structure and nodes.py with BaseNode + 5 node types** - `2766909` (feat)
2. **Task 2: Create relations.py, envelopes.py, tests, and shared __init__.py with re-exports** - `34f803c` (feat)

## Files Created/Modified
- `envelope/middleware/__init__.py` - Package marker with docstring
- `envelope/middleware/shared/__init__.py` - Re-exports all 13 public types with __all__
- `envelope/middleware/shared/nodes.py` - BaseNode + 5 Neo4j node types
- `envelope/middleware/shared/relations.py` - RelationType enum (8 members) + DerivedFromRel model
- `envelope/middleware/shared/envelopes.py` - Strategy enum (4 members) + 4 transport envelopes
- `tests/unit/test_nodes.py` - 26 tests for node instantiation, validation, inheritance, roundtrip
- `tests/unit/test_relations.py` - 11 tests for RelationType and DerivedFromRel
- `tests/unit/test_envelopes.py` - 35 tests for Strategy, envelopes, and headers

## Decisions Made
- BaseNode carries `id: str` (min_length=1) + `created_at`/`updated_at` per D-02; all node types inherit via `class XxxNode(BaseNode)`
- RelationType and Strategy enums use UPPER_CASE values -- intentional deviation from project lowercase enum convention since these are protocol constants, not YAML config values (documented in research as assumption A1)
- `diff_patch` typed as `dict[str, Any]` rather than a stricter type, accommodating the rewards field which is `dict[str, list[dict]]` while other keys are `list[dict]`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All shared data contracts are defined and tested
- Plan 01-02 (ConfigHasher + DiffEngine) can import BaseNode and node types from `envelope.middleware.shared`
- Phase 2 (DB Layer) can import node/relation models for Neo4j repository
- Phase 4 (Master API) can import transport envelopes for request/response schemas

## Self-Check: PASSED

All 9 files verified present. Both task commits (2766909, 34f803c) verified in git log. 72 tests passing.

---
*Phase: 01-shared-layer*
*Completed: 2026-04-10*
