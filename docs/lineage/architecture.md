# Lineage System Architecture

## Overview

The lineage system implements a **Worker-Master** pattern where workers (GPU nodes) track experiment progress and asynchronously sync with a centralized master (CPU node) that stores the complete lineage graph.

**Core principles:**
- **Decoupled**: Training proceeds unblocked even if lineage sync unavailable
- **Async-First**: All checkpoint syncs happen in background with retry; no network timeouts block train.py
- **Atomic State**: Local state persisted via tmp+rename; audit trail immutable
- **Traceable**: Every event has event_id, timestamp, source for debugging

## Architectural Layers

The lineage system spans 9 phases of development:

```
Phase 1: Shared Contracts
├─ ConfigSnapshot, ConfigHasher, DiffEngine
├─ Node types: ExperimentNode, CheckpointNode, RecipeNode, ModelNode, ComponentNode
└─ Transport envelopes: HandshakeRequest/Response, CheckpointPush, SyncEvent

Phase 2: Database
├─ Neo4j 5.x with 5 UNIQUE constraints
├─ APOC triggers for timestamps and orphan validation
└─ ExperimentRepository with idempotent Cypher queries

Phase 3: Observability
├─ OpenTelemetry SDK
├─ FastAPI auto-instrumentation
└─ Phoenix UI for trace visualization

Phase 4: Master API
├─ 5 REST endpoints
├─ LineageController with strategy logic
└─ Error handlers with semantic status codes

Phase 5: Storage
├─ URIResolver for artifact dispatch
└─ Pluggable backends (file, s3, nfs, worker, master)

Phase 6: Worker Layer
├─ WorkerDaemon for handshake and async push
├─ Connection layer (HTTP, SSH stubs)
└─ AsyncPusher with exponential backoff

Phase 7: Generator Integration
├─ inject_worker_middleware() copies worker code to scaffold
├─ run.sh.j2 orchestrates daemon lifecycle
└─ MergeTechnique plugin for checkpoint merging

Phase 8: Datamix
└─ Multi-source dataset support (independent of lineage)

Phase 9: Testing
├─ E2E test suite with real Neo4j
└─ All 4 strategies tested (NEW, RESUME, BRANCH, RETRY)
```

## Data Flow

**A checkpoint flows from Worker to Master:**

```
[Worker] train.py epoch 5, run 2
    ↓ (writes checkpoint to disk)
[Worker] daemon.pusher observes lineage/to_transfer/
    ↓ (reads checkpoint metadata)
[Worker] queues CheckpointPush event
    ↓ (async, with retry)
[Network] HTTP POST /checkpoint_push
    ↓
[Master] FastAPI validates request
    ↓
[Master] LineageController processes push
    ↓ (checks consistency)
[Master] Neo4j creates Checkpoint node
    ↓
[Master] returns 200 + checkpoint_id
    ↓
[Network] HTTP response
    ↓
[Worker] pusher deduplicates (event_id) and logs to transfer_log.jsonl
```

## Strategy Detection Logic

**Handshake determines strategy via decision tree:**

```
Handshake: find_experiment_by_hashes(config_hash, code_hash, req_hash)
    ├─ Found with all hashes matching? → RESUME
    │  (same config, same code, continue from last checkpoint)
    │
    ├─ Found but config_hash differs? → BRANCH
    │  (config changed, new direction)
    │
    ├─ Found but code_hash differs? → BRANCH
    │  (train.py changed)
    │
    ├─ Found but req_hash differs? → BRANCH
    │  (requirements.txt changed - should be rare)
    │
    ├─ Not found + seed/run specified? → RETRY
    │  (repeat with different seed for statistical validation)
    │
    └─ Not found + fresh start? → NEW
       (fresh experiment)
```

## Async Push with Retry

Daemon uses exponential backoff for failed pushes:

```
Attempt 1: immediate
Attempt 2: 2s delay
Attempt 3: 4s delay
Attempt 4: 8s delay
...
Attempt N: min(2^N, 300s) = max 5 min
Give up after: 10 attempts or 30 min timeout

During backoff:
- Training continues unblocked
- Local checkpoint queued in memory
- Event logged to transfer_log.jsonl
- On network recovery, daemon retries
```

## Failure Modes & Degradation

**Master unavailable during handshake:**
- Warning printed to stderr
- Setup continues in "degraded mode" (no exp_id)
- No lineage tracking until handshake succeeds
- Training proceeds normally

**Master unavailable during training:**
- Daemon queues pushes locally
- Syncs to transfer_log.jsonl
- Retries with exponential backoff
- Training unaffected

**Network timeout:**
- Daemon retries with backoff
- Training unaffected
- Events persisted locally

**Circular lineage detected:**
- Master rejects with 409 Conflict
- ConsistencyGuard prevents: source == target, depth > 50
- Daemon logs error and retries

## Security Model

**Authentication:**
- X-API-Key on all endpoints (reject 401 if missing)
- Token validated by middleware
- No other auth (assumes network isolation)

**Validation:**
- All inputs validated (Pydantic models at API boundary)
- Config hashes validated (SHA256)
- Checkpoint URIs validated

**Trust:**
- Master trusts Worker during handshake (must be on same network or VPN)
- No secrets transmitted (API keys in headers, not body)

**Audit:**
- transfer_log.jsonl immutable append-only audit trail
- Every event logged with event_id, timestamp, source
- Neo4j audit trail via created_at, updated_at timestamps

## Performance Characteristics

**Handshake:** < 100ms (Neo4j query + hash comparison)

**Checkpoint push:** < 500ms (Neo4j transaction + storage check)

**Worker daemon overhead:** < 5% CPU, < 50MB RAM (idle)

**Async push latency:** 1-5 seconds (depends on backoff attempt, no blocking)

## Next Steps / Further Reading

- **[API Reference](api-reference.md)**: Detailed endpoint documentation and examples
- **[Schema](schema.md)**: Neo4j node types, relations, constraints, indexes
- **[Troubleshooting](troubleshooting.md)**: Common issues and debugging steps
