# Phase 13.1: Neo4j Schema Consolidation — PLAN

**Phase Number**: 13.1 (INSERTED after 13)
**Status**: PLANNING
**Goal**: Consolidate Neo4j schema into version-controlled, complete Cypher files derived from Pydantic models; eliminate redundancy; initialize seed data

---

## Requirements Analysis

### FIX 1: Eliminate Redundancy
- **Problem**: `database/schema_init.cypher` contains only Recipe uniqueness constraint; duplicates logic in `master/neo4j/schema.cypher`
- **Action**: Delete `database/schema_init.cypher` entirely
- **Rationale**: Single source of truth in `master/neo4j/` simplifies maintenance

### FIX 2: Complete Schema File (01-schema.cypher)
- **Problem**: Current `master/neo4j/schema.cypher` has constraints and indexes but NO node/edge type definitions
- **Action**: Rewrite as `master/neo4j/01-schema.cypher`:
  - All 5 node types with properties from Pydantic models (aligned to nodes.py):
    - `Recipe(recipe_id, name, description, scope, tasks, tags, issued, modified, derived_from, config_yaml, entries, created_at, updated_at)`
    - `Model(model_name, version, uri, url, doc_url, architecture_info_ref, description, created_at, updated_at)`
    - `Experiment(exp_id, model_id, status, exit_status, exit_msg, strategy, config_hash, code_hash, req_hash, config, train, rewards, rewards_filenames, requirements, scaffold_local_uri, scaffold_remote_uri, usable, manual_save, metrics_uri, hw_metrics_uri, description, created_at, updated_at)`
    - `Checkpoint(ckp_id, epoch, run, metrics_snapshot, uri, is_usable, is_merging, description, created_at, updated_at)`
    - `Component(technique_code, framework_code, docs_url, description, created_at, updated_at)`
  - All 8 relationship types (USED_FOR, SELECTED_FOR, BASED_ON, PRODUCED, DERIVED_FROM, STARTED_FROM, RETRY_OF, MERGED_FROM)
  - All constraints (5 UNIQUE constraints)
  - All indexes (3 BTREE on Experiment hashes: config_hash, code_hash, req_hash)
  - Full Cypher comments mapping each property to Pydantic field

### FIX 3: Seed Data File (02-seeds.cypher)
- **Problem**: No initial data population; users see empty graph on first startup
- **Action**: Create `master/neo4j/02-seeds.cypher`:
  - Component Nodes: All valid (technique, framework) combinations from `envelope/config/models.py`
    - Techniques: SFT, DPO, SIMPO, KTO, ORPO, PPO, GRPO, etc. (23 total)
    - Frameworks: TRL, UNSLOTH, AXOLOTL, TORCHTUNE, VERL, OPENRLHF, LLAMAFACTORY, NEMO, FROM_SCRATCH (9 total)
    - Creates few component  Component nodes with idempotent logic (MERGE, not CREATE)
  - Core Models: Foundation models for reference/teacher roles (no-op if exist)
    - Examples: `meta-llama/Llama-2-7b`, `meta-llama/Llama-3-8b`, `mistralai/Mistral-7B-v0.1`
  - Idempotent: Uses MERGE to avoid duplicates on re-runs

---

## Tasks

### Task 1: Delete database/schema_init.cypher
**Owner**: TBD
**Effort**: <1 min
**Acceptance Criteria**:
- [ ] File deleted from `database/` folder
- [ ] Only `master/neo4j/` contains schema files
- [ ] Git commits deletion with message: "refactor: remove redundant database/schema_init.cypher"

### Task 2: Create master/neo4j/01-schema.cypher
**Owner**: TBD
**Effort**: 2-3 hours
**Acceptance Criteria**:
- [ ] File created with complete schema definition
- [ ] All 5 node types defined with properties matching Pydantic models
- [ ] All relationship types defined with cardinality notes
- [ ] All 5+ constraints present (UNIQUE on recipe_id, exp_id, ckp_id, model_name, composite on Component)
- [ ] APOC triggers for created_at, updated_at, orphan validation
- [ ] All indexes present (3 BTREE on Experiment hashes, etc.)
- [ ] Idempotent: All CREATE statements use IF NOT EXISTS
- [ ] Rich Cypher comments cross-reference Pydantic field names and validation rules
- [ ] File passes syntax validation: `neo4j-admin` or runtime test against Neo4j instance

### Task 3: Create master/neo4j/02-seeds.cypher
**Owner**: TBD
**Effort**: 1-2 hours
**Acceptance Criteria**:
- [ ] File created with seed data initialization
- [ ] Component Nodes: All (technique, framework) combinations created via MERGE
  - [ ] 23 techniques enumerated and cross-referenced to `envelope/config/models.py`
  - [ ] 9 frameworks enumerated and cross-referenced to `envelope/config/models.py`
  - [ ] Creates ~207 nodes (23×9); idempotent on re-runs
  - [ ] Each node has: `technique_code`, `framework_code`, `created_at`, `updated_at`
- [ ] Model Nodes: Core foundation models for reference/teacher roles (at minimum 3-5 examples)
  - [ ] Each node has: `model_name`, `model_path`, `revision`, `created_at`, `updated_at`
  - [ ] Uses MERGE to skip if already exist
- [ ] Idempotent: All operations use MERGE or conditional logic
- [ ] Syntax valid and tested

### Task 4: Update Docker initialization script
**Owner**: TBD
**Effort**: 30 min
**Acceptance Criteria**:
- [ ] Schema initialization at startup loads Cypher files in order:
  1. `master/neo4j/01-schema.cypher` — schema definition
  2. `master/neo4j/02-seeds.cypher` — seed data
- [ ] Startup script or `docker-entrypoint.sh` executes both files
- [ ] Logs confirm successful execution: "Schema initialized" + "Seed data loaded"
- [ ] No errors on re-runs (idempotency verified)

### Task 5: Integration testing + documentation
**Owner**: TBD
**Effort**: 1 hour
**Acceptance Criteria**:
- [ ] `make master-up` starts fresh Neo4j with complete schema + seed data
- [ ] Query Neo4j to verify:
  - [ ] 5 node types exist (Recipe, Model, Experiment, Checkpoint, Component)
  - [ ] ~207 Component nodes present
  - [ ] 3+ core Models present
  - [ ] Constraints enforced (test unique violation on Recipe.name)
  - [ ] Triggers fire (create test node, verify created_at auto-set)
- [ ] Update `.planning/docs/NEO4J_SCHEMA.md` to document:
  - [ ] All node types with properties
  - [ ] All relationship types with examples
  - [ ] Constraint list
  - [ ] Trigger behavior
  - [ ] Seed data initialization

---

## Dependencies & Ordering

**Depends on**: Phase 13 (Recipe Management Fix)
**Blocks**: None immediately (integration phases can use improved schema)
**Parallelization**: Can be worked in parallel with Phase 10 (Documentation)

---

## Verification Criteria

**Before marking complete, verify ALL of:**

1. ✅ **Redundancy eliminated**: `database/schema_init.cypher` deleted, no references remain
2. ✅ **Schema complete**: `01-schema.cypher` contains all node types, edges, constraints, triggers
3. ✅ **Seeds initialized**: `02-seeds.cypher` populates Components (~207) and Models (3+)
4. ✅ **Idempotent**: Both files safe to run multiple times without errors
5. ✅ **Docker startup**: Schema initialization runs on container startup
6. ✅ **Tests pass**: `make master-up` → schema validation tests → ✓
7. ✅ **Documentation**: Node types and schema documented

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|-----------|
| Schema conflicts on upgrade | Low | High | Idempotent IF NOT EXISTS; test on fresh DB |
| Seed data not idempotent | Medium | Medium | Use MERGE, add duplicate detection tests |
| Missing Pydantic field | Medium | Medium | Read Pydantic models twice, cross-check |
| Neo4j version compatibility | Low | High | Target Neo4j 5.x; test locally first |

---

## Success Criteria (Phase Level)

**This phase is complete when:**

1. `database/schema_init.cypher` is deleted ✅
2. `master/neo4j/01-schema.cypher` exists with complete node/edge definitions ✅
3. `master/neo4j/02-seeds.cypher` exists with seed data (Components + Models) ✅
4. Docker startup initializes both files in order ✅
5. All schema validation tests pass (constraints, triggers, indexes verified) ✅
6. Schema documentation exists in `.planning/docs/NEO4J_SCHEMA.md` ✅

---

## Estimated Effort

- **Total**: 5-6 hours
- **Breakdown**:
  - Task 1 (delete): <1 min
  - Task 2 (schema): 2-3 hours
  - Task 3 (seeds): 1-2 hours
  - Task 4 (docker init): 30 min
  - Task 5 (testing + docs): 1 hour

---

## Notes

- Phase 13.1 is a consolidation/refactoring phase; no breaking changes to functionality
- Backward-compatible: existing data in Neo4j remains intact when running idempotent schema files
- Building block for future schema evolution (Phase 14+)
