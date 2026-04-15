# Phase 13.1: Critical Schema Audit — Code vs. Plans

**Status**: DISCREPANCIES FOUND — Code is OUT OF SYNC with approved plans

---

## Discrepanza #1: ExperimentNode Missing Hash Fields

### Phase 2 PLAN (02-01-PLAN.md) specifies:
```cypher
# BTREE Indexes on Experiment hashes (lines 134-136)
CREATE INDEX idx_experiment_config_hash FOR (e:Experiment) ON (e.config_hash);
CREATE INDEX idx_experiment_code_hash FOR (e:Experiment) ON (e.code_hash);
CREATE INDEX idx_experiment_req_hash FOR (e:Experiment) ON (e.req_hash);
```

### Current Code (nodes.py) is MISSING:
```python
# Current ExperimentNode (nodes.py) does NOT have:
# - config_hash: str
# - code_hash: str
# - req_hash: str

# Instead it has:
hash_committed_code: str = ""  # ← This is NOT the same as the 3 hashes above!
```

### Root Issue:
- In Phase 1, the model was designed with `hash_committed_code` (single aggregated hash)
- In Phase 2 Database, the decision changed to 3 SEPARATE hashes for handshake detection
- The code in `nodes.py` was never updated to reflect this decision!

### Fix Required:
```python
class ExperimentNode(BaseNode):
    exp_id: str
    # ... other fields ...

    # ← REMOVE:
    # hash_committed_code: str = ""

    # ← ADD (for handshake find_experiment_by_hashes):
    config_hash: str = ""        # SHA256 sha hash, used for handshake detection
    code_hash: str = ""          # SHA256 of train.py + rewards/*
    req_hash: str = ""           # SHA256 of requirements.txt
```

---

## Discrepanza #2: ExperimentNode Has Redundant `hyperparams_json`

### User Confirmation:
> "In alte planning phases abbiamo risolto la questione del nodo experiment, integrando hyperparameters in config.yml, rendendo il campo hyperparameters ridondante"

### Current Code:
```python
class ExperimentNode(BaseNode):
    # ... lines 50-72 ...
    hyperparams_json: str = ""  # ← LINE 64 — SHOULD BE REMOVED
```

### Root Issue:
- On Phase 1,  hyperparams were added to support flexibility
- On later phases, decision was made: hyperparameters are part of config.yaml, don't need separate field
- The code still has this field (dead code)

### Fix Required:
```python
class ExperimentNode(BaseNode):
    # ← REMOVE line 64:
    # hyperparams_json: str = ""

    # Rationale: Hyperparameters are frozen as part of config.yaml snapshot
    # The config: str field contains the complete YAML, including hyperparameters
```

---

## Discrepanza #3: RecipeNode Missing `entries` Field

### User Requirement (D2):
> "Recipe node ha anche una lista di RecipeEntry object, qui non l'hai gestita come list di dizionari neo4J!! sicuramente dvrai aggiungere il campo composto lista entries"

### Current Code:
```python
class RecipeNode(BaseNode):
    recipe_id: str
    name: str
    description: str
    scope: str
    tasks: list[str]
    tags: list[str]
    issued: datetime
    modified: datetime
    derived_from: str | None = None
    config_yaml: str = ""
    # ← MISSING: entries: list[dict]
```

### LINEAGE_SYSTEM_ARCHITECTURE (§3.1) also confirms:
```
The field config_yaml contains one snapshot of the location of various datasets

/path/to/dataset/ARC-Challenge/downsampled__0.7__en:
  chat_type: simple_chat_cycle2
  dist_id: ecef45fc-ba10-471d-a8ba-39172cdbf388
  samples: 1603
  tokens: 141889

This should be in RecipeNode.entries
```

### Fix Required:
```python
class RecipeNode(BaseNode):
    # ... existing fields ...
    entries: list[dict[str, Any]] = Field(default_factory=list)
    # Each dict represents a RecipeEntry: {"dist_id": "...", "samples": 1603, "tokens": 141889, ...}
```

---

## Discrepanza #4: ComponentNode Has Unexpected Field`opt_code`

### Current Code (nodes.py):
```python
class ComponentNode(BaseNode):
    opt_code: str = Field(..., min_length=1, description="Optimization code/identifier")  # ← ???
    technique_code: str
    framework_code: str
    docs_url: str
    description: str
```

### LINEAGE_SYSTEM_ARCHITECTURE (§3.1) specifies:
```python
class Component:
    technique_code: str     # es. `grpo`, `sft`, `dpo`
    framework_code: str     # es. `trl`, `axolotl`, `fsdp`
    docs_url: str
    description: str
```

**NO `opt_code` field!**

### Root Issue:
Unknown where `opt_code` came from. It's not in the architecture spec and not used anywhere visible.

### Fix Required:
```python
class ComponentNode(BaseNode):
    # ← REMOVE: opt_code

    technique_code: str = Field(..., min_length=1)
    framework_code: str = Field(..., min_length=1)
    docs_url: str = ""
    description: str = ""
```

---

## Summary of Required Fixes

| Node | Fix | Why |
|------|-----|-----|
| **ExperimentNode** | Remove `hash_committed_code`, add `config_hash`, `code_hash`, `req_hash` | Phase 2 Database design mandates 3 separate hashes for handshake queries |
| **ExperimentNode** | Remove `hyperparams_json` | Dead code — hyperparams are frozen in config.yaml textual snapshot |
| **RecipeNode** | Add `entries: list[dict]` | User requirement + LINEAGE_SYSTEM_ARCHITECTURE §3.1 |
| **ComponentNode** | Remove `opt_code` | Not in spec, unknown origin |

---

## Action Plan (Before Proceeding with Phase 13.1)

**BLOCKER**: Cannot create accurate Neo4j schema if Pydantic models don't match the approved plans.

1. **[CRITICAL]** Update `envelope/middleware/shared/nodes.py`:
   - ✅ Add config_hash, code_hash, req_hash to ExperimentNode
   - ✅ Remove hash_committed_code from ExperimentNode
   - ✅ Remove hyperparams_json from ExperimentNode
   - ✅ Add entries: list[dict] to RecipeNode
   - ✅ Remove opt_code from ComponentNode

2. **Then Proceed**: After fixing nodes.py, can create accurate 01-schema.cypher (Phase 13.1 Task 2)

---

## Questions for User

1. Should I fix nodes.py now before continuing with Phase 13.1?
2. Confirm that `entries` should be `list[dict[str, Any]]` (generic dict, not typed RecipeEntry)?
3. Should we add fields like `strategy` and `status` to ExperimentNode (you confirmed D3)?

