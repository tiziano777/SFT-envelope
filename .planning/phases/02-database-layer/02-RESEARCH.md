# Phase 2: Database Layer - Research

**Researched:** 2026-04-13
**Domain:** Neo4j 5.x graph constraints, APOC triggers, Python driver pooling, idempotent Cypher patterns
**Confidence:** HIGH

## Summary

Phase 2 implements the Master's Neo4j layer — persistent storage and querying of experiment lineage data. Core deliverables: (1) Neo4j schema with UNIQUE constraints on all node identifiers and composite key for Component nodes; (2) APOC triggers for automatic created_at/updated_at timestamps and validation guards against orphan checkpoints; (3) Python driver singleton with connection pooling and idempotent query patterns; (4) ExperimentRepository ABC with atomic Cypher transactions for all CRUD operations; (5) efficient handshake query using hash indexes; (6) checkpoint merge supporting N-ary MERGED_FROM relationships.

The architecture document (LINEAGE_SYSTEM_ARCHITECTURE.md, Sections 3.1-3.4 and 6.1) specifies all node types, relations, constraint types, and trigger logic. Neo4j 5.x is stable and mature; the neo4j-python-driver 5.28.3 (LTS) is production-ready and supports all required features. APOC Core 5.26+ is the standard approach for triggers since Neo4j lacks native trigger support.

**Primary recommendation:** Use Neo4j 5.x UNIQUE constraints + APOC triggers for schema enforcement. Use neo4j-python-driver 5.28.3 with connection pooling (default pool size 50). Implement ExperimentRepository with MERGE-based idempotency for all upsert operations. Index hash fields (config_hash, code_hash, req_hash) for O(1) handshake lookups. Use Python ABC for repository pattern to enable testing with mock implementations.

<user_constraints>
## User Constraints (from Architecture Document)

### Locked Decisions (Phase Requirements)
- **DB-01:** Neo4j UNIQUE constraints on recipe_id, exp_id, ckp_id, model_name; composite UNIQUE on (technique_code, framework_code) for Component
- **DB-02:** APOC triggers for automatic created_at/updated_at timestamps on node creation and property updates
- **DB-03:** APOC validation triggers to prevent orphan checkpoints (except those with is_merging=true for merged checkpoints)
- **DB-04:** Neo4j driver singleton with connection pooling; thread-safe session management; configuration via environment variables
- **DB-05:** ExperimentRepository with idempotent MERGE patterns for upsert_checkpoint; atomic Cypher transactions
- **DB-06:** find_experiment_by_hashes(config_hash, code_hash, req_hash) for handshake strategy determination
- **DB-07:** get_latest_checkpoint(exp_id) for RESUME logic to retrieve most recent checkpoint
- **DB-08:** create_merged_checkpoint with N MERGED_FROM relations for multi-source checkpoint merging

### Claude's Discretion (Options to Research)
- Connection pool size tuning (default 50 per driver docs; may need adjustment based on load testing)
- APOC trigger phases (before vs. after) for performance optimization
- Indexing strategy: single-field indexes vs. composite indexes for hash lookups
- Whether to use `apoc.util.validate` vs. custom Cypher constraints for validation
- Repository method signatures and transaction boundaries (single transaction per method vs. larger atomic blocks)

### Deferred Ideas (OUT OF SCOPE)
- S3/NFS storage writer implementations (marked as "stubs" in architecture)
- Advanced query optimization (query analysis comes after V1)
- Cluster deployment (single-node Neo4j 5.x Docker container is target)
- Backup/recovery procedures (not specified in phase scope)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DB-01 | UNIQUE constraints on recipe_id, exp_id, ckp_id, model_name; composite UNIQUE (technique_code, framework_code) | Neo4j 5.x supports both single-property and composite UNIQUE constraints via CREATE CONSTRAINT syntax. VERIFIED: Official docs. |
| DB-02 | APOC triggers for created_at/updated_at timestamps on creation and update events | APOC 5.26+ includes apoc.trigger.install with phases. VERIFIED: trigger install available in 5.x. |
| DB-03 | Validation trigger prevents orphan Checkpoint nodes (except is_merging=true for merged) | APOC apoc.util.validate function validates Cypher conditions; apoc.trigger.install can encapsulate validation logic. VERIFIED: trigger pattern in architecture doc. |
| DB-04 | Neo4j driver singleton with connection pooling, thread-safe sessions, env-var configuration | neo4j-python-driver 5.28.3 LTS supports GraphDatabase.driver with pool configuration. VERIFIED: driver version confirmed. |
| DB-05 | ExperimentRepository with idempotent MERGE patterns, atomic transactions | MERGE statement in Cypher provides idempotency with ON CREATE/ON MATCH guards. VERIFIED: Cypher MERGE semantics. |
| DB-06 | find_experiment_by_hashes queries by (config_hash, code_hash, req_hash) triple | Requires indexes on these fields for fast lookup. Index creation in schema.cypher. VERIFIED: indexing needed for handshake performance. |
| DB-07 | get_latest_checkpoint(exp_id) returns most recent checkpoint by epoch | Query via (exp)-[:PRODUCED]->(ckp) ordered by ckp.epoch DESC LIMIT 1. VERIFIED: pattern in architecture doc. |
| DB-08 | create_merged_checkpoint with N MERGED_FROM relations; supports multi-source merge | Single transaction: CREATE checkpoint, then for each source: CREATE (new_ckp)-[:MERGED_FROM]->(src_ckp). VERIFIED: architecture doc 7.5. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard | Source |
|---------|---------|---------|-------------|--------|
| neo4j-python-driver | 5.28.3 LTS | Database connectivity, session/transaction management, query execution | Latest 5.x LTS release (Jan 2026); v6.0 released Sept 2025 but 5.x is more stable for Neo4j 5.x databases | [VERIFIED: GitHub releases] |
| Neo4j (server) | 5.x | Graph database engine | Stable release; APOC plugin available; used in architecture doc | [VERIFIED: architecture doc Section 11.1] |
| APOC Core | 5.26+ | Triggers, utilities, validation procedures | Standard Neo4j extension; only mechanism for trigger support (Neo4j lacks native triggers) | [VERIFIED: installed via docker-compose NEO4J_PLUGINS] |
| pydantic | 2.12.5 | Model serialization for Cypher parameter binding | Already a project dependency; works with neo4j driver via model_dump() | [VERIFIED: Phase 1 uses pydantic 2.12.5] |
| fastapi | 0.110+ (future) | Will consume repository methods in Phase 4 API layer | Existing project intent; prepare repository for async if FastAPI uses async | [ASSUMED: Phase 4 uses FastAPI] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.2+ | Unit and integration tests for repository | All repository methods require test coverage |
| docker-compose | (latest) | Neo4j + APOC + Phoenix stack orchestration | Docker environment for local dev and CI |
| Neo4j Browser | (any) | Manual schema inspection, test queries | Development and troubleshooting |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| neo4j-python-driver 5.28.3 | neo4j-python-driver 6.0.x | v6.0 has breaking API changes; unnecessary upgrade risk for Neo4j 5.x databases. Stay on 5.x. |
| Neo4j 5.x | Neo4j 4.x | Architecture doc specifies Neo4j 5.x for UNIQUE composite constraints and improved trigger support. |
| APOC triggers | Custom application logic (polling) | Polling adds latency and system load; triggers are atomic at database level; standard Neo4j approach. |
| Python driver pooling | Manual connection management | Driver pooling handles reconnection, thread-safety, resource cleanup automatically. |
| Single ExperimentRepository ABC | Separate classes per operation | ABC pattern allows test mocking, dependency injection, consistent interface. |

**Installation (pyproject.toml extras [master]):**
```toml
[project.optional-dependencies]
master = [
    "neo4j>=5.0,<6.0",              # Stay on 5.x for now
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "pydantic>=2.0",
    "arize-phoenix-otel>=0.6",      # Phase 3 observability
    "opentelemetry-sdk>=1.24",
    "opentelemetry-exporter-otlp-proto-grpc>=1.24",
]
```

**Version verification:**
```bash
pip index versions neo4j  # Confirm 5.28.3 is latest in 5.x
```

## Architecture Patterns

### Recommended Project Structure
```
master/
├── neo4j/
│   ├── __init__.py
│   ├── client.py              # Driver singleton, pool config
│   ├── repository.py          # ExperimentRepository ABC + implementation
│   ├── schema.cypher          # UNIQUE constraints, indexes
│   ├── triggers.cypher        # APOC trigger definitions
│   └── errors.py              # Custom exception types
├── api/
│   ├── routes.py              # Will import repository
│   └── lineage_controller.py  # Handshake logic
└── docker-compose.yml         # Neo4j service with APOC plugin
```

### Pattern 1: Neo4j Connection Pooling

**What:** Single driver instance with connection pooling, thread-safe sessions.
**When to use:** All database operations use the global driver singleton.
**Example (master/neo4j/client.py):**
```python
# Source: neo4j-python-driver 5.28.3 best practices
from __future__ import annotations

import os
from typing import Optional

from neo4j import GraphDatabase, Driver

_driver: Optional[Driver] = None

def get_driver() -> Driver:
    """Returns singleton Neo4j driver with connection pooling.

    Configuration via environment variables:
    - NEO4J_URI: database URI (default: bolt://localhost:7687)
    - NEO4J_USER: username (default: neo4j)
    - NEO4J_PASSWORD: password (required)

    Pool configuration:
    - max_connection_pool_size: 50 (default, tunable via NEO4J_POOL_SIZE)
    - connection_timeout: 30 (seconds, tunable via NEO4J_CONN_TIMEOUT)
    """
    global _driver
    if _driver is not None:
        return _driver

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "")
    pool_size = int(os.getenv("NEO4J_POOL_SIZE", "50"))
    conn_timeout = int(os.getenv("NEO4J_CONN_TIMEOUT", "30"))

    if not password:
        raise ValueError("NEO4J_PASSWORD environment variable is required")

    _driver = GraphDatabase.driver(
        uri,
        auth=(user, password),
        max_connection_pool_size=pool_size,
        connection_timeout=conn_timeout,
    )
    return _driver

def close_driver() -> None:
    """Close driver and release resources. Call on app shutdown."""
    global _driver
    if _driver:
        _driver.close()
        _driver = None
```

### Pattern 2: Repository ABC with Idempotent MERGE

**What:** Abstract base class defining interface; concrete implementation uses MERGE for idempotency.
**When to use:** All repository methods follow this pattern to enable mocking in tests.
**Example (master/neo4j/repository.py):**
```python
# Source: LINEAGE_SYSTEM_ARCHITECTURE.md Section 6.1 + DB-05
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
import json

from envelope.middleware.shared import ExperimentNode, CheckpointNode
from neo4j import Driver, Transaction

class ExperimentRepository(ABC):
    """Abstract repository for experiment lineage queries."""

    @abstractmethod
    def upsert_checkpoint(self, ckp: CheckpointNode) -> str:
        """Idempotent checkpoint create/update. Returns ckp_id."""
        pass

    @abstractmethod
    def find_experiment_by_hashes(
        self,
        config_hash: str,
        code_hash: str,
        req_hash: str
    ) -> Optional[ExperimentNode]:
        """Query by triple hash for handshake strategy. Returns experiment or None."""
        pass

class Neo4jExperimentRepository(ExperimentRepository):
    """Concrete implementation using neo4j-python-driver."""

    def __init__(self, driver: Driver):
        self.driver = driver

    def upsert_checkpoint(self, ckp: CheckpointNode) -> str:
        """MERGE checkpoint by ckp_id, set all properties atomically."""
        with self.driver.session() as session:
            result = session.run(
                """
                MERGE (c:Checkpoint {ckp_id: $ckp_id})
                ON CREATE SET
                  c.epoch = $epoch,
                  c.run = $run,
                  c.metrics_snapshot = $metrics_snapshot,
                  c.uri = $uri,
                  c.is_usable = $is_usable,
                  c.is_merging = $is_merging,
                  c.description = $description
                ON MATCH SET
                  c.uri = $uri,
                  c.is_usable = $is_usable,
                  c.metrics_snapshot = $metrics_snapshot
                RETURN c.ckp_id AS ckp_id
                """,
                ckp_id=ckp.ckp_id,
                epoch=ckp.epoch,
                run=ckp.run,
                metrics_snapshot=json.dumps(ckp.metrics_snapshot) if ckp.metrics_snapshot else "{}",
                uri=ckp.uri,
                is_usable=ckp.is_usable,
                is_merging=ckp.is_merging,
                description=ckp.description,
            )
            return result.single()["ckp_id"]

    def find_experiment_by_hashes(
        self,
        config_hash: str,
        code_hash: str,
        req_hash: str
    ) -> Optional[ExperimentNode]:
        """Query with indexed hash lookup. Requires indexes on hash fields (Schema phase)."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (e:Experiment)
                WHERE e.hash_committed_code = $code_hash
                  AND e.config_hash = $config_hash
                  AND e.req_hash = $req_hash
                RETURN e
                LIMIT 1
                """,
                config_hash=config_hash,
                code_hash=code_hash,
                req_hash=req_hash,
            )
            record = result.single()
            if record:
                # Deserialize node from Neo4j to ExperimentNode
                node_dict = record["e"]
                return ExperimentNode(**node_dict)
            return None
```

### Pattern 3: APOC Trigger for Timestamps

**What:** Trigger installed at Neo4j startup that automatically sets created_at and updated_at.
**When to use:** All nodes should have automatic timestamp management; no manual timestamp code needed.
**Example (master/neo4j/triggers.cypher):**
```cypher
-- Source: LINEAGE_SYSTEM_ARCHITECTURE.md Section 3.4
-- Install at database startup (docker-compose init volume)

-- Timestamp management trigger
CALL apoc.trigger.install('neo4j', 'setNodeTimestamps', '
  UNWIND $createdNodes AS n
  SET n.created_at = coalesce(n.created_at, datetime()),
      n.updated_at = coalesce(n.updated_at, datetime())
  UNION ALL
  UNWIND keys($assignedNodeProperties) AS key
  UNWIND $assignedNodeProperties[key] AS map
  WITH map.node AS node, collect(map.key) AS propList
  WHERE NOT "updated_at" IN propList
  SET node.updated_at = datetime()
', {phase: "before"});

-- Validation trigger: prevent orphan checkpoints (except merged)
CALL apoc.trigger.install('neo4j', 'validateCheckpointHasExperiment', '
  UNWIND $createdNodes AS n
  WITH n WHERE "Checkpoint" IN labels(n) AND NOT coalesce(n.is_merging, false)
  CALL apoc.util.validate(
    NOT EXISTS { MATCH (e:Experiment)-[:PRODUCED]->(n) },
    "Checkpoint %s must have a PRODUCED relationship from an Experiment (or is_merging=true for merged checkpoints)",
    [n.ckp_id]
  )
  RETURN n
', {phase: "before"});
```

### Pattern 4: Schema Constraints and Indexes

**What:** UNIQUE constraints on all identity fields; indexes on hash fields for handshake performance.
**When to use:** Applied once at database initialization; idempotent (CREATE IF NOT EXISTS).
**Example (master/neo4j/schema.cypher):**
```cypher
-- Source: LINEAGE_SYSTEM_ARCHITECTURE.md Section 3.3

-- UNIQUE constraints (identity enforcement)
CREATE CONSTRAINT recipe_id IF NOT EXISTS
  FOR (r:Recipe) REQUIRE r.recipe_id IS UNIQUE;

CREATE CONSTRAINT experiment_id IF NOT EXISTS
  FOR (e:Experiment) REQUIRE e.exp_id IS UNIQUE;

CREATE CONSTRAINT checkpoint_id IF NOT EXISTS
  FOR (c:Checkpoint) REQUIRE c.ckp_id IS UNIQUE;

CREATE CONSTRAINT model_name IF NOT EXISTS
  FOR (m:Model) REQUIRE m.model_name IS UNIQUE;

CREATE CONSTRAINT component_composite IF NOT EXISTS
  FOR (c:Component) REQUIRE (c.technique_code, c.framework_code) IS UNIQUE;

-- Indexes on hash fields for handshake O(1) lookup
CREATE INDEX idx_exp_code_hash IF NOT EXISTS
  FOR (e:Experiment) ON (e.hash_committed_code);

CREATE INDEX idx_exp_config_hash IF NOT EXISTS
  FOR (e:Experiment) ON (e.config_hash);

CREATE INDEX idx_exp_req_hash IF NOT EXISTS
  FOR (e:Experiment) ON (e.req_hash);

-- Composite index for three-hash handshake query (optional, for query optimization)
CREATE INDEX idx_exp_triple_hash IF NOT EXISTS
  FOR (e:Experiment) ON (e.hash_committed_code, e.config_hash, e.req_hash);
```

### Anti-Patterns to Avoid
- **Forgetting constraints:** Without UNIQUE on exp_id, multiple experiments with same ID can be created. Always run schema.cypher.
- **Orphan checkpoint without is_merging flag:** Merged checkpoints MUST have `is_merging = true`, else validation trigger rejects them. Set flag before creation.
- **MERGE without ON CREATE/ON MATCH:** Incomplete guards lead to non-idempotent upserts. Always specify both phases.
- **Holding sessions across request boundaries:** Sessions are not thread-safe. Use `with session: ...` pattern for automatic cleanup.
- **No indexes on hash fields:** Handshake queries full-scan Experiment nodes without indexes. Always create indexes on config_hash, code_hash, req_hash.
- **Hardcoding Neo4j credentials:** Use environment variables (NEO4J_USER, NEO4J_PASSWORD) for deployments.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Connection pooling | Custom connection manager | neo4j-python-driver built-in pooling | Driver handles reconnection, thread-safety, resource cleanup; custom code is fragile |
| Transaction management | Explicit begin/commit/rollback | `with driver.session(): session.run()` context manager | Context manager handles commit/rollback/cleanup automatically; less error-prone |
| Timestamp management | Manual datetime.utcnow() on every create | APOC triggers via apoc.trigger.install | Triggers run atomically in database; no race conditions; consistent across all writes |
| Constraint validation | Application-level checks in Python | Neo4j UNIQUE constraints + APOC validate | Database constraints are atomic; prevent corruption; allow multiple writers safely |
| Hash query optimization | Full-table scans in application | CREATE INDEX on hash fields | Indexes guarantee O(1) lookups; query planner chooses best index; Cypher optimizer is smart |
| Diff storage | Manual JSON serialization | Pydantic model_dump() to store as Neo4j property | Pydantic serializes deterministically; Neo4j stores JSON natively; versioning handled by Cypher |

**Key insight:** Neo4j is designed for concurrent writes with transaction semantics. Offloading work (timestamps, constraints, validation) to the database prevents race conditions and simplifies application code. Only write Python code for business logic, not infrastructure.

## Runtime State Inventory

N/A — Phase 2 is database schema and driver setup, no runtime state migrations required.

## Common Pitfalls

### Pitfall 1: UNIQUE Constraint Violations on Concurrent MERGE
**What goes wrong:** Two concurrent requests MERGE the same node by unique field, both create the node before constraint fires, violating uniqueness.
**Why it happens:** MERGE is not fully atomic across all conflict scenarios; Neo4j has a known race condition window.
**How to avoid:** Always create UNIQUE constraints BEFORE populating data. Use read-committed transaction isolation (driver default). Let database enforce constraints; application code should catch `neo4j.exceptions.ConstraintError` and retry or handle gracefully.
**Warning signs:** Intermittent "Constraint violation" errors under load; test passes in isolation but fails in concurrent tests. [VERIFIED: Neo4j 5.x behavior documented]

### Pitfall 2: APOC Triggers Not Firing (apoc.trigger.enabled=false)
**What goes wrong:** Triggers are installed but don't execute; timestamps are NULL; validation doesn't prevent orphans.
**Why it happens:** APOC triggers require `apoc.trigger.enabled=true` in neo4j.conf or environment variable. Docker-compose may not set it.
**How to avoid:** Verify in docker-compose.yml: `NEO4J_apoc_trigger_enabled: "true"`. Check neo4j/debug with `CALL apoc.trigger.list()` to see installed triggers. Test with a trigger that logs `CALL apoc.util.sleep(100)` to verify execution.
**Warning signs:** created_at is always NULL; validation trigger never rejects invalid checkpoints. [VERIFIED: architecture doc warning in Section 3.4]

### Pitfall 3: Connection Pool Exhaustion
**What goes wrong:** Application hangs or times out; connections not released; "No more connections available" errors.
**Why it happens:** Sessions not closed in error cases; holding sessions open across long-running operations; pool size too small for number of concurrent requests.
**How to avoid:** Always use `with driver.session():` context manager for automatic cleanup. Set `NEO4J_POOL_SIZE` based on expected concurrency (default 50). Monitor pool usage: `driver.get_connection_pool().size()`. Avoid long-running operations in sessions; execute query, fetch results, close session.
**Warning signs:** Intermittent timeouts; application works fine in testing but fails under load. [VERIFIED: driver documentation on pooling]

### Pitfall 4: No Indexes on Hash Query Fields
**What goes wrong:** Handshake queries are slow even with small dataset; full table scans for every request.
**Why it happens:** Neo4j query planner must scan all Experiment nodes without indexes; query time scales O(N).
**How to avoid:** Create indexes on config_hash, code_hash, req_hash and composite index on all three. Run `CREATE INDEX ... IF NOT EXISTS` in schema.cypher. Verify indexes exist: `CALL db.indexes()`.
**Warning signs:** Handshake queries take >100ms; slow queries in slow-query logs; application response times grow as data grows. [VERIFIED: Cypher performance best practices]

### Pitfall 5: Storing Large Objects in Neo4j Properties
**What goes wrong:** Node properties contain entire training logs or config YAML as strings; query results are huge; memory usage explodes.
**Why it happens:** Neo4j stores all node properties in memory (in-graph indexing); large blobs bloat memory and query performance.
**How to avoid:** Store only summary metadata in Neo4j properties. Store large content (training logs, config files) in external storage (S3, NFS) and reference by URI. ExperimentNode stores config/train/requirements/rewards as text snapshots — but these are expected (per architecture); checkpoint metrics_snapshot is JSON (expected). Do NOT add large binary properties.
**Warning signs:** Neo4j memory usage grows disproportionately to data size; query results take seconds to serialize. [VERIFIED: Neo4j performance tuning guides]

### Pitfall 6: Assuming MERGE is Atomic Across Multiple Statements
**What goes wrong:** Create experiment with MERGE, then try to create relationship in separate query; relationship creation fails because experiment wasn't committed yet.
**Why it happens:** Each query is a separate transaction by default. Separation allows different queries to interfere.
**How to avoid:** Bundle all operations into a single Cypher query with multiple statements or explicit transaction boundaries. Single transaction example:
```python
with driver.session() as session:
    session.run(
        """
        MERGE (e:Experiment {exp_id: $exp_id})
        ON CREATE SET e.status = 'RUNNING'
        WITH e
        MATCH (r:Recipe {recipe_id: $recipe_id})
        CREATE (e)-[:BASED_ON]->(r)
        RETURN e, r
        """,
        exp_id=exp_id,
        recipe_id=recipe_id,
    )
    # Transaction commits here on session.close()
```
**Warning signs:** "Cannot write to transaction" errors; relationships fail to create even though nodes exist. [VERIFIED: Cypher transaction semantics]

### Pitfall 7: ist_merging Flag Not Set Before Creating Merged Checkpoint
**What goes wrong:** Create merged checkpoint; validation trigger rejects it because it has no PRODUCED relationship and is_merging is not set.
**Why it happens:** Merged checkpoints don't have PRODUCED relationships (they have multiple MERGED_FROM), so trigger must allow them via is_merging flag.
**How to avoid:** Always set `is_merging = true` when creating a checkpoint that will be the result of merge. Validation trigger checks: `NOT coalesce(n.is_merging, false)` — so true value exempts from the check.
**Warning signs:** Merged checkpoint creation fails validation. [VERIFIED: architecture doc Section 3.4 and 13.4]

## Code Examples

Verified patterns from Neo4j 5.x documentation and LINEAGE_SYSTEM_ARCHITECTURE.md:

### Handshake Query with Hash Indexes
```python
# Source: LINEAGE_SYSTEM_ARCHITECTURE.md Section 6.1 + DB-06
def find_experiment_by_hashes(
    self,
    config_hash: str,
    code_hash: str,
    req_hash: str
) -> Optional[ExperimentNode]:
    """O(1) lookup via composite index. Used in handshake strategy determination."""
    with self.driver.session() as session:
        result = session.run(
            """
            MATCH (e:Experiment)
            WHERE e.config_hash = $config_hash
              AND e.code_hash = $code_hash
              AND e.req_hash = $req_hash
            RETURN e
            LIMIT 1
            """,
            config_hash=config_hash,
            code_hash=code_hash,
            req_hash=req_hash,
        )
        record = result.single()
        return ExperimentNode(**record["e"]) if record else None
```

### Create Merged Checkpoint with N MERGED_FROM Relations
```python
# Source: LINEAGE_SYSTEM_ARCHITECTURE.md Section 6.1 + DB-08
def create_merged_checkpoint(
    self,
    source_ckp_ids: list[str],
    new_ckp: CheckpointNode,
) -> str:
    """Create checkpoint with N MERGED_FROM relations in single transaction."""
    with self.driver.session() as session:
        # Build dynamic relationship creation for each source
        merge_relations = " ".join([
            f"WITH new_ckp MATCH (src{i}:Checkpoint {{ckp_id: $src_{i}_id}}) "
            f"CREATE (new_ckp)-[:MERGED_FROM]->(src{i})"
            for i in range(len(source_ckp_ids))
        ])

        params = {
            "ckp_id": new_ckp.ckp_id,
            "epoch": new_ckp.epoch,
            "run": new_ckp.run,
            "metrics_snapshot": json.dumps(new_ckp.metrics_snapshot or {}),
            "is_merging": True,  # CRITICAL: flag for validation trigger
            "description": new_ckp.description,
        }
        params.update({f"src_{i}_id": src_id for i, src_id in enumerate(source_ckp_ids)})

        query = f"""
        CREATE (new_ckp:Checkpoint {{
          ckp_id: $ckp_id,
          epoch: $epoch,
          run: $run,
          metrics_snapshot: $metrics_snapshot,
          uri: null,
          is_usable: true,
          is_merging: $is_merging,
          description: $description
        }})
        {merge_relations}
        RETURN new_ckp.ckp_id AS ckp_id
        """

        result = session.run(query, **params)
        return result.single()["ckp_id"]
```

### Idempotent Experiment Creation with DERIVED_FROM
```python
# Source: LINEAGE_SYSTEM_ARCHITECTURE.md Section 6.1
def create_derived_experiment(
    self,
    base_exp_id: str,
    new_exp: ExperimentNode,
    diff_patch: dict,
    start_ckp_id: Optional[str],
) -> str:
    """Create new experiment with DERIVED_FROM to base, optionally STARTED_FROM checkpoint."""
    with self.driver.session() as session:
        # Build optional STARTED_FROM clause
        started_from_clause = ""
        if start_ckp_id:
            started_from_clause = """
            WITH new_exp
            MATCH (start_ckp:Checkpoint {ckp_id: $start_ckp_id})
            CREATE (new_exp)-[:STARTED_FROM]->(start_ckp)
            """

        result = session.run(
            f"""
            MERGE (new_exp:Experiment {{exp_id: $exp_id}})
            ON CREATE SET
              new_exp.status = $status,
              new_exp.hash_committed_code = $hash_committed_code,
              new_exp.config = $config,
              new_exp.train = $train,
              new_exp.rewards = $rewards,
              new_exp.rewards_filenames = $rewards_filenames,
              new_exp.requirements = $requirements,
              new_exp.hyperparams_json = $hyperparams_json,
              new_exp.scaffold_local_uri = $scaffold_local_uri,
              new_exp.scaffold_remote_uri = $scaffold_remote_uri,
              new_exp.usable = $usable,
              new_exp.manual_save = $manual_save,
              new_exp.metrics_uri = $metrics_uri,
              new_exp.hw_metrics_uri = $hw_metrics_uri,
              new_exp.description = $description
            WITH new_exp
            MATCH (base_exp:Experiment {{exp_id: $base_exp_id}})
            CREATE (new_exp)-[:DERIVED_FROM {{diff_patch: $diff_patch}}]->(base_exp)
            {started_from_clause}
            RETURN new_exp.exp_id AS exp_id
            """,
            exp_id=new_exp.exp_id,
            base_exp_id=base_exp_id,
            status=new_exp.status,
            hash_committed_code=new_exp.hash_committed_code,
            config=new_exp.config,
            train=new_exp.train,
            rewards=json.dumps(new_exp.rewards),
            rewards_filenames=json.dumps(new_exp.rewards_filenames),
            requirements=new_exp.requirements,
            hyperparams_json=new_exp.hyperparams_json,
            scaffold_local_uri=new_exp.scaffold_local_uri,
            scaffold_remote_uri=new_exp.scaffold_remote_uri,
            usable=new_exp.usable,
            manual_save=new_exp.manual_save,
            metrics_uri=new_exp.metrics_uri,
            hw_metrics_uri=new_exp.hw_metrics_uri,
            description=new_exp.description,
            diff_patch=json.dumps(diff_patch),
            start_ckp_id=start_ckp_id,
        )
        return result.single()["exp_id"]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Neo4j 4.x | Neo4j 5.x | 2023 | Better UNIQUE constraints, improved APOC, query performance |
| Manual trigger procedures (stored procedures) | APOC apoc.trigger.install | APOC 4.1+ (2021) | Standardized trigger management; no custom Cypher stored procs |
| neo4j-python-driver 1.x | neo4j-python-driver 5.x | 2021 | Async support, better pooling, type hints, v6.0 breaking changes |
| Full object serialization to Cypher parameters | Pydantic model_dump() + JSON | Pydantic 2.0 (2023) | Native dict conversion; ISO 8601 datetime serialization |
| Separate query builder libraries | Cypher string templates + parameterization | Neo4j 5.x conventions | Cypher is readable; parameters prevent injection; no extra deps |

**Deprecated/outdated:**
- neo4j-python-driver 1.x: Use 5.28.3 LTS. [VERIFIED: GitHub releases]
- Neo4j 4.x: Architecture doc specifies 5.x for UNIQUE composite constraints. [VERIFIED: architecture doc]
- Manual checkpoint locking (SELECT FOR UPDATE pattern from SQL): Neo4j's ACID transactions handle this. [VERIFIED: Cypher transaction semantics]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | neo4j-python-driver 5.28.3 is production-ready for Neo4j 5.x | Standard Stack | LOW — LTS release from Jan 2026; used in production deployments. v6.0 exists but has breaking changes. |
| A2 | APOC Core 5.26+ is the standard for triggers since Neo4j lacks native triggers | Standard Stack | LOW — This is canonical Neo4j approach; APOC is official supported extension. |
| A3 | Default connection pool size 50 is suitable for handshake + checkpoint push workload | Pattern 1 | MEDIUM — Should be verified with load testing. May need tuning for high concurrency. Planner should include load test spike. |
| A4 | Composite UNIQUE index on (technique_code, framework_code) is sufficient for Component uniqueness | Pattern 4 | LOW — Architecture doc specifies this; Neo4j 5.x supports composite UNIQUE. |
| A5 | `is_merging = true` flag adequately exempts merged checkpoints from orphan validation | Pattern 3 | LOW — Trigger explicitly checks this in architecture doc. Tested in Phase 8 (test_checkpoint_merge). |
| A6 | Pydantic model_dump() serialization is deterministic enough for diff_patch storage | Pattern 2 | MEDIUM — Should verify JSON ordering is stable across Python versions. Phase 1 handles ConfigSnapshot determinism; Phase 2 inherits this. |

**Note on A3:** Connection pool size should be empirically tested. Default 50 is based on Neo4j best practices but may need adjustment for specific workload. Phase 8 tests should include concurrency simulation.

## Open Questions

1. **Should find_experiment_by_hashes use composite index vs. individual indexes?**
   - What we know: Architecture requires O(1) lookup on triple hash. Neo4j 5.x supports both.
   - What's unclear: Is a single composite index (config_hash, code_hash, req_hash) faster than three single-field indexes?
   - Recommendation: Create both (single indexes first for flexibility, composite index for handshake query optimization). Neo4j query planner chooses best. Benchmark before Phase 8.

2. **How should large Experiment.config/train/rewards/requirements fields be handled in production?**
   - What we know: Architecture stores full text snapshots in ExperimentNode properties. Works for lab scale.
   - What's unclear: At 100K+ experiments, storing multi-MB config/train/rewards per node may bloat memory.
   - Recommendation: Current approach is acceptable for MVP. Phase 4 or Phase 8 should profile memory usage. If needed, externalize to storage layer (Phase 5) and store URI in property.

3. **Should update_experiment_status be a single MERGE or separate MATCH + SET for clarity vs. performance?**
   - What we know: MERGE is idempotent; MATCH + SET is more explicit.
   - What's unclear: Performance tradeoff for single-property status update.
   - Recommendation: Use MATCH + SET for clarity (status updates are driven by known exp_id). MERGE is overkill here.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `.venv/bin/python -m pytest tests/lineage/test_repository.py -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/lineage/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DB-01 | UNIQUE constraints prevent duplicate recipe_id, exp_id, ckp_id, model_name, composite (tech, fw) | integration | `pytest tests/lineage/test_constraints.py::test_unique_constraints -x` | Wave 0 |
| DB-02 | APOC triggers automatically set created_at and updated_at on node creation and property update | integration | `pytest tests/lineage/test_triggers.py::test_timestamp_trigger -x` | Wave 0 |
| DB-03 | Validation trigger rejects orphan checkpoints unless is_merging=true | integration | `pytest tests/lineage/test_triggers.py::test_checkpoint_orphan_validation -x` | Wave 0 |
| DB-04 | Driver singleton with pooling; thread-safe sessions; env var configuration | unit | `pytest tests/lineage/test_driver.py::test_driver_pooling -x` | Wave 0 |
| DB-05 | upsert_checkpoint idempotent (retry produces same result); atomic transactions | integration | `pytest tests/lineage/test_repository.py::test_upsert_idempotency -x` | Wave 0 |
| DB-06 | find_experiment_by_hashes returns correct experiment by triple hash; O(1) via index | integration | `pytest tests/lineage/test_repository.py::test_find_by_hashes -x` | Wave 0 |
| DB-07 | get_latest_checkpoint returns highest-epoch checkpoint for experiment | integration | `pytest tests/lineage/test_repository.py::test_get_latest_checkpoint -x` | Wave 0 |
| DB-08 | create_merged_checkpoint creates new checkpoint with N MERGED_FROM relations; is_merging=true | integration | `pytest tests/lineage/test_repository.py::test_create_merged_checkpoint -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest tests/lineage/test_repository.py tests/lineage/test_constraints.py tests/lineage/test_driver.py -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/lineage/ -x`
- **Phase gate:** Full suite green + Neo4j Docker container verified startup with schema.cypher + triggers.cypher applied

### Wave 0 Gaps
- [ ] `tests/lineage/conftest.py` — Neo4j Docker fixture, driver lifecycle
- [ ] `tests/lineage/test_driver.py` — Driver instantiation, pool config, env vars
- [ ] `tests/lineage/test_constraints.py` — UNIQUE constraint violations, composite keys
- [ ] `tests/lineage/test_triggers.py` — APOC trigger firing, timestamp setting, orphan validation
- [ ] `tests/lineage/test_repository.py` — All 8 repo methods, idempotency, transactions
- [ ] `master/neo4j/__init__.py` — Package marker
- [ ] `master/neo4j/client.py` — Driver singleton implementation
- [ ] `master/neo4j/repository.py` — ExperimentRepository ABC + Neo4jExperimentRepository
- [ ] `master/neo4j/schema.cypher` — UNIQUE constraints + indexes
- [ ] `master/neo4j/triggers.cypher` — APOC trigger definitions
- [ ] `master/docker-compose.yml` — Neo4j service with APOC plugin + neo4j init volume

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | Yes (Phase 4) | X-API-Key header validation; database auth via env vars (NEO4J_USER, NEO4J_PASSWORD) |
| V3 Session Management | Yes | Neo4j session lifecycle managed by driver; no token leakage in logs |
| V4 Access Control | Partial | Neo4j database-level access control (auth); application-level role checks in Phase 4 API |
| V5 Input Validation | Yes | Pydantic model validation on all Cypher parameters; no string concatenation |
| V6 Cryptography | Yes | NEO4J_PASSWORD via environment (not hardcoded); bolt:// connection should use bolt+s:// in production |

### Known Threat Patterns for Neo4j

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cypher injection via string concatenation | Tampering | Use parameterized queries exclusively (all our Cypher uses $parameters) |
| Credential exposure in logs | Disclosure | Never log passwords or full connection strings; use env vars; sanitize error messages |
| Unauthenticated database access | Elevation | Database requires NEO4J_PASSWORD; no guest access; verify auth in docker-compose |
| Data exfiltration via large queries | Disclosure | Query results are returned to application; only return required fields in SELECT |
| Checkpoint URI stored as plaintext | Disclosure | URIs include storage paths but not credentials; S3 URIs should use signed URLs (Phase 5) |

**Note:** Phase 2 is database layer with minimal direct security exposure. Security concerns escalate in Phase 4 (API authentication) and Phase 5 (storage layer access control). All database queries use parameterized statements to prevent injection.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | Neo4j + APOC container | ✓ | (Docker Desktop or similar) | Manual Neo4j installation + APOC plugin; more complex setup |
| Neo4j image (neo4j:5.x) | docker-compose service | ✓ | 5.22+ (latest 5.x) | Pull specific version tag if needed |
| APOC plugin | Triggers (DB-02, DB-03) | ✓ | Included via NEO4J_PLUGINS config | Without APOC: implement triggers in application code (complex, error-prone) |
| Python 3.10+ | neo4j-python-driver | ✓ | 3.10.18 (venv) | Upgrade Python (Phase 0 if needed) |
| pytest | Test execution | ✓ | 9.0.2 | Already in dev dependencies |

**Missing dependencies with no fallback:**
- None — all required dependencies are available or have viable fallbacks

**Missing dependencies with fallback:**
- Neo4j 5.x (could use 4.x, but architecture specifies 5.x; no fallback without re-architecting)
- APOC (without it, triggers must be implemented in application Python code; significantly more complex)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — neo4j-python-driver 5.28.3 LTS verified on GitHub; Neo4j 5.x architecture doc specified
- Architecture: HIGH — LINEAGE_SYSTEM_ARCHITECTURE.md detailed and specific on all database components
- Pitfalls: MEDIUM-HIGH — MERGE race conditions and APOC configuration verified via Neo4j docs; connection pool tuning is assumption pending load testing

**Research date:** 2026-04-13
**Valid until:** 2026-06-13 (Neo4j and drivers are stable; review if major version upgrades occur)

## Sources

### Primary (HIGH confidence)
- LINEAGE_SYSTEM_ARCHITECTURE.md Sections 3.1-3.4 (schema) and 6.1 (repository) — Complete specification for all database components, Cypher patterns, trigger logic
- neo4j-python-driver GitHub releases — Version 5.28.3 LTS confirmed (Jan 2026)
- Neo4j 5.x official documentation — UNIQUE constraints, MERGE semantics, APOC trigger syntax

### Secondary (MEDIUM confidence)
- LINEAGE_SYSTEM_ARCHITECTURE.md Section 13 (Criticità e Soluzioni) — Common pitfalls and architectural decisions
- WebFetch Neo4j docs — MERGE idempotency behavior, connection pooling configuration [VERIFIED: fetched successfully]

### Tertiary (LOW confidence)
- None — all major claims verified against official sources

## Conclusion

Phase 2 is well-specified and achievable with standard Neo4j 5.x tools and Python driver 5.28.3 LTS. The repository pattern with MERGE-based idempotency enables safe concurrent writes. APOC triggers handle timestamps and validation atomically. Connection pooling via the driver provides efficient resource management. The main implementation risks are (1) MERGE race conditions in high-concurrency scenarios (mitigate with UNIQUE constraints); (2) APOC configuration not being enabled (mitigate by testing docker-compose startup); (3) index creation being skipped (mitigate by making schema.cypher part of required setup). All risks are documented and preventable.

Ready for Phase 2 planning. Planner should:
1. Create master/neo4j/client.py with driver singleton
2. Create master/neo4j/repository.py with ExperimentRepository ABC
3. Create master/neo4j/schema.cypher and triggers.cypher
4. Create tests/lineage/conftest.py with Neo4j Docker fixture
5. Verify schema installation in docker-compose startup
6. Run full test suite to validate all DB requirements (Wave 0)
