---
phase: 04-master-api
type: context
depends_on: [01-shared-layer, 02-database-layer, 03-observability, 05-storage-layer]
---

# Phase 4 Context: Master API + Infrastructure

## Goal

Implement the Master API that accepts Worker requests, applies lineage logic (strategy determination, checkpoint validation, merge operations), and coordinates with Neo4j database and artifact storage. Integrate all Wave 2-3 components into a production-ready service running in Docker.

## Requirements (from ROADMAP)

### MAPI-01 through MAPI-10
1. **Handshake Logic** — Determine strategy (NEW, RESUME, BRANCH, RETRY) based on config hashes
2. **Experiment Discovery** — Find existing experiments by hashes, handle collisions
3. **Strategy Routing** — Route to appropriate experiment path based on strategy
4. **Checkpoint Persistence** — Validate and store checkpoints in Neo4j
5. **Artifact Management** — Persist artifacts via URIResolver to backends
6. **Status Tracking** — Update experiment/checkpoint status through lifecycle
7. **Merge Orchestration** — Coordinate lineage merges between experiments
8. **Event Sync** — Process sync events from worker daemon
9. **Consistency Guardrails** — Prevent circular lineage relationships
10. **API Error Handling** — Return semantically correct error responses

### INFR-01 through INFR-05
1. **Docker Deployment** — Master API runs in container with health checks
2. **Docker Compose** — Orchestrate Neo4j + Phoenix + Master API stack
3. **Makefile Targets** — make master-up/down/logs/test for developer workflow
4. **Health Checks** — /health endpoint with readiness/liveness semantics
5. **Graceful Shutdown** — Signal handling, database connection cleanup

## Key Dependencies (All Satisfied ✓)

### From Phase 1 (Shared Layer)
- HandshakeRequest, HandshakeResponse models
- CheckpointPush, SyncEvent, StatusUpdate envelopes
- Strategy enum (NEW, RESUME, BRANCH, RETRY)
- ConfigHasher, DiffEngine, ConfigSnapshot
- BaseNode, Experiment/Checkpoint node types

### From Phase 2 (Database Layer)
- Neo4jClient (async driver, pooling, healthchecks)
- BaseExperimentRepository ABC
- ExperimentRepositoryAsync (find_by_hashes, create, upsert, get_latest_checkpoint)
- Schema with APOC triggers (timestamps, validation)

### From Phase 3 (Observability)
- setup_tracing(), get_tracer() for Phoenix OTEL
- FastAPIInstrumentor (auto-instrumentation)
- Manual span context managers
- Graceful degradation when Phoenix unavailable

### From Phase 5 (Storage Layer)
- URIResolver for dispatching to backends
- BaseStorageWriter ABC
- LocalStorageWriter for file:// URIs
- Error hierarchy (StorageError, FileNotFound, URINotSupported)

## Design Patterns from Earlier Phases

### TDD Workflow
- RED: Write failing tests for new endpoints
- GREEN: Implement endpoint logic
- REFACTOR: Extract controllers, middleware, validators

### Async-First
- All I/O wrapped with asyncio
- Database queries are async
- Storage writes via URIResolver are async

### ABC-Based Extensibility
- BaseExperimentRepository for different DB backends
- BaseStorageWriter for different storage backends
- Services inherit from abstract bases

### Error Hierarchy
- Custom exceptions (ExperimentNotFound, ConflictError, ValidationError, etc.)
- Graceful degradation (tracing failures don't crash API)
- Semantic HTTP status codes (404, 409, 400, 500)

## Critical Constraints

1. **Idempotency** — Same request twice should not duplicate checkpoints
2. **Strategy Determination** — Must check config hashes, not assume NEW
3. **Circular Dependency Prevention** — ConsistencyGuard rejects cycles in merge
4. **No Blocking I/O** — All Neo4j and storage calls are async
5. **Trace Visibility** — Every endpoint has manual spans with attributes
6. **Configuration via Environment** — No hardcoded DB URIs, storage backends, etc.

## Files to Create/Modify

**Core API (master/):**
- master/api.py (extend with business logic)
- master/controllers/ (new) — LineageController, CheckpointController, etc.
- master/middleware/ (new) — Auth, validation, error handling
- master/validators/ (new) — Request validation rules

**Infrastructure:**
- docker-compose.yml (update with health checks)
- Dockerfile.master (add startup logic)
- Makefile (extend targets)
- pyproject.toml (add [master] dependencies)

**Tests (tests/):**
- tests/api/test_handshake.py — All 4 strategies
- tests/api/test_checkpoint.py — CRUD operations
- tests/api/test_merge.py — Lineage operations
- tests/api/test_errors.py — Error scenarios

**Documentation:**
- docs/MASTER_API.md — API reference, examples
- Update ROADMAP.md

## Next Steps

1. **Create PLAN.md** — 3 detailed plans (endpoints, auth/validation, infrastructure)
2. **Execute Wave 3** — Parallel with Phase 6 (Worker) and Phase 8 (Datamix)
3. **Integration** — E2E testing with simulated workers (Phase 9)
