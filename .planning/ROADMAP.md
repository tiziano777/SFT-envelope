# Roadmap: FineTuning-Envelope Lineage System

## Overview

This roadmap delivers a distributed lineage tracking system for AI fine-tuning experiments. Starting from shared data contracts, it builds up through database, observability, and API layers on the Master side, then the Worker daemon and generator integration, adds datamix support, validates everything end-to-end, and finishes with documentation. The architecture follows a Worker (GPU) to Master (CPU) pattern where training proceeds unblocked and lineage data syncs asynchronously. Every phase delivers a verifiable, self-contained capability.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

**Parallelization Waves:**
- Wave 1: Phase 1
- Wave 2: Phase 2 + Phase 3 + Phase 5
- Wave 3: Phase 4 + Phase 6 + Phase 8
- Wave 4: Phase 7
- Wave 5: Phase 9
- Wave 6: Phase 10

- [ ] **Phase 1: Shared Layer** - Pydantic dataclasses, enums, ConfigHasher, DiffEngine, and transport envelopes
- [ ] **Phase 2: Database Layer** - Neo4j schema, APOC triggers, driver, and repository with atomic Cypher queries
- [ ] **Phase 3: Observability** - Phoenix tracing setup, OTEL integration, and Docker service
- [ ] **Phase 4: Master API + Infrastructure** - FastAPI endpoints, LineageController, auth middleware, Docker Compose, Makefile
- [ ] **Phase 5: Storage Layer** - BaseStorageWriter ABC, URIResolver, LocalStorage, and S3/NFS stubs
- [ ] **Phase 6: Worker Layer** - Connections, local persistence, filesystem watcher, async pusher, and daemon
- [ ] **Phase 7: Generator Integration** - inject_worker_middleware, run.sh.j2 daemon lifecycle, merge scaffold
- [ ] **Phase 8: Datamix** - Multi-source config, DatamixLoader, replica oversampling, backward compatibility
- [ ] **Phase 9: Testing** - E2E suite with simulate_worker/master, handshake/checkpoint/config/daemon tests
- [ ] **Phase 10: Documentation** - Update workflow.md, README, existing docs, and new lineage docs

## Phase Details

### Phase 1: Shared Layer
**Goal**: All data contracts and utility functions used across Worker and Master are defined and tested
**Depends on**: Nothing (first phase)
**Requirements**: SHRD-01, SHRD-02, SHRD-03, SHRD-04, SHRD-05, SHRD-06, SHRD-07, SHRD-08, SHRD-09
**Success Criteria** (what must be TRUE):
  1. All 5 Neo4j node types (RecipeNode, ModelNode, ExperimentNode, CheckpointNode, ComponentNode) are instantiable as Pydantic dataclasses with field validation
  2. ConfigHasher produces identical SHA256 hashes for identical config/train/rewards files across runs, and requirements.txt is excluded from the trigger hash
  3. DiffEngine produces a git-style diff (line number, change type, content) between two ConfigSnapshots
  4. All transport envelopes (HandshakeRequest/Response, CheckpointPush, SyncEvent) and the Strategy enum serialize/deserialize correctly for HTTP transport
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Data contracts: BaseNode + 5 node types, RelationType enum, DerivedFromRel, Strategy enum, 4 transport envelopes with headers
- [ ] 01-02-PLAN.md — Utility functions: ConfigHasher (deterministic SHA256), ConfigSnapshot, DiffEngine (git-style diffs), DiffEntry model

### Phase 2: Database Layer
**Goal**: Neo4j stores and retrieves experiment lineage data with enforced constraints and automatic housekeeping
**Depends on**: Phase 1
**Requirements**: DB-01, DB-02, DB-03, DB-04, DB-05, DB-06, DB-07, DB-08
**Success Criteria** (what must be TRUE):
  1. Neo4j schema enforces uniqueness on recipe_id, exp_id, ckp_id, model_name, and component composite key
  2. APOC triggers automatically set created_at/updated_at timestamps and validate against orphan checkpoints (except is_merging=true)
  3. ExperimentRepository creates, queries, and upserts experiments and checkpoints via idempotent Cypher queries
  4. find_experiment_by_hashes returns the existing experiment for matching config hashes, and get_latest_checkpoint returns the most recent checkpoint for RESUME logic
**Plans**: TBD

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD

### Phase 3: Observability
**Goal**: All Master API activity is traced and visible in Phoenix UI without manual per-request instrumentation
**Depends on**: Nothing (independent — can parallel with Phase 2)
**Requirements**: OBSV-01, OBSV-02, OBSV-03, OBSV-04, OBSV-05
**Success Criteria** (what must be TRUE):
  1. Phoenix UI is accessible on localhost:6006 showing trace data from Master API requests
  2. setup_tracing() succeeds silently when Phoenix is unreachable (no crash, no hang, no error propagation)
  3. get_tracer() returns a functional tracer when OTEL is available, and a no-op fallback otherwise
  4. FastAPI auto-instrumentation is active without double-instrumentation, and manual spans exist on critical endpoints (handshake, checkpoint_push, status_update, merge, sync_event)
**Plans**: TBD

Plans:
- [ ] 03-01: TBD

### Phase 4: Master API + Infrastructure
**Goal**: Master API accepts Worker requests over HTTP, applies lineage logic, and runs in Docker with all supporting services
**Depends on**: Phase 1, Phase 2, Phase 3
**Requirements**: MAPI-01, MAPI-02, MAPI-03, MAPI-04, MAPI-05, MAPI-06, MAPI-07, MAPI-08, MAPI-09, MAPI-10, INFR-01, INFR-02, INFR-03, INFR-04, INFR-05
**Success Criteria** (what must be TRUE):
  1. POST /handshake returns the correct strategy (NEW, RESUME, BRANCH, RETRY) based on config hashes and experiment state
  2. All 7 REST endpoints respond with correct status codes and payloads (handshake, checkpoint push, status update, event log, merge, lineage query, health)
  3. X-API-Key middleware rejects unauthenticated requests with 401
  4. ConsistencyGuard prevents circular lineage relationships (source != target, max depth 50)
  5. `make master-up` starts Neo4j + Phoenix + Master API via Docker Compose; `make master-down` stops them; `make master-logs` streams logs
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD
- [ ] 04-03: TBD

### Phase 5: Storage Layer
**Goal**: Master can persist and retrieve artifacts via URI-based dispatch to pluggable storage backends
**Depends on**: Phase 1
**Requirements**: STOR-01, STOR-02, STOR-03, STOR-04, STOR-05
**Success Criteria** (what must be TRUE):
  1. LocalStorageWriter reads, writes, and checks existence of files via file:/// URIs
  2. URIResolver dispatches to the correct writer based on URI prefix (file://, s3://, nfs://, worker://, master://)
  3. S3 and NFS stubs raise NotImplementedError with a descriptive message
  4. URI prefix-to-writer mapping is configured via .env variables, not hardcoded
**Plans**: TBD

Plans:
- [ ] 05-01: TBD

### Phase 6: Worker Layer
**Goal**: Worker daemon runs alongside training, persists state locally, and pushes events to Master asynchronously with retry
**Depends on**: Phase 1, Phase 5
**Requirements**: WRKR-01, WRKR-02, WRKR-03, WRKR-04, WRKR-05, WRKR-06, WRKR-07, WRKR-08, WRKR-09, WRKR-10
**Success Criteria** (what must be TRUE):
  1. Worker daemon performs a blocking handshake on startup (configurable timeout, default 30s), writes .handshake_done and .exp_id files, and falls back to degraded mode on timeout
  2. HTTPConnection and SSHConnection both implement BaseConnection ABC and can send metadata and transfer files to Master
  3. WorkerState persists atomically (tmp + rename) and transfer_log.jsonl records every push attempt as an append-only audit trail
  4. Filesystem watcher (watchdog) detects changes in lineage/to_transfer/, training_metrics/, and config/rewards directories
  5. AsyncPusher uses a thread-safe queue with exponential backoff retry and deduplicates events by event_id
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD
- [ ] 06-03: TBD

### Phase 7: Generator Integration
**Goal**: Generated scaffolds include Worker middleware automatically, and merge scaffolds are producible as a new technique
**Depends on**: Phase 1, Phase 6
**Requirements**: GENR-01, GENR-02, GENR-03, GENR-04, GENR-05
**Success Criteria** (what must be TRUE):
  1. `envelope setup` produces a scaffold containing worker/ and shared/ directories via inject_worker_middleware() as step 16
  2. Generated run.sh starts the daemon, waits for .handshake_done, runs training, writes .training_done, and waits for daemon flush
  3. Generated requirements.txt includes watchdog, httpx, and paramiko dependencies
  4. `envelope setup` with merge technique produces a merge.py scaffold with daemon --one-shot mode
  5. capability_matrix recognizes 'merge' as a valid no-GPU technique
**Plans**: TBD

Plans:
- [ ] 07-01: TBD
- [ ] 07-02: TBD

### Phase 8: Datamix
**Goal**: Config YAML supports multi-source dataset definitions with replica oversampling while preserving backward compatibility
**Depends on**: Nothing (independent — only touches generator templates and config models)
**Requirements**: DMIX-01, DMIX-02, DMIX-03, DMIX-04
**Success Criteria** (what must be TRUE):
  1. Config YAML accepts a datamix section with multiple sources, each specifying uri, replica, samples, dist_name, and chat_type
  2. DatamixLoader in prepare.py detects whether config uses datamix or single dataset and loads accordingly
  3. Replica field causes integer oversampling (dataset repeated N times in the training data)
  4. Existing configs with single dataset field continue to work without any modification
**Plans**: TBD

Plans:
- [ ] 08-01: TBD

### Phase 9: Testing
**Goal**: Full end-to-end test suite validates the Worker-Master lineage flow across all branching scenarios and failure modes
**Depends on**: Phase 4, Phase 6, Phase 7
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05, TEST-06, TEST-07, TEST-08
**Success Criteria** (what must be TRUE):
  1. simulate_worker.py and simulate_master.py can run a complete experiment lifecycle (handshake through training_done) in a test environment
  2. All four handshake strategies (NEW, RESUME, BRANCH, RETRY) are tested with diff_patch verification against expected outputs
  3. Checkpoint push, idempotency (same event_id), and uri=NULL scenarios are explicitly covered
  4. Config change detection triggers branch strategy, verifying trigger hash on config.yaml, train.py, and rewards/*
  5. Test nodes use _TEST label and are cleaned up via DETACH DELETE after each test run
**Plans**: TBD

Plans:
- [ ] 09-01: TBD
- [ ] 09-02: TBD

### Phase 10: Documentation
**Goal**: All existing and new documentation reflects the lineage system integration so users can understand and operate the full system
**Depends on**: Phase 1, Phase 2, Phase 3, Phase 4, Phase 5, Phase 6, Phase 7, Phase 8, Phase 9
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04
**Success Criteria** (what must be TRUE):
  1. workflow.md describes the lineage phases in the setup generation pipeline (including step 16: inject_worker_middleware)
  2. README.md has a Lineage System section explaining the Worker-Master architecture, setup, and usage
  3. Existing docs for generator and frameworks modules describe the middleware injection and merge technique changes
  4. New documentation exists for lineage-specific modules: middleware/shared, middleware/worker, and master
**Plans**: TBD

Plans:
- [ ] 10-01: TBD

## Progress

**Execution Order:**
Phases execute respecting dependency waves. Within a wave, phases can execute in parallel.
- Wave 1: 1 | Wave 2: 2, 3, 5 | Wave 3: 4, 6, 8 | Wave 4: 7 | Wave 5: 9 | Wave 6: 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Shared Layer | 0/2 | Planning complete | - |
| 2. Database Layer | 0/2 | Not started | - |
| 3. Observability | 0/1 | Not started | - |
| 4. Master API + Infrastructure | 0/3 | Not started | - |
| 5. Storage Layer | 0/1 | Not started | - |
| 6. Worker Layer | 0/3 | Not started | - |
| 7. Generator Integration | 0/2 | Not started | - |
| 8. Datamix | 0/1 | Not started | - |
| 9. Testing | 0/2 | Not started | - |
| 10. Documentation | 0/1 | Not started | - |
