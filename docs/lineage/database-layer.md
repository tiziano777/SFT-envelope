# Database Layer — Neo4j Lineage Storage

## Overview

The Database Layer manages experiment lineage data in Neo4j 5.x, providing atomic transactions, automatic timestamp management via APOC triggers, and async-first Python API.

**Key Responsibility:**
- Store and retrieve experiment nodes (5 types: Recipe, Model, Experiment, Checkpoint, Component)
- Enforce UNIQUE constraints and referential integrity through APOC triggers
- Provide idempotent CRUD operations for handshake and checkpoint sync workflows
- Enable querying experiments by hash for branching detection

---

## Architecture

### Neo4j Data Model

**Nodes:**
- `Recipe` — Training technique definition
- `Model` — Base model (llama-7b, mistral-7b, etc.)
- `Experiment` — Training run instance
- `Checkpoint` — Saved model artifact (epoch/run)
- `Component` — Framework/technique pair

**Relations (8 types):**
| Relation | From | To | Purpose |
|----------|------|----|-|
| `PRODUCED_BY` | Checkpoint | Experiment | Checkpoint belongs to experiment |
| `DERIVED_FROM` | Experiment | Experiment | Config/code change → branch |
| `RETRY_FROM` | Experiment | Experiment | Same config, different seed |
| `MERGED_FROM` | Checkpoint | Checkpoint | Merge multiple checkpoints |
| `USES_TECHNIQUE` | Experiment | Component | Experiment uses technique |
| `USES_MODEL` | Experiment | Model | Experiment uses base model |
| `USES_RECIPE` | Experiment | Recipe | Experiment from recipe |
| `OPTIMIZED_WITH` | Experiment | Component | Optimization setting |

---

## Schema & Constraints

### UNIQUE Constraints (5)

```cypher
CREATE CONSTRAINT unique_recipe_id FOR (r:Recipe) REQUIRE r.recipe_id IS UNIQUE;
CREATE CONSTRAINT unique_exp_id FOR (e:Experiment) REQUIRE e.exp_id IS UNIQUE;
CREATE CONSTRAINT unique_ckp_id FOR (c:Checkpoint) REQUIRE c.ckp_id IS UNIQUE;
CREATE CONSTRAINT unique_model_name FOR (m:Model) REQUIRE m.model_name IS UNIQUE;
CREATE CONSTRAINT composite_component_key FOR (co:Component) REQUIRE (co.technique_code, co.framework_code) IS UNIQUE;
```

### BTREE Indexes (3)

```cypher
CREATE INDEX idx_experiment_config_hash FOR (e:Experiment) ON (e.config_hash);
CREATE INDEX idx_experiment_code_hash FOR (e:Experiment) ON (e.code_hash);
CREATE INDEX idx_experiment_req_hash FOR (e:Experiment) ON (e.req_hash);
```

**Purpose:** Handshake queries filter experiments by config/code/requirements hashes to detect branching.

---

## APOC Triggers

### Trigger 1: Automatic `created_at`

```cypher
CALL apoc.trigger.install('neo4j', 'created_at_trigger',
  'UNWIND apoc.trigger.nodesByLabel($createdNodes, null) AS node
   SET node.created_at = datetime()',
  {phase: 'before'})
```

**Effect:** Every node automatically gets `created_at = current timestamp` on creation.

### Trigger 2: Automatic `updated_at`

```cypher
CALL apoc.trigger.install('neo4j', 'updated_at_trigger',
  'UNWIND apoc.trigger.nodesByLabel($changedNodes, null) AS node
   SET node.updated_at = datetime()',
  {phase: 'before'})
```

**Effect:** Every node property update sets `updated_at = current timestamp`.

### Trigger 3: Orphan Checkpoint Validation

```cypher
CALL apoc.trigger.install('neo4j', 'orphan_checkpoint_validation',
  'UNWIND apoc.trigger.nodesByLabel($createdNodes, "Checkpoint") AS ckp
   WHERE NOT (ckp)-[:PRODUCED_BY|DERIVED_FROM|RETRY_FROM|MERGED_FROM]->()
     AND NOT ckp.is_merging = true
   CALL apoc.util.validate(false, "Checkpoint %s is orphan and is_merging != true", [ckp.ckp_id])',
  {phase: 'after'})
```

**Effect:** Prevents creating standalone Checkpoint nodes (must have parent relation or `is_merging=true`).

---

## Repository API

### Class: `ExperimentRepositoryAsync`

Async Neo4j implementation of `BaseExperimentRepository` ABC.

```python
from master.neo4j import ExperimentRepositoryAsync, get_driver

driver = await get_driver()
repo = ExperimentRepositoryAsync(driver)
```

### Core Methods

#### `create_experiment()`

**Signature:**
```python
async def create_experiment(
    recipe_id: str,
    exp_id: str,
    model_id: str,
    config_hash: str,
    code_hash: str,
    req_hash: str,
    config_snapshot: ConfigSnapshot,
) -> ExperimentNode:
```

**Implementation:** `MERGE` on `exp_id` for idempotency. Called during handshake to create or retrieve experiment.

**Example:**
```python
exp = await repo.create_experiment(
    recipe_id="lora_trl_7b",
    exp_id="e-20260410-001",
    model_id="llama-7b",
    config_hash="sha256_config",
    code_hash="sha256_train_py",
    req_hash="sha256_requirements",
    config_snapshot=snapshot
)
```

#### `upsert_checkpoint()`

**Signature:**
```python
async def upsert_checkpoint(
    exp_id: str,
    ckp_id: str,
    epoch: int,
    run: int,
    metrics_snapshot: dict,
    uri: Optional[str] = None,
) -> CheckpointNode:
```

**Implementation:** Atomic transaction creating Checkpoint + `PRODUCED_BY` relation. Metrics stored as JSON.

**Example:**
```python
ckp = await repo.upsert_checkpoint(
    exp_id="e-20260410-001",
    ckp_id="e-20260410-001_c5_r2",
    epoch=5,
    run=2,
    metrics_snapshot={"loss": 0.23, "accuracy": 0.94},
    uri="file:///checkpoints/e-20260410-001_c5_r2/model.bin"
)
```

#### `find_experiment_by_hashes()`

**Signature:**
```python
async def find_experiment_by_hashes(
    config_hash: str,
    code_hash: str,
    req_hash: str,
) -> Optional[ExperimentNode]:
```

**Implementation:** Query all 3 hashes with WHERE clause. Used by handshake to detect RESUME vs NEW vs BRANCH.

**Example:**
```python
existing_exp = await repo.find_experiment_by_hashes(
    config_hash="h1",
    code_hash="h2",
    req_hash="h3"
)
if existing_exp:
    return Strategy.RESUME  # or BRANCH if config changed
else:
    return Strategy.NEW
```

#### `get_latest_checkpoint()`

**Signature:**
```python
async def get_latest_checkpoint(self, exp_id: str) -> Optional[CheckpointNode]:
```

**Implementation:** Orders by `epoch DESC, run DESC`, `LIMIT 1`. Used for RESUME strategy baseline.

#### `create_merged_checkpoint()`

**Signature:**
```python
async def create_merged_checkpoint(
    exp_id: str,
    merged_ckp_id: str,
    source_ckp_ids: list[str],
    epoch: int,
) -> CheckpointNode:
```

**Implementation:** Creates checkpoint with `is_merging=true` + N `MERGED_FROM` relations.

#### `create_derived_from_relation()`

**Signature:**
```python
async def create_derived_from_relation(
    source_exp_id: str,
    target_exp_id: str,
    diff_patch: dict,
) -> None:
```

**Implementation:** Creates `DERIVED_FROM` relation with `diff_patch` as relation property (JSON).

#### `create_retry_from_relation()`

**Signature:**
```python
async def create_retry_from_relation(
    source_exp_id: str,
    target_exp_id: str,
) -> None:
```

**Implementation:** Creates `RETRY_FROM` relation (for same config, different seed).

#### `get_experiment()`

**Signature:**
```python
async def get_experiment(self, exp_id: str) -> Optional[ExperimentNode]:
```

**Implementation:** Simple query by `exp_id`.

---

## Connection Pooling

### Neo4j Driver Singleton

**Pattern:**
```python
from master.neo4j import get_driver, close_driver

# Get or create singleton
driver = await get_driver()

# Use driver
async with driver.session() as session:
    result = await session.run("MATCH (e:Experiment) RETURN COUNT(*)")

# Close on shutdown
await close_driver()
```

**Configuration (via environment variables):**
- `NEO4J_URI` — Connection string (default: `bolt://localhost:7687`)
- `NEO4J_USER` — Username (default: `neo4j`)
- `NEO4J_PASSWORD` — Password (default: `password`)
- `NEO4J_POOL_SIZE` — Max pool size (default: 50)

**Example:**
```bash
export NEO4J_POOL_SIZE=100
export NEO4J_URI=bolt://prod-neo4j:7687
```

---

## Atomic Transactions

All multi-step operations use explicit transactions for consistency:

```python
async with driver.session() as session:
    tx = session.begin_transaction()
    try:
        # Step 1: Create checkpoint
        ckp = await tx.run("CREATE (c:Checkpoint {ckp_id: ...}) RETURN c")

        # Step 2: Create relation
        await tx.run("MATCH ... MERGE (c)-[:PRODUCED_BY]->(e)")

        await tx.commit()
    except Exception as e:
        await tx.rollback()
        raise
```

---

## Error Handling

### Exception Hierarchy

```
RepositoryError (base)
├── ExperimentAlreadyExists
└── CheckpointNotFound
```

**Usage:**
```python
from master.neo4j import RepositoryError, ExperimentAlreadyExists

try:
    exp = await repo.create_experiment(...)
except ExperimentAlreadyExists:
    logger.warning("Experiment already exists")
except RepositoryError as e:
    logger.error(f"Database error: {e}")
```

---

## Testing

### Test Setup (conftest.py)

```python
@pytest.fixture(scope="session")
async def neo4j_container(docker_client):
    """Start Neo4j 5.22 with APOC plugin."""
    container = docker_client.containers.run(
        "neo4j:5.22",
        environment={
            "NEO4J_PLUGINS": '["apoc"]',
            "NEO4J_apoc_trigger_enabled": "true",
        },
        ports={"7687/tcp": 7687},
    )
    ...
    return container

@pytest.fixture
async def neo4j_session(neo4j_driver):
    """Session with schema and triggers pre-loaded."""
    async with neo4j_driver.session() as session:
        await session.run(open("master/neo4j/schema.cypher").read())
        await session.run(open("master/neo4j/triggers.cypher").read())
        yield session
        await session.run("MATCH (n) DETACH DELETE n")
```

### Sample Test

```python
@pytest.mark.asyncio
async def test_create_experiment_idempotent(repo):
    """MERGE ensures idempotency."""
    exp1 = await repo.create_experiment(exp_id="e-001", ...)
    exp2 = await repo.create_experiment(exp_id="e-001", ...)
    assert exp1.created_at == exp2.created_at
```

---

## Performance Considerations

- **Indexes:** BTREE on experiment hashes speeds up `find_experiment_by_hashes()` queries (handshake)
- **Connection Pooling:** Configurable pool size balances resource usage vs. throughput
- **Atomic Transactions:** Multi-step operations (upsert + relations) protected by transaction scope
- **APOC Triggers:** Run on database side (no round-trip latency for timestamp updates)

---

## Future Enhancements

- [ ] Pagination for checkpoint queries
- [ ] Batch checkpoint creation with single transaction
- [ ] Custom indexes on experiment status/state
- [ ] Read replicas for query load distribution

---

*Database Layer documentation — Phase 2-02b (2026-04-13)*
