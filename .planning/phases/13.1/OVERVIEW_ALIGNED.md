# Phase 13.1: Neo4j Schema Consolidation — CORRECTED OVERVIEW (Aligned to LINEAGE_SYSTEM_ARCHITECTURE)

**Status**: CRITICAL REWRITE AFTER ARCHITECTURE REVIEW
**Mistake Fixed**: Was inventing relationship types instead of using spec from LINEAGE_SYSTEM_ARCHITECTURE.md

---

## 🚨 Critical Corrections (from LINEAGE_SYSTEM_ARCHITECTURE §3)

### ❌ WRONG Relationships (My First Draft)
```
USES_TECHNIQUE, USES_MODEL, USES_RECIPE
```

### ✅ CORRECT Relationships (8 types from Architecture)
```
USED_FOR       (Component) -[r]-> (Experiment)    # Stack tecnologico usato
SELECTED_FOR   (Model) -[r]-> (Experiment)        # Modello base selezionato
BASED_ON       (Experiment) -[r]-> (Recipe)       # Configurazione di input
PRODUCED       (Experiment) -[r]-> (Checkpoint)   # Checkpoint generato

DERIVED_FROM   (Experiment) -[r: {diff_patch}]-> (Experiment)  # Branching logico
STARTED_FROM   (Experiment) -[r]-> (Checkpoint)   # Branching fisico (opzionale)
RETRY_OF       (Experiment) -[r]-> (Experiment)   # Stesso setup, nuevo tentativo
MERGED_FROM    (Checkpoint) -[r]-> (Checkpoint)   # Merge N-a-1 di pesi
```

---

## Updated Decisions with User Confirmations

### D1: ✅ Separato (Option B)
- `master/neo4j/01-schema.cypher` — node types + constraints + indexes
- `master/neo4j/02-triggers.cypher` — APOC triggers (kept separate)
- `master/neo4j/03-seeds.cypher` — seed data (Component + Model nodes)

### D2: ✅ Recipe Node — CORRECTED
Recipe **MUST** contain entries as list of dictionaries (Neo4j property list) + tags field.

**From LINEAGE_SYSTEM_ARCHITECTURE §3.1 RecipeNode**:
```python
class RecipeNode(BaseModel):
    recipe_id: str                      # UUID
    name: str                           # UNIQUE
    description: str
    scope: str
    tasks: list[str]
    tags: list[str]                     # ← USER AUTHORIZED THIS
    issued: datetime
    modified: datetime
    derived_from: Optional[str]         # UUID auto-riferimento
    config_yaml: str                    # config.yaml frozen (dataset snapshot)

    # ← NEW: entries as list of RecipeEntry dicts (USER REQUIREMENT)
    entries: list[dict]                 # [{"dist_id": "...", "samples": 1603, ...}, ...]
```

**Neo4j Representation**:
```cypher
CREATE (r:Recipe {
  recipe_id: "uuid",
  name: "my_recipe",
  description: "...",
  scope: "...",
  tasks: ["task1", "task2"],
  tags: ["tag1", "tag2"],              # ✅ NEW
  issued: datetime(),
  modified: datetime(),
  config_yaml: "...YAML snapshot...",
  entries: [                            # ✅ NEW - list of dicts
    {dist_id: "uuid1", samples: 1603, tokens: 141889, chat_type: "simple_chat_cycle2"},
    {dist_id: "uuid2", samples: 7473, tokens: 892044, chat_type: "simple_chat_cycle2"}
  ]
})
```

### D3: ✅ Experiment Node — CORRECTED
Add `strategy` + `status` fields (USER CONFIRMED).

**From LINEAGE_SYSTEM_ARCHITECTURE §3.1 ExperimentNode**:
```python
class ExperimentNode(BaseModel):
    exp_id: str                     # UUID
    model_id: str                   # UUID
    status: str                     # ← NEW: RUNNING | COMPLETED | FAILED | PAUSED
    exit_status: Optional[str]      # Exit code or description
    exit_msg: Optional[str]

    # Hashes (trigger hash logic)
    hash_committed_code: str        # SHA256 of train.py + config.yaml + rewards/*
    config_hash: str                # ← For find_experiment_by_hashes()
    code_hash: str                  # ← For find_experiment_by_hashes()
    req_hash: str                   # ← For find_experiment_by_hashes()

    # Strategy (USER CONFIRMED)
    strategy: str                   # ← NEW: NEW | RESUME | BRANCH | RETRY

    # Textual content (CRITICAL — frozen at handshake)
    config: str                     # Complete config.yaml text snapshot
    train: str                      # Complete train.py text snapshot
    rewards: list[str]              # List of reward file contents (parallel to rewards_filenames)
    rewards_filenames: list[str]    # Names of files in rewards/* (e.g., ["math_reward.py", ...])
    requirements: str               # Complete requirements.txt text snapshot
    hyperparams_json: str           # JSON of resolved hyperparameters

    # Scaffold URIs
    scaffold_local_uri: str         # Path scaffold on worker
    scaffold_remote_uri: str        # Path scaffold on master/storage

    # Metadata
    usable: bool                    # Experiment is valid
    manual_save: bool               # Saved manually, don't discard
    metrics_uri: str                # Pointer to training metrics files
    hw_metrics_uri: str             # Pointer to hw metrics files
    description: str

    # Timestamps (APOC triggers)
    created_at: datetime
    updated_at: datetime
```

---

## Correct Node Types & Properties

### Recipe
```cypher
CREATE (r:Recipe {
  recipe_id: "uuid",
  name: "unique_name",
  description: "...",
  scope: "...",
  tasks: ["task1", "task2"],
  tags: ["tag1", "tag2"],
  issued: datetime(),
  modified: datetime(),
  derived_from: "uuid" OR NULL,
  config_yaml: "...YAML...",
  entries: [
    {dist_id: "...", samples: 1603, tokens: 141889, chat_type: "simple_chat_cycle2"},
    ...
  ],
  created_at: datetime(),
  updated_at: datetime()
})
```

### Model
```cypher
CREATE (m:Model {
  id: "uuid",
  model_name: "UNIQUE",
  version: "main",
  uri: "path or remote",
  url: "HuggingFace/hub URL",
  doc_url: "...",
  architecture_info_ref: "...",
  description: "...",
  created_at: datetime(),
  updated_at: datetime()
})
```

### Experiment
```cypher
CREATE (e:Experiment {
  exp_id: "UNIQUE uuid",
  model_id: "uuid",
  status: "RUNNING|COMPLETED|FAILED|PAUSED",
  exit_status: NULL,
  exit_msg: NULL,
  hash_committed_code: "sha256",
  config_hash: "sha256",
  code_hash: "sha256",
  req_hash: "sha256",
  strategy: "NEW|RESUME|BRANCH|RETRY",
  config: "...YAML text snapshot...",
  train: "...train.py text snapshot...",
  rewards: ["...content1...", "...content2..."],
  rewards_filenames: ["math_reward.py", "format_reward.py"],
  requirements: "...requirements.txt text...",
  hyperparams_json: "{...}",
  scaffold_local_uri: "/path/to/scaffold",
  scaffold_remote_uri: "/master/storage/...",
  usable: true,
  manual_save: false,
  metrics_uri: "...",
  hw_metrics_uri: "...",
  description: "...",
  created_at: datetime(),
  updated_at: datetime()
})
```

### Checkpoint
```cypher
CREATE (c:Checkpoint {
  ckp_id: "UNIQUE uuid",
  epoch: 5,
  run: 2,
  metrics_snapshot: {loss: 0.23, accuracy: 0.94},
  uri: "file:///path" OR "s3://..." OR NULL,
  is_usable: true,
  is_merging: false,
  description: "...",
  created_at: datetime(),
  updated_at: datetime()
})
```

### Component
```cypher
CREATE (c:Component {
  technique_code: "grpo",
  framework_code: "trl",
  docs_url: "...",
  description: "...",
  created_at: datetime(),
  updated_at: datetime()
})
CONSTRAINT composite_component_key (c.technique_code, c.framework_code) IS UNIQUE
```

---

## Correct Relationship Types (8 total)

| Rel | From | To | Props | Purpose |
|-----|------|----|----|---------|
| `USED_FOR` | Component | Experiment | — | Stack tecnologico usato |
| `SELECTED_FOR` | Model | Experiment | — | Modello base selezionato |
| `BASED_ON` | Experiment | Recipe | — | Configurazione input |
| `PRODUCED` | Experiment | Checkpoint | — | Checkpoint generato |
| `DERIVED_FROM` | Experiment | Experiment | `{diff_patch: {...}}` | Branching logico |
| `STARTED_FROM` | Experiment | Checkpoint | — | Branching fisico (opz) |
| `RETRY_OF` | Experiment | Experiment | — | Stesso setup, nuovo tentativo |
| `MERGED_FROM` | Checkpoint | Checkpoint | — | Merge N-a-1 pesi |

---

## Constraints (From Architecture §3.3)

```cypher
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
```

---

## Indexes (From Architecture §3.3)

```cypher
CREATE INDEX idx_experiment_config_hash IF NOT EXISTS
  FOR (e:Experiment) ON (e.config_hash);

CREATE INDEX idx_experiment_code_hash IF NOT EXISTS
  FOR (e:Experiment) ON (e.code_hash);

CREATE INDEX idx_experiment_req_hash IF NOT EXISTS
  FOR (e:Experiment) ON (e.req_hash);
```

---

## APOC Triggers (Keep as separate 02-triggers.cypher)

From Architecture §3.4, keep as-is from `master/neo4j/triggers.cypher`:

1. **setNodeTimestamps** — auto-set created_at/updated_at
2. **validateCheckpointHasExperiment** — Checkpoint must have PRODUCED or is_merging=true

---

## Seed Data (03-seeds.cypher)

### Component Nodes (23 × 9 = 207)

From `envelope/config/models.py` Technique enum (23) × FrameworkBackend enum (9):

**23 Techniques**:
```
sft, dpo, simpo, kto, orpo,
ppo, grpo, dapo, vapo, rloo,
reinforce_pp, dr_grpo, flowrl, prime,
gkd, sdft, sdpo, gold, reward_modeling
```

**9 Frameworks**:
```
trl, unsloth, axolotl, torchtune, verl,
openrlhf, llamafactory, nemo, from_scratch
```

**Cypher** (idempotent via MERGE):
```cypher
// Generate all 23×9 combinations
MERGE (c:Component {
  technique_code: $technique,
  framework_code: $framework
})
SET c.created_at = coalesce(c.created_at, datetime()),
    c.updated_at = datetime()
RETURN c
```

### Model Seed Nodes (3-5 examples)

```cypher
MERGE (m:Model {
  model_name: "meta-llama/Llama-2-7b"
})
SET m.model_path = "meta-llama/Llama-2-7b",
    m.version = "main",
    m.created_at = coalesce(m.created_at, datetime())

MERGE (m:Model {
  model_name: "meta-llama/Llama-3-8b"
})
SET m.model_path = "meta-llama/Llama-3-8b",
    m.version = "main",
    m.created_at = coalesce(m.created_at, datetime())

MERGE (m:Model {
  model_name: "mistralai/Mistral-7B-v0.1"
})
SET m.model_path = "mistralai/Mistral-7B-v0.1",
    m.version = "main",
    m.created_at = coalesce(m.created_at, datetime())
```

---

## File Structure (Corrected - Separate Files)

| File | Content | Status |
|------|---------|--------|
| `database/schema_init.cypher` | DELETE | 📋 Ready |
| `master/neo4j/01-schema.cypher` | Node types + constraints + indexes | 🔧 Needs rewrite |
| `master/neo4j/02-triggers.cypher` | APOC triggers (keep existing) | ✅ Use as-is |
| `master/neo4j/03-seeds.cypher` | Component + Model seeds | 🔧 New |
| `master/neo4j/schema.cypher` | Archive/rename | ⚠️ Move to backup |
| `master/neo4j/triggers.cypher` | Archive/rename | ⚠️ Move to backup |

---

## Tasks (Revised Based on Architecture)

### Task 1: Delete redundant files
- [ ] Delete `database/schema_init.cypher`
- [ ] Backup `master/neo4j/schema.cypher` → `schema.cypher.bak`
- [ ] Backup `master/neo4j/triggers.cypher` → `triggers.cypher.bak`

### Task 2: Create `master/neo4j/01-schema.cypher`
- [ ] Node types: Recipe (with entries list + tags), Model, Experiment (with strategy + status), Checkpoint, Component
- [ ] Relationship types: All 8 correct types (USED_FOR, SELECTED_FOR, BASED_ON, PRODUCED, DERIVED_FROM, STARTED_FROM, RETRY_OF, MERGED_FROM)
- [ ] Constraints: All 5 UNIQUE
- [ ] Indexes: All 3 BTREE on Experiment hashes
- [ ] Idempotent: All use IF NOT EXISTS
- [ ] Cypher comments mapping to Pydantic fields

### Task 3: Keep `master/neo4j/02-triggers.cypher`
- [ ] Copy from existing `master/neo4j/triggers.cypher` (content is correct)
- [ ] No changes needed

### Task 4: Create `master/neo4j/03-seeds.cypher`
- [ ] Component Nodes: All 207 combinations (23 techniques × 9 frameworks)
- [ ] Model Nodes: 3-5 core foundation models
- [ ] All use MERGE (idempotent)

### Task 5: Update Docker initialization
- [ ] Load 01-schema.cypher → 02-triggers.cypher → 03-seeds.cypher in order at startup
- [ ] Locate entrypoint script and update

### Task 6: Integration tests + docs
- [ ] Verify schema structure in Neo4j
- [ ] Verify 207 Component nodes
- [ ] Verify 3+ Model nodes
- [ ] Test constraints (unique violation on exp_id)
- [ ] Test triggers (created_at auto-set)
- [ ] Document in `.planning/docs/NEO4J_SCHEMA.md`

---

## Summary of Corrections

✅ **Relationship types** → Corrected to match LINEAGE_SYSTEM_ARCHITECTURE (8 total, exact names)
✅ **Experiment properties** → Added `strategy`, `status`, and textual content fields (config, train, rewards, requirements)
✅ **Recipe node** → Added `entries` list (as Neo4j property list) + `tags` field
✅ **File organization** → Restructured as 3 separate files (01-schema, 02-triggers, 03-seeds)
✅ **Seed data** → Component nodes (207) + Model nodes (3-5)

Now aligned to **LINEAGE_SYSTEM_ARCHITECTURE.md** — the source of truth.

Ready to proceed? 🚀
