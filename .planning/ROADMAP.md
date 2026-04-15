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

- [x] **Phase 1: Shared Layer** - Pydantic dataclasses, enums, ConfigHasher, DiffEngine, and transport envelopes
- [x] **Phase 2: Database Layer** - Neo4j schema, APOC triggers, driver, and repository with atomic Cypher queries
- [x] **Phase 3: Observability** - Phoenix tracing setup, OTEL integration, and Docker service
- [x] **Phase 4: Master API + Infrastructure** - FastAPI endpoints, LineageController, auth middleware, Docker Compose, Makefile
- [x] **Phase 5: Storage Layer** - BaseStorageWriter ABC, URIResolver, LocalStorage, and S3/NFS stubs
- [x] **Phase 6: Worker Layer** - Connections, local persistence, filesystem watcher, async pusher, and daemon
- [x] **Phase 7: Generator Integration** - inject_worker_middleware, run.sh.j2 daemon lifecycle, merge scaffold
- [x] **Phase 8: Datamix** - Multi-source config, DatamixLoader, replica oversampling, backward compatibility
- [ ] **Phase 9: Testing** - E2E suite with simulate_worker/master, handshake/checkpoint/config/daemon tests
- [ ] **Phase 10: Documentation** - Update workflow.md, README, existing docs, and new lineage docs
- [x] **Phase 13: Recipe Management Fix** - Filename-based recipe names, Neo4j DDL constraints, comprehensive logging, error recovery
- [x] **Phase 13.1: Neo4j Schema Consolidation** (INSERTED) - Eliminate database/schema_init.cypher redundancy, create complete schema (nodes/edges/constraints/triggers from Pydantic models), populate seed data (Component Nodes and Models)

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
- [x] 01-02-PLAN.md — Utility functions: ConfigHasher (deterministic SHA256), ConfigSnapshot, DiffEngine (git-style diffs), DiffEntry model

### Phase 2: Database Layer
**Goal**: Neo4j stores and retrieves experiment lineage data with enforced constraints and automatic housekeeping
**Depends on**: Phase 1
**Requirements**: DB-01, DB-02, DB-03, DB-04, DB-05, DB-06, DB-07, DB-08
**Success Criteria** (what must be TRUE):
  1. Neo4j schema enforces uniqueness on recipe_id, exp_id, ckp_id, model_name, and component composite key
  2. APOC triggers automatically set created_at/updated_at timestamps and validate against orphan checkpoints (except is_merging=true)
  3. ExperimentRepository creates, queries, and upserts experiments and checkpoints via idempotent Cypher queries
  4. find_experiment_by_hashes returns the existing experiment for matching config hashes, and get_latest_checkpoint returns the most recent checkpoint for RESUME logic
**Plans**: 2 plans

Plans:
- [x] 02-01-PLAN.md — Neo4j schema: unique constraints, APOC triggers, node initialization
- [x] 02-02-PLAN.md — Repository: ExperimentRepository with idempotent Cypher, find_experiment_by_hashes, get_latest_checkpoint

### Phase 3: Observability
**Goal**: All Master API activity is traced and visible in Phoenix UI without manual per-request instrumentation
**Depends on**: Nothing (independent — can parallel with Phase 2)
**Requirements**: OBSV-01, OBSV-02, OBSV-03, OBSV-04, OBSV-05
**Success Criteria** (what must be TRUE):
  1. Phoenix UI is accessible on localhost:6006 showing trace data from Master API requests
  2. setup_tracing() succeeds silently when Phoenix is unreachable (no crash, no hang, no error propagation)
  3. get_tracer() returns a functional tracer when OTEL is available, and a no-op fallback otherwise
  4. FastAPI auto-instrumentation is active without double-instrumentation, and manual spans exist on critical endpoints (handshake, checkpoint_push, status_update, merge, sync_event)
**Plans**: 1 plan

Plans:
- [x] 03-01-PLAN.md — OTEL tracing setup, FastAPI auto-instrumentation, manual spans on 5 critical endpoints, graceful degradation, integration tests with Phoenix

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
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md — Master API: 5 critical endpoints, error handlers, manual spans, Neo4j integration
- [x] 04-02-GREEN-PLAN.md — Test mock fixes: correct patch targets and return values
- [x] 04-03-PLAN.md — Docker Compose, Makefile, infrastructure tests

### Phase 5: Storage Layer
**Goal**: Master can persist and retrieve artifacts via URI-based dispatch to pluggable storage backends
**Depends on**: Phase 1
**Requirements**: STOR-01, STOR-02, STOR-03, STOR-04, STOR-05
**Success Criteria** (what must be TRUE):
  1. LocalStorageWriter reads, writes, and checks existence of files via file:/// URIs
  2. URIResolver dispatches to the correct writer based on URI prefix (file://, s3://, nfs://, worker://, master://)
  3. S3 and NFS stubs raise NotImplementedError with a descriptive message
  4. URI prefix-to-writer mapping is configured via .env variables, not hardcoded
**Plans**: 1 plan

Plans:
- [x] 05-01-PLAN.md — Storage layer: BaseStorageWriter ABC, URIResolver dispatch, LocalStorage, S3/NFS stubs, integration tests

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
**Plans**: 3 plans

Plans:
- [x] 06-01-PLAN.md — Daemon core: bootstrap, state persistence (WorkerDaemon, WorkerState)
- [x] 06-02-PLAN.md — Connection layer: BaseConnection ABC, HTTP, SSH stubs
- [x] 06-03-PLAN.md — Async pushing: watcher, AsyncPusher, exponential backoff

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
**Plans**: 2 plans

Plans:
- [x] 07-01-PLAN.md — inject_worker_middleware() in setup_generator.py, run.sh.j2 daemon lifecycle, requirements.txt.j2 worker deps
- [x] 07-02-PLAN.md — MergeTechnique plugin, merge.py.j2 template, capability_matrix merge entry, integration tests

### Phase 8: Datamix
**Goal**: Config YAML supports multi-source dataset definitions with replica oversampling while preserving backward compatibility
**Depends on**: Nothing (independent — only touches generator templates and config models)
**Requirements**: DMIX-01, DMIX-02, DMIX-03, DMIX-04
**Success Criteria** (what must be TRUE):
  1. Config YAML accepts a datamix section with multiple sources, each specifying uri, replica, samples, dist_name, and chat_type
  2. DatamixLoader in prepare.py detects whether config uses datamix or single dataset and loads accordingly
  3. Replica field causes integer oversampling (dataset repeated N times in the training data)
  4. Existing configs with single dataset field continue to work without any modification
**Plans**: 1 plan

Plans:
- [x] 08-01-PLAN.md — Datamix config: DatamixSource, DatamixLoader, multi-source + replica oversampling

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
**Plans**: 2 plans

Plans:
- [x] 09-01-PLAN.md — E2E test suite: simulate_worker, simulate_master, lifecycle tests
- [x] 09-02-PLAN.md — Strategy tests: NEW, RESUME, BRANCH, RETRY with diff verification

### Phase 10: Documentation
**Goal**: All existing and new documentation reflects the lineage system integration so users can understand and operate the full system
**Depends on**: Phase 1, Phase 2, Phase 3, Phase 4, Phase 5, Phase 6, Phase 7, Phase 8, Phase 9
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04
**Success Criteria** (what must be TRUE):
  1. workflow.md describes the lineage phases in the setup generation pipeline (including step 16: inject_worker_middleware)
  2. README.md has a Lineage System section explaining the Worker-Master architecture, setup, and usage
  3. Existing docs for generator and frameworks modules describe the middleware injection and merge technique changes
  4. New documentation exists for lineage-specific modules: middleware/shared, middleware/worker, and master
**Plans**: 1 plan

Plans:
- [ ] 10-01-PLAN.md — Documentation updates: workflow.md, README, module docs, lineage guides

### Phase 13: Recipe Management Fix
**Goal**: Recipe upload workflow supports filename-based recipe names, enforces Neo4j uniqueness at DDL level, provides comprehensive error handling and logging
**Depends on**: Phase 11 (Streamlit UI async pattern)
**Requirements**: RECIPE-01, RECIPE-02, RECIPE-03, RECIPE-04, RECIPE-05, RECIPE-06
**Success Criteria** (what must be TRUE):
  1. Recipe name is derived from YAML filename when 'name' field is not present; if both missing, raise clear validation error
  2. Neo4j unique constraint on Recipe.name is created via DDL during build phase (not runtime in asyncClient)
  3. Duplicate recipe name detection catches both app-level and DB-level constraint violations; user sees recovery options (rename or undo)
  4. RecipeManager.create_recipe() validates recipe structure and confirms all entries loaded into recipe.entries
  5. Comprehensive logging added to all CRUD operations (create, read, update, delete) with structured log messages
  6. User sees informative error messages: "Recipe name already exists → rename or choose different file" with clear recovery path
**Plans**: 2 plans

Plans:
- [x] 13-01-PLAN.md — Filename-based names, Neo4j DDL constraint creation, validation error handling
- [x] 13-02-PLAN.md — Logging infrastructure, error messages, user recovery flows, E2E test coverage

### Phase 13.1: Neo4j Schema Consolidation (INSERTED)
**Goal**: Consolidate Neo4j schema into version-controlled Cypher files with complete node/edge definitions derived from Pydantic models and seed data initialization
**Depends on**: Phase 13 (Recipe Management Fix)
**Requirements**: SCHEMA-01, SCHEMA-02, SCHEMA-03
**Success Criteria** (what must be TRUE):
  1. database/schema_init.cypher is eliminated; schema consolidated into master/neo4j/ (01-schema.cypher, 02-seeds.cypher)
  2. master/neo4j/01-schema.cypher is idempotent and complete: node types (Recipe, Model, Experiment, Checkpoint, Component) with all properties from Pydantic models, edge types with cardinality, constraints, triggers, indexes
  3. master/neo4j/02-seeds.cypher populates initial Component Nodes (all technique + framework combinations) and core Models (no-op if already exist)
  4. Schema initialization at Docker startup runs all Cypher files in order (01-schema.cypher → 02-seeds.cypher)
  5. All 5 node types and relationship types are fully documented in Cypher comments with Pydantic field mappings
**Plans**: 1 plan

Plans:
- [ ] 13-01-PLAN.md — Complete schema consolidation: Cypher generation from Pydantic models, seed data initialization, idempotent execution

## Progress

**Execution Order:**
Phases execute respecting dependency waves. Within a wave, phases can execute in parallel.
- Wave 1: 1 | Wave 2: 2, 3, 5 | Wave 3: 4, 6, 8 | Wave 4: 7 | Wave 5: 9 | Wave 6: 10 | Wave 7: 13 (Maintenance)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Shared Layer | 2/2 | Complete | 2026-04-10 |
| 2. Database Layer | 2/2 | Complete | 2026-04-11 |
| 3. Observability | 1/1 | Complete | 2026-04-13 |
| 4. Master API + Infrastructure | 3/3 | Complete | 2026-04-13 |
| 5. Storage Layer | 1/1 | Complete | 2026-04-13 |
| 6. Worker Layer | 3/3 | Complete | 2026-04-13 |
| 7. Generator Integration | 2/2 | Complete | 2026-04-13 |
| 8. Datamix | 1/1 | Complete | 2026-04-13 |
| 9. Testing | 2/2 | Created | 2026-04-13 |
| 10. Documentation | 0/1 | Not started | - |
| 13. Recipe Management Fix | 2/2 | Complete | 2026-04-15 |
| 13.1. Neo4j Schema Consolidation | 1/1 | Complete | 2026-04-15 |
