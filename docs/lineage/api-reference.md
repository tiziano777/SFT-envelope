# Master API Reference

## Authentication

All endpoints require the X-API-Key header:

```bash
curl -H "X-API-Key: your-secret-key" http://localhost:8000/endpoint
```

Missing or invalid X-API-Key returns **401 Unauthorized**.

## Common Response Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | Success | Successful request |
| 201 | Created | New resource created |
| 400 | Bad Request | Validation error |
| 401 | Unauthorized | Missing/invalid X-API-Key |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Lineage violation, circular dependency |
| 500 | Server Error | Neo4j unavailable, internal error |

## Endpoints

### 1. POST /handshake

**Purpose**: Determine experiment strategy and create/resume experiment

**Headers:**
```
X-API-Key: your-secret-key
Content-Type: application/json
```

**Request Body:**
```json
{
  "recipe_id": "lora_trl_7b",
  "exp_id": "e-20260410-001",
  "model_id": "llama-7b-instruct",
  "config_hash": "sha256abc123def456",
  "code_hash": "sha256ghi789jkl012",
  "req_hash": "sha256mno345pqr678",
  "config_snapshot": {
    "experiment": {"name": "my-exp"},
    "training": {"technique": "grpo"}
  }
}
```

**Response 200 (OK):**
```json
{
  "strategy": "RESUME",
  "exp_id": "e-20260410-001",
  "latest_ckp_id": "e-001_c5_r2"
}
```

**Response 400 (Bad hash format):**
```json
{"error": "config_hash must be hex string of length 64"}
```

**Response 409 (Circular dependency):**
```json
{"error": "Circular dependency detected in lineage graph"}
```

**Notes:**
- Returns RESUME if all hashes match existing experiment
- Returns BRANCH if any hash differs (config changed, code changed, etc.)
- Returns NEW if no matching experiment found
- Returns RETRY if seed/run number specified in config_snapshot
- Worker creates marker files: `.handshake_done`, `.exp_id` with result

---

### 2. POST /checkpoint_push

**Purpose**: Store checkpoint metadata, metrics, and artifact URI

**Headers:**
```
X-API-Key: your-secret-key
Content-Type: application/json
```

**Request Body:**
```json
{
  "exp_id": "e-20260410-001",
  "ckp_id": "e-001_c5_r2",
  "epoch": 5,
  "run": 2,
  "metrics": {
    "loss": 0.23,
    "accuracy": 0.94,
    "reward_mean": 0.72
  },
  "uri": "file:///checkpoints/e-001_c5_r2/model.bin"
}
```

**Response 201 (Created):**
```json
{
  "ckp_id": "e-001_c5_r2",
  "created_at": "2026-04-13T10:00:00Z"
}
```

**Response 400 (Invalid metrics JSON):**
```json
{"error": "metrics must be valid JSON object"}
```

**Response 404 (Experiment not found):**
```json
{"error": "Experiment e-20260410-001 not found"}
```

**Response 409 (URI conflict):**
```json
{"error": "Artifact not found at file:///checkpoints/e-001_c5_r2/model.bin"}
```

**Notes:**
- Idempotent on ckp_id: same event_id returns 200 without duplicate
- Stores artifact URI (not the artifact itself) in Neo4j
- Creates PRODUCED_BY relation to experiment
- Validates URI scheme (file://, s3://, nfs://, etc.)

---

### 3. POST /status_update

**Purpose**: Update experiment lifecycle state

**Headers:**
```
X-API-Key: your-secret-key
Content-Type: application/json
```

**Request Body:**
```json
{
  "exp_id": "e-20260410-001",
  "status": "training",
  "timestamp": "2026-04-13T10:05:00Z"
}
```

**Response 200 (OK):**
```json
{
  "exp_id": "e-20260410-001",
  "status": "training"
}
```

**Response 404 (Experiment not found):**
```json
{"error": "Experiment e-20260410-001 not found"}
```

**Notes:**
- Valid statuses: `created`, `training`, `completed`, `failed`
- Timestamp optional (defaults to now)
- Non-blocking call (daemon continues regardless)

---

### 4. POST /merge

**Purpose**: Combine N source checkpoints into one merged checkpoint

**Headers:**
```
X-API-Key: your-secret-key
Content-Type: application/json
```

**Request Body:**
```json
{
  "exp_id": "e-20260410-001",
  "source_ckp_ids": ["e-001_c1_r1", "e-001_c3_r1"],
  "merge_method": "linear",
  "weights": [0.4, 0.6]
}
```

**Response 201 (Merged):**
```json
{
  "merged_ckp_id": "e-001_merged_20260413",
  "source_ckp_ids": ["e-001_c1_r1", "e-001_c3_r1"],
  "created_at": "2026-04-13T10:10:00Z"
}
```

**Response 400 (Weights don't sum to 1.0):**
```json
{"error": "weights must sum to 1.0, got 0.95"}
```

**Response 404 (Source checkpoint not found):**
```json
{"error": "Checkpoint e-001_c1_r1 not found"}
```

**Response 409 (Circular dependency or incompatible):**
```json
{"error": "Source checkpoints have incompatible base models"}
```

**Notes:**
- Merge must have valid lineage (no cycles)
- Weights optional (equal distribution by default)
- Source checkpoints must have same base model architecture
- Creates MERGED_FROM relations to all source checkpoints

---

### 5. POST /sync_event

**Purpose**: Async event processing (metrics updates, logs, config changes)

**Headers:**
```
X-API-Key: your-secret-key
Content-Type: application/json
```

**Request Body:**
```json
{
  "exp_id": "e-20260410-001",
  "event_id": "evt-20260413-001",
  "event_type": "metrics_update",
  "payload": {
    "step": 100,
    "loss": 0.21,
    "timestamp": "2026-04-13T10:05:15Z"
  }
}
```

**Response 200 (Queued):**
```json
{
  "event_id": "evt-20260413-001",
  "status": "queued"
}
```

**Response 400 (Unknown event_type):**
```json
{"error": "Unknown event_type: 'invalid_type'"}
```

**Response 409 (Duplicate event_id):**
```json
{
  "event_id": "evt-20260413-001",
  "status": "queued",
  "note": "Duplicate event_id (idempotent)"
}
```

**Notes:**
- Idempotent: duplicate event_ids return 200 (no reprocessing)
- Queued in background (non-blocking)
- Valid event_types: `metrics_update`, `log_event`, `config_changed`, custom
- Payload structure flexible (depends on event_type)

---

## Common Workflows

### New Experiment Workflow

```
1. POST /handshake
   ↓ Returns: strategy=NEW, exp_id=e-001
2. [training starts...]
3. POST /checkpoint_push (repeat multiple times)
   ↓ ckp1 created, ckp2 created, ckp3 created
4. POST /status_update
   ↓ status: training → completed
5. Experiment complete in lineage graph
```

### Resume Experiment Workflow

```
1. POST /handshake (same config_hash, code_hash)
   ↓ Returns: strategy=RESUME, exp_id=e-001, latest_ckp_id=e-001_c5
2. [training resumes from epoch 6...]
3. POST /checkpoint_push (new ckp: c6, c7, ...)
4. POST /status_update
   ↓ status: completed
5. Previous and new checkpoints linked in same experiment
```

### Merge Workflow

```
1. [two separate training runs completed]
   ↓ exp1 with ckp1, ckp2, ckp3
   ↓ exp2 with ckp1', ckp2', ckp3'
2. POST /handshake (technique: merge)
   ↓ Returns: strategy=NEW, exp_id=e-merge-001
3. POST /merge
   ↓ Combines exp1.ckp2 (40%) + exp2.ckp2' (60%)
4. POST /checkpoint_push (merged artifact)
5. Merged checkpoint linked via MERGED_FROM relations
```

### Error Handling

```python
import httpx

async def push_checkpoint(url, key, payload):
    headers = {"X-API-Key": key}
    try:
        resp = await httpx.post(f"{url}/checkpoint_push", json=payload, headers=headers)
        if resp.status_code == 201:
            return resp.json()
        elif resp.status_code == 404:
            print(f"Experiment not found: {resp.json()['error']}")
        elif resp.status_code == 409:
            print(f"Lineage conflict: {resp.json()['error']}")
            # Retry with backoff
        else:
            print(f"Unexpected error: {resp.status_code}")
    except httpx.ConnectError:
        print("Master unavailable, queuing for retry...")
```
