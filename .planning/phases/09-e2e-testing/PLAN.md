# Phase 9: E2E Testing Plan

**Phase:** 9 (Wave 5)
**Goal:** Full end-to-end test suite validates the Worker-Master lineage flow across all branching scenarios and failure modes
**Depends on:** Phase 4 (Master API ✓), Phase 6 (Worker Layer ✓), Phase 7 (Generator Integration ✓)
**Status:** Planning
**Plans:** 2

**Success Criteria:**
1. ✓ simulate_worker.py and simulate_master.py can run a complete experiment lifecycle (handshake through training_done)
2. ✓ All four handshake strategies (NEW, RESUME, BRANCH, RETRY) are tested with diff_patch verification
3. ✓ Checkpoint push, idempotency (same event_id), and uri=NULL scenarios are explicitly covered
4. ✓ Config change detection triggers BRANCH strategy; trigger hash verified on config.yaml, train.py, rewards/*
5. ✓ Test nodes use _TEST label and cleaned via DETACH DELETE after each test run

---

## Task 1: E2E Simulation & Lifecycle Tests

**Deliverables:**
- `tests/test_e2e.py` — Top-level E2E flow tests (lifecycle, daemon startup/shutdown, crash recovery)
- `tests/conftest.py` — Enhanced with Neo4j Docker fixture, FastAPI TestClient, test database cleanup
- `tests/utils/simulate_worker.py` — Reusable Worker simulator (handshake, checkpoint push, sync events, training_done)
- `tests/utils/simulate_master.py` — Subprocess Master API launcher with port auto-detection
- `tests/test_daemon_lifecycle.py` — Daemon startup, signal handling, graceful shutdown, .handshake_done/.training_done flags
- `tests/test_checkpoint_sync.py` — Checkpoint push (idempotency by event_id), uri=NULL handling, state persistence

**Key Implementation Details:**

### conftest.py Enhancements
```
- neo4j_docker_fixture: start Docker Neo4j container, create session, cleanup after test
- app_client: FastAPI TestClient pointing to localhost:8000 (or dynamic port)
- worker_simulator: fixture returning simulate_worker() helper
- master_process: fixture that starts master-api subprocess, waits for health check, yields, stops
- test_db_cleanup: after each test, MATCH (n:_TEST) DETACH DELETE n
```

### simulate_worker.py
```
- handshake(config, strategy_override=None) → HandshakeResponse
  - Makes POST /handshake with Worker config
  - Returns strategy (NEW, RESUME, BRANCH, RETRY)

- checkpoint_push(exp_id, ckp_num, artifact_uri=None) → CheckpointPush response
  - Serializes checkpoint data
  - Includes optional artifact_uri or sets uri=NULL
  - Tests idempotency: same event_id returns success

- sync_event(exp_id, event_type, payload) → response
  - Sends SyncEvent to /sync_event

- training_done(exp_id) → response
  - Signals completion
```

### simulate_master.py
```
- start_master(port=8000) → subprocess.Popen
  - Launches: python -m master.api --port PORT
  - Waits for GET /health 200
  - Logs to subprocess stdout/stderr

- stop_master(proc) → exit_code
  - Sends SIGTERM, waits 5s, SIGKILL if needed
  - Cleans up log files
```

### test_daemon_lifecycle.py
```
- test_daemon_bootstrap: .exp_id and .handshake_done files created
- test_daemon_shutdown: SIGTERM handled correctly
- test_daemon_crash_recovery: state persisted, restart resumes
- test_daemon_timeout_degraded_mode: handshake timeout triggers degraded (if implemented)
- test_transfer_log_append: transfer_log.jsonl grows atomically
```

### test_checkpoint_sync.py
```
- test_push_checkpoint_idempotency: same event_id → 200 (not error)
- test_push_checkpoint_no_uri: uri=NULL handling
- test_push_checkpoint_artifact: artifact_uri supplied, verified in storage
- test_state_persistence: WorkerState survives process restart
```

**Risk & Mitigations:**
- **Risk:** Neo4j Docker container takes time to start or port conflict
  - *Mitigation:* Use testcontainers with auto-port detection; waits up to 30s

- **Risk:** Master subprocess doesn't start or crashes
  - *Mitigation:* Health-check loop (5s timeout); detailed stderr logging for debugging

- **Risk:** Test pollution (nodes left in DB)
  - *Mitigation:* DETACH DELETE all _TEST nodes after each test; DETACH DELETE entire graphs before suite

---

## Task 2: Strategy Verification & Diff Tests

**Deliverables:**
- `tests/test_handshake.py` — All 4 strategies (NEW, RESUME, BRANCH, RETRY) with lineage graph verification
- `tests/test_config_change.py` — Trigger hash detection, branch strategy on config/train/rewards changes
- `tests/test_diff_verification.py` — diff_patch correctness (line numbers, change types, content)
- `tests/test_lineage_graph.py` — Experiment nodes, checkpoint links, derived-from relationships verified
- `tests/test_merge_strategy.py` — Merge checkpoint scenarios (N sources, circular dependency detection)

**Key Implementation Details:**

### test_handshake.py
```
Scenario 1: NEW Strategy
- First time running config hash
- Expect: strategy=NEW
- Verify: experiment node created, exp_id returned

Scenario 2: RESUME Strategy
- Same config hash as previous run
- New checkpoint available
- Expect: strategy=RESUME, latest checkpoint returned
- Verify: uses latest_checkpoint.ckp_id

Scenario 3: BRANCH Strategy
- Config hash differs (config.yaml XOR train.py XOR rewards/* changed)
- Expect: strategy=BRANCH, diff_patch populated
- Verify: diff_patch shows old_line/new_line/change_type for config file

Scenario 4: RETRY Strategy
- Same config hash, same checkpoint
- Last sync failed (retry counter active)
- Expect: strategy=RETRY, same checkpoint returned
- Verify: retry_count incremented in Neo4j

Test execution:
- For each scenario:
  1. Setup database state (prior experiment or empty)
  2. Call simulate_worker.handshake()
  3. Assert strategy enum value
  4. Graph query: verify nodes created/linked correctly
  5. If BRANCH: verify diff_patch structure and content
```

### test_config_change.py
```
- Setup: Run NEW strategy, record config hash
- Modify config.yaml (whitespace only) → hash should be same (deterministic)
- Modify config.yaml (actual change) → hash differs
- Call handshake with new config
- Assert: strategy=BRANCH
- Verify: diff_patch shows change details (line num, old content, new content)

- Test: Modify train.py
- Test: Add/remove file in rewards/
- Test: Modify requirements.txt (should NOT be in trigger hash)
  - Expect: strategy=RESUME (not BRANCH) — requirements.txt explicitly excluded
```

### test_diff_verification.py
```
- Generate two ConfigSnapshot objects (old, new)
- Call DiffEngine.diff(old, new)
- Verify DiffEntry list:
  - Line numbers correct
  - change_type in [ADD, REMOVE, MODIFY]
  - Content preserved exactly

- Edge cases:
  - Empty config
  - Identical configs → empty diff
  - Multi-line file changes
```

### test_lineage_graph.py
```
- After multiple handshakes and checkpoints:
  - Query experiment node
  - Verify checkpoint nodes linked with :HAS_CHECKPOINT
  - Verify DERIVED_FROM relationship if strategy=BRANCH
  - Verify _TEST label on all nodes

- Graph traversal:
  - find_experiment_by_hashes() returns correct node
  - get_latest_checkpoint() returns newest by timestamp
```

### test_merge_strategy.py
```
- Setup: 3 checkpoint nodes from different experiments
- POST /merge with [ckp1, ckp2, ckp3]
- Verify: Merged checkpoint created
- Verify: :MERGED_FROM relationship to N sources
- Verify: Circular dependency detection (A merged from B, B merged from A) → 409 error
```

**Assumptions & Constraints:**
- All test data uses minimal sizes (single config file, 1-2 checkpoints)
- Master API runs on auto-detected port (env var or fixture)
- Neo4j transaction rollback/cleanup between tests (not per-node deletion)
- No actual GPU training — simulate via mock or stub

**Risk & Mitigations:**
- **Risk:** Diff verification is brittle (whitespace, encoding)
  - *Mitigation:* Normalize line endings; use raw byte comparison; test with various file types

- **Risk:** Config hash collisions (spurious RESUME when should be BRANCH)
  - *Mitigation:* Comprehensive hash tests cover all trigger files; add fuzzing test

- **Risk:** Graph state leaks between tests
  - *Mitigation:* Fixture scopes: function-level cleanup; session-level setup of DB container

---

## Environment Setup

### Prerequisites
- Python 3.10+ with .venv activated
- Docker running (for Neo4j container)
- pytest, httpx, neo4j, FastAPI, uvicorn installed

### Test Database
- Neo4j Docker container started by `neo4j_docker_fixture`
- Schema auto-initialized on fixture startup (run setup_neo4j_schema.py)
- Port: 7687 (bolt) — auto-detected in fixture

### Test Master API
- Runs in subprocess on ephemeral port (8000+ assigned by fixture)
- Logs: `/tmp/master-api-test-*.log`
- Cleanup: Killed and log deleted after test

### Test Data
- Minimal configs: 3-line config.yaml, simple train.py
- Checkpoint data: mock tensors or small numpy arrays
- All nodes tagged with `:_TEST` label for cleanup

---

## Verification Checklist

- [ ] `conftest.py` has neo4j_docker_fixture with cleanup
- [ ] `simulate_worker.py` implements handshake, checkpoint_push, sync_event
- [ ] `simulate_master.py` starts/stops subprocess with health check
- [ ] `test_e2e.py` runs complete lifecycle (handshake → checkpoint → training_done)
- [ ] `test_handshake.py` covers all 4 strategies with graph verification
- [ ] `test_config_change.py` detects hash changes and triggers BRANCH
- [ ] `test_checkpoint_sync.py` verifies idempotency and uri=NULL handling
- [ ] `test_daemon_lifecycle.py` tests startup, shutdown, signal handling
- [ ] `test_diff_verification.py` validates DiffEntry correctness
- [ ] `test_lineage_graph.py` verifies Neo4j relationships
- [ ] `test_merge_strategy.py` tests merge and circular dependency detection
- [ ] All tests use `:_TEST` label and cleanup DETACH DELETE
- [ ] pytest runs all tests with `pytest tests/test_*.py -v`
- [ ] Coverage: > 80% for `envelope/master/` and `envelope/middleware/worker/`
- [ ] Neo4j Docker fixture works on both macOS and Linux (Docker Desktop / Docker Engine)

---

## Success Definition

**Done when:**
1. All 5 test files pass: test_handshake, test_config_change, test_checkpoint_sync, test_daemon_lifecycle, test_diff_verification
2. All 4 handshake strategies verified with diff_patch comparison
3. Idempotency tested: same event_id returns 200
4. Config change detection working: trigger hash excludes requirements.txt
5. Test cleanup: 0 nodes left in Neo4j after full test suite
6. pytest run with `-v` shows 50+ tests passing (estimate: 8-12 per test file)

---

## Notes

- This plan assumes Phase 4, 6, 7 implementations are complete and stable
- Test-specific mocks (e.g., for storage URIs) can use file:// schema only (S3/NFS are v2)
- Graph queries use Cypher directly via neo4j.Session (not via repository, to avoid circular test dependencies)
- Fast execution target: full suite < 60s (aggressive cleanup, no sleeps)
