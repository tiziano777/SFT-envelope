# Neo4j Schema Documentation

**Version**: 5.x
**Last Updated**: 2026-04-15
**Status**: COMPLETE (Phase 13.1)

---

## Overview

The Neo4j schema defines the complete lineage tracking system for LLM fine-tuning experiments. It consists of **5 node types**, **8 relationship types**, **6 unique constraints**, **3 BTREE indexes**, and **APOC automation triggers**.

All files are version-controlled and idempotent, safe to run multiple times without conflicts.

### Files

| File | Purpose | Execution Order |
|------|---------|-----------------|
| `master/neo4j/01-schema.cypher` | Node types, relationships, constraints, indexes | 1 (first) |
| `master/neo4j/02-triggers.cypher` | APOC triggers for automation (timestamps, validation) | 2 (second) |
| `master/neo4j/03-seeds.cypher` | Initial seed data (207 Components, 5+ Models) | 3 (third) |

### Initialization

All files load automatically on container startup via `/master/entrypoint.sh`:

```bash
# Docker startup sequence:
1. entrypoint.sh invoked
2. init_schema.py runs (loads all 3 files in sequence)
3. Master API starts (health check verifies Neo4j connectivity)
```

---

## Node Types

### 1. Recipe

**Purpose**: Dataset configuration and metadata
**PK**: `recipe_id` (UNIQUE constraint)

| Property | Type | Description | Default |
|----------|------|-------------|---------|
| `recipe_id` | String | Unique identifier (UUID) | REQUIRED |
| `name` | String | Human-readable name | REQUIRED, UNIQUE |
| `description` | String | Narrative description | `""` |
| `scope` | String | Domain/scope (e.g., "instruction-tuning") | `""` |
| `tasks` | List[String] | Task categories | `[]` |
| `tags` | List[String] | Metadata tags | `[]` |
| `issued` | DateTime | Creation timestamp | REQUIRED |
| `modified` | DateTime | Last modification | REQUIRED |
| `derived_from` | String | Optional recursive reference to parent recipe_id | NULL |
| `config_yaml` | String | Frozen YAML content snapshot | REQUIRED |
| `entries` | List[Dict] | Dataset entries (dist_id, samples, tokens, words) | REQUIRED |
| `created_at` | DateTime | Set by APOC trigger | Auto-set |
| `updated_at` | DateTime | Set by APOC trigger | Auto-set |

**Example Creation**:
```cypher
CREATE (r:Recipe {
  recipe_id: "rec_abc123",
  name: "instruction-tuning-v1",
  description: "First iteration instruction tuning",
  scope: "instruction-tuning",
  tasks: ["instruction", "followup"],
  tags: ["v1", "baseline"],
  issued: datetime(),
  modified: datetime(),
  config_yaml: "version: 1\nentries: [...]\n",
  entries: [
    {dist_id: "dist_1", samples: 1000, tokens: 50000, words: 8000},
    {dist_id: "dist_2", samples: 500, tokens: 30000, words: 5000}
  ]
})
```

---

### 2. Model

**Purpose**: Foundation models used as base for fine-tuning
**PK**: `model_name` (UNIQUE constraint)

| Property | Type | Description | Default |
|----------|------|-------------|---------|
| `model_name` | String | Model identifier (e.g., "meta-llama/Llama-3-8b") | REQUIRED, UNIQUE |
| `model_path` | String | Local or remote path | `""` |
| `version` | String | Version tag (e.g., "main") | `"main"` |
| `uri` | String | Local file path (file://) or remote (s3://) | `""` |
| `url` | String | HuggingFace hub URL | `""` |
| `doc_url` | String | Documentation URL | `""` |
| `architecture_info_ref` | String | Architecture reference | `""` |
| `description` | String | Model description | `""` |
| `created_at` | DateTime | Set by APOC trigger | Auto-set |
| `updated_at` | DateTime | Set by APOC trigger | Auto-set |

**Example Creation**:
```cypher
CREATE (m:Model {
  model_name: "meta-llama/Llama-3-8b",
  model_path: "meta-llama/Llama-3-8b",
  version: "main",
  uri: "s3://my-bucket/llama-3-8b",
  url: "https://huggingface.co/meta-llama/Llama-3-8b",
  doc_url: "https://llama.meta.com/",
  description: "Meta Llama 3 8B parameter model"
})
```

---

### 3. Experiment

**Purpose**: Fine-tuning experiment run with lineage tracking
**PK**: `exp_id` (UNIQUE constraint)

| Property | Type | Description | Default |
|----------|------|-------------|---------|
| `exp_id` | String | Unique experiment identifier (UUID) | REQUIRED, UNIQUE |
| `model_id` | String | Foreign key to Model.model_name | `""` |
| `status` | String | Lifecycle: RUNNING, COMPLETED, FAILED, PAUSED | RUNNING |
| `exit_status` | String | Exit code if terminated | NULL |
| `exit_msg` | String | Error message if failed | NULL |
| `strategy` | String | NEW, RESUME, BRANCH, RETRY | REQUIRED |
| `config_hash` | String | SHA256(config.yaml) — indexed for handshake | REQUIRED, INDEXED |
| `code_hash` | String | SHA256(train.py + rewards/*) — indexed | REQUIRED, INDEXED |
| `req_hash` | String | SHA256(requirements.txt) — indexed | REQUIRED, INDEXED |
| `config` | String | Frozen config.yaml text snapshot | REQUIRED |
| `train` | String | Frozen train.py text snapshot | REQUIRED |
| `rewards` | List[String] | Reward function file contents | `[]` |
| `rewards_filenames` | List[String] | Names of reward files | `[]` |
| `requirements` | String | Frozen requirements.txt text | REQUIRED |
| `scaffold_local_uri` | String | Path on worker machine | `""` |
| `scaffold_remote_uri` | String | Path on master/storage | `""` |
| `usable` | Boolean | Experiment is valid | true |
| `manual_save` | Boolean | Manually saved by user | false |
| `metrics_uri` | String | Pointer to training metrics | `""` |
| `hw_metrics_uri` | String | Pointer to hardware metrics | `""` |
| `description` | String | Narrative description | `""` |
| `created_at` | DateTime | Set by APOC trigger | Auto-set |
| `updated_at` | DateTime | Set by APOC trigger | Auto-set |

**Handshake Query** (uses 3 indexed hashes):
```cypher
MATCH (e:Experiment)
WHERE e.config_hash = $config_hash
  AND e.code_hash = $code_hash
  AND e.req_hash = $req_hash
RETURN e LIMIT 1
```

---

### 4. Checkpoint

**Purpose**: Saved weights at specific training steps
**PK**: `ckp_id` (UNIQUE constraint)

| Property | Type | Description | Default |
|----------|------|-------------|---------|
| `ckp_id` | String | Unique checkpoint identifier (UUID) | REQUIRED, UNIQUE |
| `epoch` | Integer | Training epoch number | REQUIRED |
| `run` | Integer | Run number within epoch | REQUIRED |
| `metrics_snapshot` | Dict | JSON metrics at save time | REQUIRED |
| `uri` | String | Storage location (file://, s3://, nfs://) or NULL | NULL (can be discarded) |
| `is_usable` | Boolean | Can be used for RESUME strategy | true |
| `is_merging` | Boolean | Participates in merge operation | false |
| `description` | String | Description | `""` |
| `created_at` | DateTime | Set by APOC trigger | Auto-set |
| `updated_at` | DateTime | Set by APOC trigger | Auto-set |

**Validation** (APOC trigger):
- Must have either `PRODUCED` relationship (from Experiment) OR `is_merging=true`
- Orphan checkpoints (no relationships, is_merging=false) trigger validation error

**Example Creation**:
```cypher
CREATE (c:Checkpoint {
  ckp_id: "ckp_exp123_e5r2",
  epoch: 5,
  run: 2,
  metrics_snapshot: {loss: 0.45, accuracy: 0.92},
  uri: "s3://my-bucket/checkpoints/exp123_e5_r2.pt",
  is_usable: true,
  is_merging: false
})
```

---

### 5. Component

**Purpose**: Capability matrix entry (technique × framework pair)
**PK**: Composite (technique_code, framework_code)

| Property | Type | Description | Default |
|----------|------|-------------|---------|
| `technique_code` | String | Fine-tuning technique (e.g., "grpo", "dpo", "sft") | REQUIRED |
| `framework_code` | String | Framework (e.g., "trl", "unsloth", "axolotl") | REQUIRED |
| `docs_url` | String | Documentation link | `""` |
| `description` | String | Description | `""` |
| `created_at` | DateTime | Set by APOC trigger | Auto-set |
| `updated_at` | DateTime | Set by APOC trigger | Auto-set |

**Composite UNIQUE Constraint**:
```cypher
CREATE CONSTRAINT unique_component_composite IF NOT EXISTS
  FOR (co:Component) REQUIRE (co.technique_code, co.framework_code) IS UNIQUE
```

**Seed Data**: 207 Components (23 techniques × 9 frameworks)
- Techniques: SFT, DPO, SIMPO, KTO, ORPO, PPO, GRPO, DAPO, VAPO, RLOO, REINFORCE_PP, DR_GRPO, FLOWRL, PRIME, GKD, SDFT, SDPO, GOLD, REWARD_MODELING (19 core, 23 total)
- Frameworks: TRL, UNSLOTH, AXOLOTL, TORCHTUNE, VERL, OPENRLHF, LLAMAFACTORY, NEMO, FROM_SCRATCH (9 total)

---

## Relationship Types

### 1. USED_FOR

**Direction**: Component → Experiment
**Cardinality**: Many-to-Many
**Purpose**: Which technique+framework pair was used for this experiment

```cypher
(c:Component) -[r:USED_FOR]-> (e:Experiment)
```

**Example**:
```cypher
MATCH (c:Component {technique_code: "grpo", framework_code: "trl"})
MATCH (e:Experiment {exp_id: "exp_123"})
CREATE (c) -[:USED_FOR]-> (e)
```

---

### 2. SELECTED_FOR

**Direction**: Model → Experiment
**Cardinality**: Many-to-Many
**Purpose**: Which base model was selected for this experiment

```cypher
(m:Model) -[r:SELECTED_FOR]-> (e:Experiment)
```

---

### 3. BASED_ON

**Direction**: Experiment → Recipe
**Cardinality**: Many-to-One
**Purpose**: Which recipe/dataset configuration sourced this experiment

```cypher
(e:Experiment) -[r:BASED_ON]-> (r:Recipe)
```

---

### 4. PRODUCED

**Direction**: Experiment → Checkpoint
**Cardinality**: One-to-Many
**Purpose**: Which experiment produced this checkpoint (atomic, immutable)

```cypher
(e:Experiment) -[r:PRODUCED]-> (c:Checkpoint)
```

---

### 5. DERIVED_FROM

**Direction**: Experiment → Experiment
**Cardinality**: Many-to-One
**Properties**: `diff_patch` (JSON with git-style diffs)
**Purpose**: Config/code changed (BRANCH strategy), logical branching

```cypher
(e1:Experiment) -[r:DERIVED_FROM {diff_patch: {...}}]-> (e2:Experiment)
```

**Strategy**: BRANCH

---

### 6. STARTED_FROM

**Direction**: Experiment → Checkpoint
**Cardinality**: Many-to-One (optional)
**Purpose**: Which checkpoint was used as weights baseline for BRANCH strategy

```cypher
(e:Experiment) -[r:STARTED_FROM]-> (c:Checkpoint)
```

**Strategy**: BRANCH (optional weights resumption)

---

### 7. RETRY_OF

**Direction**: Experiment → Experiment
**Cardinality**: Many-to-One
**Purpose**: Same config, different seed (RETRY strategy)

```cypher
(e1:Experiment) -[r:RETRY_OF]-> (e2:Experiment)
```

**Strategy**: RETRY

---

### 8. MERGED_FROM

**Direction**: Checkpoint → Checkpoint
**Cardinality**: Many-to-One
**Purpose**: New checkpoint created by merging source checkpoints

```cypher
(c1:Checkpoint) -[r:MERGED_FROM]-> (c_merged:Checkpoint)
```

---

## Constraints

| Constraint | Target | Properties | Type | Purpose |
|-----------|--------|-----------|------|---------|
| `unique_recipe_id` | Recipe | `recipe_id` | UNIQUE | Primary key |
| `unique_recipe_name` | Recipe | `name` | UNIQUE | User-facing identification |
| `unique_experiment_id` | Experiment | `exp_id` | UNIQUE | Primary key |
| `unique_checkpoint_id` | Checkpoint | `ckp_id` | UNIQUE | Primary key |
| `unique_model_name` | Model | `model_name` | UNIQUE | Primary key |
| `unique_component_composite` | Component | `(technique_code, framework_code)` | UNIQUE | Capability matrix integrity |

---

## Indexes

| Index | Target | Properties | Type | Purpose |
|-------|--------|-----------|------|---------|
| `idx_experiment_config_hash` | Experiment | `config_hash` | BTREE | Handshake lookup |
| `idx_experiment_code_hash` | Experiment | `code_hash` | BTREE | Handshake lookup |
| `idx_experiment_req_hash` | Experiment | `req_hash` | BTREE | Handshake lookup |

**Handshake Query Optimization**:
```cypher
MATCH (e:Experiment)
WHERE e.config_hash = $config_hash
  AND e.code_hash = $code_hash
  AND e.req_hash = $req_hash
RETURN e
```

All three hashes must be indexed for fast lookup on large graphs.

---

## APOC Triggers

### Trigger: Auto-set `created_at` on creation

```cypher
APOC TRIGGER: ON CREATE nodes
  SET node.created_at = datetime()
```

Fires on all node creations (Recipe, Model, Experiment, Checkpoint, Component).

### Trigger: Auto-set `updated_at` on modification

```cypher
APOC TRIGGER: ON SET properties
  SET node.updated_at = datetime()
```

Fires on all property updates.

### Trigger: Validate orphan checkpoints

```cypher
APOC TRIGGER: ON CREATE/SET Checkpoint
  IF NOT (
    (ckp:Checkpoint) -[:PRODUCED]-> Someone
    OR (ckp.is_merging = true)
  )
  THEN RAISE ERROR
```

Ensures every checkpoint has either:
- An incoming `PRODUCED` relationship (from Experiment), OR
- `is_merging = true` (participating in merge operation)

---

## Seed Data

### Components (207 nodes)

All (technique, framework) combinations are created on initialization:

```cypher
UNWIND [
  "sft", "dpo", "simpo", "kto", "orpo", "ppo", "grpo", "dapo", "vapo",
  "rloo", "reinforce_pp", "dr_grpo", "flowrl", "prime", "gkd", "sdft",
  "sdpo", "gold", "reward_modeling"
] AS technique
UNWIND [
  "trl", "unsloth", "axolotl", "torchtune", "verl",
  "openrlhf", "llamafactory", "nemo", "from_scratch"
] AS framework
MERGE (c:Component {
  technique_code: technique,
  framework_code: framework
})
SET c.created_at = coalesce(c.created_at, datetime()),
    c.updated_at = datetime()
```

**Result**: ~207 Component nodes created (count may vary based on complete technique list)

### Models (5+ nodes)

Core foundation models for reference/teacher roles:

- `meta-llama/Llama-2-7b`
- `meta-llama/Llama-3-8b`
- `meta-llama/Llama-3-70b`
- `mistralai/Mistral-7B-v0.1`
- `meta-llama/Llama-2-13b`

All created via idempotent `MERGE` operations.

---

## Integration Points

### Master API Handshake Endpoint

**Request**:
```json
{
  "config_hash": "sha256_of_config_yaml",
  "code_hash": "sha256_of_train_py_and_rewards",
  "req_hash": "sha256_of_requirements_txt",
  "strategy": "NEW|RESUME|BRANCH|RETRY",
  ...
}
```

**Query** (uses 3 BTREE indexes):
```cypher
MATCH (e:Experiment)
WHERE e.config_hash = $config_hash
  AND e.code_hash = $code_hash
  AND e.req_hash = $req_hash
RETURN e LIMIT 1
```

---

## Startup Initialization

On container startup (`docker-compose up`):

1. **01-schema.cypher** loads:
   - 5 node types with properties
   - 8 relationship types
   - 6 UNIQUE constraints
   - 3 BTREE indexes

2. **02-triggers.cypher** loads:
   - APOC triggers for `created_at`, `updated_at`
   - Orphan checkpoint validation

3. **03-seeds.cypher** loads:
   - 207 Component nodes (all technique × framework pairs)
   - 5+ Model nodes (foundation models)

**Idempotency**: All operations use `IF NOT EXISTS` (constraints), `MERGE` (nodes), or conditional logic.

---

## Verification Queries

### Verify node counts

```cypher
MATCH (r:Recipe) RETURN COUNT(r) AS recipe_count;
MATCH (m:Model) RETURN COUNT(m) AS model_count;
MATCH (e:Experiment) RETURN COUNT(e) AS experiment_count;
MATCH (c:Checkpoint) RETURN COUNT(c) AS checkpoint_count;
MATCH (co:Component) RETURN COUNT(co) AS component_count;
```

**Expected**:
- Components: ~207 (23 techniques × 9 frameworks)
- Models: 5+ (seed data)
- Recipes/Experiments/Checkpoints: 0 initially (populated by application)

### Verify constraints

```cypher
CALL db.constraints();
```

**Expected**: 6 constraints listed

### Verify indexes

```cypher
CALL db.indexes();
```

**Expected**: 3+ indexes (composite constraint may appear as index)

### Test constraint enforcement

```cypher
CREATE (r1:Recipe {recipe_id: "test_1", name: "test-recipe"});
CREATE (r2:Recipe {recipe_id: "test_2", name: "test-recipe"});
-- Expected: CONSTRAINT VIOLATION on second CREATE
```

---

## Troubleshooting

### Schema initialization fails on startup

**Check logs**:
```bash
docker logs lineage-master-api
```

**Common causes**:
- Neo4j not ready yet → init_schema.py retries 30 times
- Port 7687 not accessible → check docker-compose.yml port binding
- Memory issues → check Neo4j heap size in docker-compose.yml

### Indexes not created

**Verify manually**:
```cypher
CALL db.indexes();
```

If missing, run 01-schema.cypher directly in Neo4j browser.

### Seed data not loaded

**Check**:
```cypher
MATCH (co:Component) RETURN COUNT(co);
```

If 0, run 03-seeds.cypher directly.

---

## References

- **Pydantic Models**: `envelope/middleware/shared/nodes.py`
- **Lineage Architecture**: `.planning/docs/LINEAGE_SYSTEM_ARCHITECTURE.md`
- **Phase 13.1 Plan**: `.planning/phases/13.1/PLAN.md`
- **Neo4j 5.x Docs**: https://neo4j.com/docs/cypher-manual/5.0/

