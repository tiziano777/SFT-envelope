# Phase 13.1 — Schema Consolidation Overview & Corrections

## Critical Issues in Original PLAN.md

### ❌ ERROR 1: Wrong Relationship Types (Line 25)
**What I wrote:**
```
All relationship types (USES_DATASET, EMPLOYS_MODEL, EMPLOYS_COMPONENT, etc.)
```

**What it should be (from database-layer.md):**
```
7 RELATIONSHIP TYPES (only these):
1. PRODUCED_BY    → Checkpoint → Experiment
2. DERIVED_FROM   → Experiment → Experiment
3. RETRY_FROM     → Experiment → Experiment
4. MERGED_FROM    → Checkpoint → Checkpoint
5. USES_TECHNIQUE → Experiment → Component
6. USES_MODEL     → Experiment → Model
7. USES_RECIPE    → Experiment → Recipe
```

**Why this matters:** These are the ONLY 7 valid relationships. My schema must have exactly these — no USES_DATASET, EMPLOYS_COMPONENT, or similar.

---

## Refined Phase Structure

### FIX 1: Delete `database/schema_init.cypher` ✅
**Status**: CORRECT
- Redundant file (only has Recipe uniqueness)
- Consolidates into `master/neo4j/01-schema.cypher`

### FIX 2: Create `master/neo4j/01-schema.cypher` 🔧 CORRECTED
**Must contain:**

#### Node Types (5) + Properties
From Pydantic models in `envelope/config/models.py` and `envelope/middleware/shared/models.py`:

| Node | Properties | Source |
|------|-----------|--------|
| `Recipe` | `recipe_id`, `name`, `description`, `created_at`, `updated_at` | Phase 13 (RecipeConfig) |
| `Model` | `model_name`, `model_path`, `revision`, `created_at`, `updated_at` | ModelConfig |
| `Experiment` | `exp_id`, `config_hash`, `code_hash`, `req_hash`, `recipe_id`, `created_at`, `updated_at` | Phase 1 (ExperimentNode) |
| `Checkpoint` | `ckp_id`, `exp_id`, `epoch`, `run`, `is_merging`, `created_at`, `updated_at` | Phase 1 (CheckpointNode) |
| `Component` | `technique_code`, `framework_code`, `created_at`, `updated_at` | envelope/config/models.py (Technique + FrameworkBackend enums) |

#### Relationship Types (7)
```cypher
// Checkpoint belongs to Experiment
PRODUCED_BY (Checkpoint) -[r]-> (Experiment)

// Experiment derives from another (config/code change)
DERIVED_FROM (Experiment) -[r: {diff_patch}]-> (Experiment)

// Experiment retries from another (same config, different seed)
RETRY_FROM (Experiment) -[r]-> (Experiment)

// Checkpoint merges from other Checkpoints
MERGED_FROM (Checkpoint) -[r]-> (Checkpoint)

// Experiment uses technique+framework combo
USES_TECHNIQUE (Experiment) -[r]-> (Component)

// Experiment uses base model
USES_MODEL (Experiment) -[r]-> (Model)

// Experiment uses recipe/dataset
USES_RECIPE (Experiment) -[r]-> (Recipe)
```

#### Constraints (5) - from database-layer.md
```cypher
CREATE CONSTRAINT unique_recipe_id FOR (r:Recipe) REQUIRE r.recipe_id IS UNIQUE;
CREATE CONSTRAINT unique_exp_id FOR (e:Experiment) REQUIRE e.exp_id IS UNIQUE;
CREATE CONSTRAINT unique_ckp_id FOR (c:Checkpoint) REQUIRE c.ckp_id IS UNIQUE;
CREATE CONSTRAINT unique_model_name FOR (m:Model) REQUIRE m.model_name IS UNIQUE;
CREATE CONSTRAINT composite_component_key FOR (co:Component) REQUIRE (co.technique_code, co.framework_code) IS UNIQUE;
```

#### Indexes (3) - from database-layer.md
```cypher
CREATE INDEX idx_experiment_config_hash FOR (e:Experiment) ON (e.config_hash);
CREATE INDEX idx_experiment_code_hash FOR (e:Experiment) ON (e.code_hash);
CREATE INDEX idx_experiment_req_hash FOR (e:Experiment) ON (e.req_hash);
```

#### APOC Triggers (3) - from database-layer.md
```cypher
// Trigger 1: Auto-set created_at
CALL apoc.trigger.install('neo4j', 'created_at_trigger', ...)

// Trigger 2: Auto-set updated_at
CALL apoc.trigger.install('neo4j', 'updated_at_trigger', ...)

// Trigger 3: Orphan Checkpoint validation
CALL apoc.trigger.install('neo4j', 'orphan_checkpoint_validation', ...)
```

### FIX 3: Create `master/neo4j/02-seeds.cypher` 🔧 REFINED
**Must populate:**

#### Component Nodes
**Source:** `envelope/config/models.py`

From `Technique` enum (23 values):
```python
SFT, DPO, SIMPO, KTO, ORPO,        # Stage 1-2
PPO, GRPO, DAPO, VAPO,             # Stage 3 PPO family
RLOO, REINFORCE_PP, DR_GRPO,       # Stage 3 REINFORCE family
FLOWRL, PRIME,                      # Stage 3 Flow
GKD, SDFT, SDPO, GOLD,             # Distillation
REWARD_MODELING                     # Reward modeling
```
**Count:** 23 techniques

From `FrameworkBackend` enum (9 values):
```python
TRL, UNSLOTH, AXOLOTL, TORCHTUNE, VERL,
OPENRLHF, LLAMAFACTORY, NEMO, FROM_SCRATCH
```
**Count:** 9 frameworks

**Total Component nodes:** 23 × 9 = **207 nodes**

Each Component node:
```cypher
MERGE (c:Component {
  technique_code: "sft",
  framework_code: "trl",
  created_at: datetime(),
  updated_at: datetime()
})
```

#### Model Nodes
**Seed 3-5 core models** (foundation models for reference/teacher roles):

```cypher
MERGE (m:Model {
  model_name: "meta-llama/Llama-2-7b",
  model_path: "meta-llama/Llama-2-7b",
  revision: "main",
  created_at: datetime(),
  updated_at: datetime()
})

MERGE (m:Model {
  model_name: "meta-llama/Llama-3-8b",
  model_path: "meta-llama/Llama-3-8b",
  revision: "main",
  created_at: datetime(),
  updated_at: datetime()
})

MERGE (m:Model {
  model_name: "mistralai/Mistral-7B-v0.1",
  model_path: "mistralai/Mistral-7B-v0.1",
  revision: "main",
  created_at: datetime(),
  updated_at: datetime()
})
```

**Idempotency:** All use MERGE, not CREATE → safe on re-runs

---

## Tasks (Refined)

### Task 1: Delete `database/schema_init.cypher`
**Status:** READY ✅
**Effort:** <1 min
- Remove file entirely
- Git commit: "refactor: eliminate redundant database/schema_init.cypher"

### Task 2: Create `master/neo4j/01-schema.cypher`
**Status:** NEEDS REWRITE 🔧
**Effort:** 2-3 hours
**Action Items:**
- [ ] Write Cypher: 5 node type definitions
- [ ] Write Cypher: 7 relationship definitions (CORRECTED list above)
- [ ] Copy constraints (5x) from database-layer.md
- [ ] Copy indexes (3x) from database-layer.md
- [ ] Copy triggers (3x) from database-layer.md
- [ ] Add Cypher comments mapping properties to Pydantic fields
- [ ] Verify file is idempotent (all CREATE use IF NOT EXISTS)

### Task 3: Create `master/neo4j/02-seeds.cypher`
**Status:** NEEDS REWRITE 🔧
**Effort:** 1-2 hours
**Action Items:**
- [ ] Enumerate all 23 Technique enums + generate MERGE for Components
- [ ] Enumerate all 9 FrameworkBackend enums + generate MERGE for Components
- [ ] Create MERGE statements for 3-5 core Model nodes
- [ ] Verify all operations use MERGE (idempotent)
- [ ] Verify syntax

### Task 4: Update Docker initialization
**Status:** READY ✅
**Effort:** 30 min
- Load 01-schema.cypher → 02-seeds.cypher in order
- Update docker-entrypoint.sh or equivalent

### Task 5: Integration tests + documentation
**Status:** READY ✅
**Effort:** 1 hour
- Verify node types exist
- Verify ~207 Component nodes
- Verify 3+ Model nodes
- Test constraint enforcement
- Document in `.planning/docs/NEO4J_SCHEMA.md`

---

## Files to Create/Modify

| File | Action | Status |
|------|--------|--------|
| `database/schema_init.cypher` | DELETE | 📋 Ready |
| `master/neo4j/01-schema.cypher` | CREATE (rewrite from current schema.cypher) | 🔧 Needs spec |
| `master/neo4j/02-seeds.cypher` | CREATE | 🔧 Needs spec |
| `master/neo4j/schema.cypher` | Archive/rename? | ⚠️ Decide |
| `master/neo4j/triggers.cypher` | Keep as-is (merge into 01?) | ⚠️ Decide |
| Docker init script | UPDATE | ⚠️ Locate & update |

---

## Open Questions

1. **Should we merge triggers.cypher into 01-schema.cypher?**
   - Current state: separate files (schema.cypher, triggers.cypher)
   - Proposed: consolidate everything into 01-schema.cypher for single-file idempotency
   - **Decision needed:** Keep separate or consolidate?

2. **Recipe node properties — do we need more?**
   - Current spec: `recipe_id`, `name`, `description`, `created_at`, `updated_at`
   - From database-layer.md, I don't see recipe_id mentioned
   - **Decision needed:** Which properties from RecipeConfig should map to Recipe node?

3. **Experiment node — what about strategy/status fields?**
   - Current: `exp_id`, `config_hash`, `code_hash`, `req_hash`, `recipe_id`, `created_at`, `updated_at`
   - Missing?: `strategy` (NEW, RESUME, BRANCH, RETRY)?
   - Missing?: `status` (running, completed, failed)?
   - **Decision needed:** Should status/metadata be on Experiment node?

4. **Docker initialization — where is the entrypoint?**
   - Location: `docker-entrypoint.sh` or other?
   - Current: How does schema load today?
   - **Decision needed:** Which file to update?

---

## Summary

**What was wrong:**
- Relationship names were invented (USES_DATASET, EMPLOYS_MODEL) instead of spec (USES_TECHNIQUE)
- Node properties not cross-referenced to Pydantic models
- Missing clarity on what goes into which node

**What's fixed:**
- ✅ Exact 7 relationship types identified (only these)
- ✅ Node properties mapped to Pydantic enums
- ✅ Constraints, indexes, triggers sourced from database-layer.md
- ✅ Component seeding formula: 23 techniques × 9 frameworks = 207 nodes
- ✅ Model seeding: 3-5 foundation models

**Ready to proceed?**
User review + decision on 4 open questions above.
