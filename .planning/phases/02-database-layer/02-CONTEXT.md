---
phase: 02-database-layer
gathered: 2026-04-13T14:00:00Z
decisions: 3
---

# Phase 2 — Gathered Context

## User Decisions (Discuss Phase)

### 1. Async-First Repository with TDD/OOP Pattern

**Decision:** Start with async Neo4j driver (neo4j.asyncio) from day one. Use ABC (Abstract Base Class) pattern to enable both sync and async implementations coexisting.

**Rationale:**
- TDD + object-oriented approach maximizes flexibility
- If async doesn't work immediately, can fallback to sync under same ABC
- Phase 4 (FastAPI) will likely need async; starting now prevents rework
- Neo4j 5.28.3 has experimental async support; can iterate

**Implementation Pattern:**
- `BaseExperimentRepository(ABC)` with abstract async methods
- `ExperimentRepositoryAsync(BaseExperimentRepository)` for production
- `ExperimentRepository(BaseExperimentRepository)` for backwards compatibility (sync, used in tests if needed)

**TDD Consequence:** All tasks must include both async tests + sync fallback tests initially.

---

### 2. Atomic Per-Method Transactions (Extensible)

**Decision:** Start with atomic transactions per repository method (e.g., `upsert_checkpoint()` is one transaction). Keep class extensible for future caller-provided sessions/transactions.

**Rationale:**
- Daemon periodically flushes experiment entities to DB — transaction boundaries are critical
- Simpler initial API: caller doesn't manage transactions
- Future extensions: allow caller to pass session for multi-operation atomic blocks
- Reserve `__future__` API: `upsert_checkpoint(..., session=None)` for extensibility

**Implementation Pattern:**
```python
async def upsert_checkpoint(self, exp_id: str, ckp_id: str, ...) -> CheckpointNode:
    """Atomic transaction: creates/updates checkpoint and relations."""
    async with self.driver.session() as session:
        async with session.begin_transaction() as tx:
            # ... MERGE operations ...
        return checkpoint_node

# Future (Phase X):
async def upsert_checkpoint(self, exp_id: str, ckp_id: str, ..., session=None) -> CheckpointNode:
    """If session provided, use it (caller controls transaction scope)."""
    target_session = session or (await self.driver.session())
    # ...
```

---

### 3. Index Strategy: Three Separate BTREE Indexes

**Decision:** Use individual BTREE indexes on:
- `Experiment.config_hash`
- `Experiment.code_hash`
- `Experiment.req_hash`

**Rationale:**
- Simpler schema (easier to evolve if handshake query logic changes)
- Neo4j optimizer handles multi-property queries efficiently
- Composite index would be rigid if we later query only one hash
- Single-property indexes are standard Neo4j practice

**Schema Impact:**
```cypher
CREATE INDEX idx_experiment_config_hash IF NOT EXISTS FOR (e:Experiment) ON (e.config_hash);
CREATE INDEX idx_experiment_code_hash IF NOT EXISTS FOR (e:Experiment) ON (e.code_hash);
CREATE INDEX idx_experiment_req_hash IF NOT EXISTS FOR (e:Experiment) ON (e.req_hash);
```

---

## TDD Checkpoint: Tests Before Implementation

All Phase 2 tasks MUST include test fixtures (pytest + pytest-asyncio) that define the contract BEFORE implementation. This matches Phase 1 pattern (tests exist in test plan context).

**Test Module Strategy:**
- `tests/lineage/test_neo4j_driver.py` — driver singleton, pool config, session management
- `tests/lineage/test_repository_abc.py` — ABC definition, method signatures
- `tests/lineage/test_constraints.py` — UNIQUE constraint enforcement
- `tests/lineage/test_apoc_triggers.py` — created_at/updated_at, orphan validation
- `tests/lineage/test_repository_operations.py` — CRUD, merge, handshake queries
- `tests/lineage/test_idempotency.py` — MERGE patterns, conflict handling

---

## Open Questions for Planner

1. **Async Session Lifecycle:** Should driver be instantiated at module load or lazily on first repository method call?
2. **Error Handling:** Retry logic for transient Neo4j connection failures — where?
3. **Logging:** Cypher query logging (verbose mode for debugging) — log level configuration?
4. **Mock Docker Compose:** Should Phase 2 include a minimal docker-compose for local Neo4j + APOC? (Currently handled by Phase 4 INFRA, but dev iteration might benefit from it now.)

---

## Dependency Graph

**Phase 2 depends on:**
- Phase 1 (Shared Layer) — node models, envelopes, config hasher

**Phase 2 blocks:**
- Phase 4 (Master API + Infra) — uses ExperimentRepository in LineageController
- Phase 9 (Testing) — E2E tests need Neo4j layer operational

---

## Requirements Traceability

| Requirement | User Decision Impact | Status |
|-------------|---------------------|--------|
| DB-01: UNIQUE constraints | Schema.cypher defines; TDD test validates | Ready |
| DB-02: APOC triggers (created_at/updated_at) | triggers.cypher + test validation | Ready |
| DB-03: Orphan checkpoint validation | APOC triggers + _TEST label cleanup | Ready |
| DB-04: Driver singleton + pooling | ABC pattern enables dependency injection | Ready |
| DB-05: Idempotent MERGE patterns | Atomic per-method + MERGE with ON CREATE/MATCH | Ready |
| DB-06: find_experiment_by_hashes | Three separate indexes (user decision 3) | Ready |
| DB-07: get_latest_checkpoint | Standard Cypher query (no new decision) | Ready |
| DB-08: create_merged_checkpoint | Async atomic transaction (user decision 2) | Ready |

---

*Gathered: 2026-04-13 with user alignment on async-first, TDD/OOP pattern, atomic-per-method, three-index strategy*
