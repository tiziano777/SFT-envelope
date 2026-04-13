# Master API — Lineage Store and Experiment Coordination

The Master serves as the centralized coordination point for experiment lineage tracking. It runs as a FastAPI service alongside Neo4j and provides REST endpoints for Workers to report handshakes, checkpoint progress, status updates, merges, and async events.

**What it does:**
- Receives handshake requests and determines experiment strategy (NEW/RESUME/BRANCH/RETRY)
- Stores checkpoint metadata and artifact URIs in Neo4j
- Tracks config and code changes, triggering branching logic
- Provides observability and tracing via OpenTelemetry + Phoenix

**Who uses it:**
- **Workers** (GPU nodes): Send POST requests from daemon during training
- **Developers**: Query Neo4j graphs via Cypher or REST API
- **Operators**: Monitor traces in Phoenix UI, debug issues

## Quick Reference

| Component | Location | Purpose |
|-----------|----------|---------|
| **API Endpoints** | `/master/api.py` | 5 REST endpoints for Worker requests |
| **Lineage Logic** | `/master/controllers.py` | Strategy detection (NEW/RESUME/BRANCH) |
| **Neo4j Schema** | `/master/neo4j/` | Graph DB structure, constraints, triggers |
| **Error Handlers** | `/master/errors.py` | Semantic error responses (404, 409, 500) |
| **Storage** | `/master/storage/` | URIResolver, artifact writers |
| **Observability** | `/master/observability/` | OpenTelemetry tracing, Phoenix integration |

## API Endpoints Overview

| Endpoint | Method | Purpose | Response Code |
|----------|--------|---------|----------------|
| `/handshake` | POST | Determine strategy, create/resume experiment | 200, 400, 401, 409 |
| `/checkpoint_push` | POST | Store checkpoint + metrics + artifact URI | 201, 400, 401, 404, 409 |
| `/status_update` | POST | Update experiment lifecycle state | 200, 400, 401, 404 |
| `/merge` | POST | Combine N checkpoints into one | 201, 400, 401, 404, 409 |
| `/sync_event` | POST | Async event (metrics, logs, config change) | 200, 400, 401, 409 |
| `/health` | GET | Health check (readiness probe) | 200, 503 |

## Architecture

**Request Flow:**
```
Worker Daemon (GPU)
    ↓ HTTP POST
FastAPI (Master)
    ├─ X-API-Key middleware (auth)
    ├─ Pydantic validation
    └─ LineageController (strategy logic)
        ↓
    Neo4j (graph store)
    ├─ Create/query :Experiment nodes
    ├─ Create/query :Checkpoint nodes
    └─ Manage relations (DERIVED_FROM, RETRY_FROM, etc.)
```

**Key Design Points:**
- **Auth**: X-API-Key header on all requests (reject 401 if missing/invalid)
- **Validation**: All inputs validated with Pydantic at API boundary
- **Consistency**: ConsistencyGuard prevents circular lineage (source != target, max depth 50)
- **Async Processing**: /sync_event uses background queue for non-critical updates
- **Tracing**: All endpoints auto-instrumented with OpenTelemetry; manual spans on critical ops

## Configuration

### Environment Variables

| Variable | Default | Purpose | Example |
|----------|---------|---------|---------|
| `MASTER_PORT` | `8000` | FastAPI server port | `8000` |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j connection string | `bolt://neo4j:7687` |
| `NEO4J_USER` | `neo4j` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | `password` | Neo4j password | `secure-pass-123` |
| `X_API_KEY` | `dev-key-123` | Authentication token | Your secret key |
| `PHOENIX_HOST` | `localhost` | Phoenix server for tracing | `localhost` |
| `PHOENIX_PORT` | `6006` | Phoenix UI port | `6006` |
| `OBSERVABILITY_ENABLED` | `true` | Enable OpenTelemetry | `true` or `false` |

### Example .env

```bash
MASTER_PORT=8000
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-secure-password
X_API_KEY=your-api-key-here
PHOENIX_HOST=localhost
PHOENIX_PORT=6006
OBSERVABILITY_ENABLED=true
```

## Deployment

### Docker Compose (Recommended)

```bash
# Start Master API + Neo4j + Phoenix
make master-up

# Verify health
curl http://localhost:8000/health

# View logs
make master-logs

# Stop
make master-down
```

### Health Check

```bash
# Should return 200 if ready
curl http://localhost:8000/health

# Expected response:
# {"status": "ok", "neo4j": "connected"}
```

### Monitoring

**Phoenix UI**: http://localhost:6006
- View traces for all API calls
- Debug slow operations
- Check error rates

**Neo4j Browser**: http://localhost:7474
- Browse graph structure
- Write Cypher queries
- Inspect node properties

## Further Reading

Detailed documentation for each component:

- **[API Reference](lineage/api-reference.md)**: Request/response examples for all 5 endpoints
- **[Neo4j Schema](lineage/schema.md)**: Graph structure, node types, relations, constraints
- **[Architecture](lineage/architecture.md)**: System design, failure modes, security model
- **[Troubleshooting](lineage/troubleshooting.md)**: Common issues and debug steps

## Testing Master API

### Quick Test

```bash
# Start Master
make master-up

# Test handshake (should return 200 with strategy)
curl -X POST http://localhost:8000/handshake \
  -H "X-API-Key: dev-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "recipe_id": "lora_trl_7b",
    "exp_id": "e-test-001",
    "model_id": "llama-7b-instruct",
    "config_hash": "sha256abc123",
    "code_hash": "sha256def456",
    "req_hash": "sha256ghi789",
    "config_snapshot": {}
  }'
```

### Run Full Test Suite

```bash
pytest tests/api/ -v --cov=master
```
