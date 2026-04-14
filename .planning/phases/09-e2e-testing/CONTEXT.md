# Phase 9: E2E Testing — Context & Decisions

**Phase Goal:** Full end-to-end test suite validates the Worker-Master lineage flow across all branching scenarios and failure modes

**Requirements:** TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06, TEST-07, TEST-08 (8 total)

**Success Criteria:**
1. ✓ simulate_worker.py and simulate_master.py can run complete experiment lifecycle
2. ✓ All 4 handshake strategies (NEW, RESUME, BRANCH, RETRY) tested with diff verification
3. ✓ Checkpoint push, idempotency (same event_id), uri=NULL scenarios covered
4. ✓ Config change detection triggers BRANCH; trigger hash verified on config.yaml, train.py, rewards/*
5. ✓ Test nodes use :_TEST label and cleaned via DETACH DELETE

---

## Phase Structure

**Two Plans:**
- **09-01-PLAN.md:** E2E Simulation & Lifecycle Tests (5 tasks, ~8-10 tests)
  - Tasks: conftest.py, simulate_worker.py, simulate_master.py, test_daemon_lifecycle.py, test_checkpoint_sync.py
  - Focus: Fixtures, simulators, daemon lifecycle, checkpoint idempotency

- **09-02-PLAN.md:** Strategy Verification & Diff Tests (5 tasks, ~20-25 tests)
  - Tasks: test_handshake.py, test_config_change.py, test_diff_verification.py, test_lineage_graph.py, test_merge_strategy.py
  - Focus: All 4 strategies, trigger hash, diff correctness, graph validation, merge scenarios

**Total Coverage:** 28-35 tests across 10 test files

---

## Key Architectural Decisions

### 1. Neo4j Test Environment
- **Decision:** Use real Neo4j Docker container (not mocks)
- **Rationale:** Full integration test required; mocks miss graph-specific edge cases (uniqueness constraints, APOC triggers, Cypher query semantics)
- **Implementation:** pytest session-scoped fixture, auto-port detection, cleanup via :_TEST label DETACH DELETE

### 2. Test Isolation
- **Decision:** :_TEST label on all test nodes; cleanup after each test
- **Rationale:** Prevents test pollution; enables parallel execution (future)
- **Implementation:** MATCH (n:_TEST) DETACH DELETE n in neo4j_session fixture

### 3. Simulator Reusability
- **Decision:** WorkerSimulator and Master subprocess launcher as separate utilities
- **Rationale:** Can be imported by user code or other test suites; not test-specific
- **Implementation:** tests/utils/simulate_worker.py, tests/utils/simulate_master.py

### 4. Strategy Test Coverage
- **Decision:** Comprehensive: all 4 strategies (NEW, RESUME, BRANCH, RETRY)
- **Rationale:** User's choice for full coverage validation
- **Implementation:** test_handshake.py with 4 explicit scenarios

### 5. Trigger Hash Verification
- **Decision:** Include explicit test for requirements.txt exclusion
- **Rationale:** Critical business logic: requirements can change without triggering BRANCH
- **Implementation:** test_config_change.py::test_requirements_excluded_from_hash

---

## Dependencies & Assumptions

### Phase 9.1 Requires (must be complete):
- ✓ Phase 1: Shared data contracts (ConfigSnapshot, ConfigHasher, DiffEngine, Strategy enum)
- ✓ Phase 2: Neo4j schema, ExperimentRepository, query methods
- ✓ Phase 3: Observability (optional for tests, but should work if present)
- ✓ Phase 4: Master API (5 endpoints, error handlers)
- ✓ Phase 6: Worker Layer (daemon, state persistence)
- ✓ Phase 7: Generator Integration (middleware, run.sh.j2)

### Phase 9.2 Requires:
- ✓ Phase 9.1 (fixtures and simulators)
- ✓ All phases above

### Assumptions:
- Python 3.10+ with .venv activated
- Docker running (for Neo4j container)
- All dependencies installed (pytest, neo4j, httpx, FastAPI)
- Master API module importable as `master.api`
- envelope package importable

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Neo4j container start time | 5-10s per test run | Session-scoped fixture (start once); testcontainers with auto-port |
| Master subprocess doesn't start | Entire test suite blocked | Health-check loop with 10s timeout; detailed stderr logging |
| Test pollution (nodes left in DB) | False failures on subsequent runs | Fixture-level DETACH DELETE :_TEST; session-scoped cleanup |
| Diff verification brittleness | Whitespace/encoding edge cases | Normalize line endings; byte-level comparison; fuzz tests |
| Config hash collisions | Spurious RESUME when should BRANCH | Comprehensive hash tests; add fuzzing with random configs |
| Graph state leaks | State-dependent test failures | Function-scoped neo4j_session fixture; fresh DB between tests |

---

## Execution Notes

### Test Execution Order
1. Fixtures setup (session-scoped): neo4j_container → instantiated once
2. Plan 9.1 tests first (infrastructure tests)
   - conftest.py fixtures validated
   - Simulators tested
   - Daemon lifecycle and checkpoint sync verified
3. Plan 9.2 tests next (strategy tests)
   - Depend on working 9.1 infrastructure
   - Can run in parallel (independent scenarios)

### Speed Targets
- **conftest.py fixture startup:** 10-15s (Neo4j warmup)
- **Per test:** 0.5-2s (most)
- **Full suite:** < 90s (est. 35 tests × 1.5s avg + 15s fixtures)

### Coverage Goals
- Master API: > 80% (5 endpoints, error paths)
- Worker Layer: > 80% (daemon, state, connections)
- Shared Layer: > 90% (ConfigHasher, DiffEngine, enums)

---

## Post-Phase Cleanup

- Archive 09-e2e-testing/ to .planning/archive/ after completion
- Move successful test files to tests/ (versioned)
- Update ROADMAP.md: Phase 9 → COMPLETE ✓

---

## Sign-off

Phase 9 planning ready for execution. All success criteria mapped. 2 concrete plans with task-level granularity. No blockers identified.

**Planned:** 28-35 tests across 2 plans
**Expected Duration:** 4-5 hours total (incl. fixture setup, test runs)
**Go/No-Go:** GO — Ready for execution via /gsd-execute-phase
