# Phase 1: Shared Layer - Research

**Researched:** 2026-04-10
**Domain:** Pydantic v2 data contracts, deterministic hashing, text diffing
**Confidence:** HIGH

## Summary

Phase 1 defines all shared data contracts (Pydantic models) and utility functions (ConfigHasher, DiffEngine) used across Worker and Master layers. All code lives in a new package `envelope/middleware/shared/` and depends only on `pydantic` (already a project dependency) and Python stdlib modules (`hashlib`, `json`, `difflib`, `pathlib`, `datetime`, `enum`, `re`). No new external dependencies are required.

The architecture doc (`LINEAGE_SYSTEM_ARCHITECTURE.md`, Sections 3-4) is the single source of truth for field definitions, types, and behaviors. Existing Pydantic patterns in `envelope/config/models.py` provide the reference for coding style, enum patterns, Field usage, and model_validator patterns. The project already uses Pydantic 2.12.5 with pytest 9.0.2 on Python 3.10.18 (venv), so all target features are available.

**Primary recommendation:** Follow the architecture doc field specifications exactly, use the existing `envelope/config/models.py` as the style reference, and split into domain-focused modules per decision D-01.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Split `middleware/shared/` into domain-focused modules: `nodes.py`, `relations.py`, `envelopes.py`, `config_hasher.py`, `diff_engine.py`, plus `__init__.py` with re-exports. Rationale: small focused files, easy to navigate, matches the phase's natural domain boundaries.
- **D-02:** Create a `BaseNode(BaseModel)` with shared Neo4j fields (`id: str`, `created_at: datetime | None = None`, `updated_at: datetime | None = None`). All 5 node types (RecipeNode, ModelNode, ExperimentNode, CheckpointNode, ComponentNode) inherit from it. Avoids field duplication, enforces consistent Neo4j schema.
- **D-03:** ConfigHasher uses a "parse + normalize" strategy for deterministic SHA256 hashes: YAML files parsed with PyYAML then `json.dumps(data, sort_keys=True, ensure_ascii=True)` before hashing; Python files normalized line endings to `\n`, strip trailing whitespace per line; files sorted by relative path before concatenation; `requirements.txt` included in textual diff but excluded from trigger hash (per SHRD-09).
- **D-04:** Use Pydantic native `.model_dump_json()` / `.model_validate_json()` for HTTP transport. Add a `headers: dict[str, str] = Field(default_factory=dict)` field on all transport envelopes for future extensibility.

### Claude's Discretion
- Exact field names and types for each node/relation (follow architecture doc specifications)
- Internal implementation details of DiffEngine (algorithm choice, output format within the git-style spec)
- `__init__.py` re-export structure and `__all__` contents
- Whether to add a `BaseRelation` model or keep relations as standalone models

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SHRD-01 | Pydantic dataclass per tutti i nodi Neo4j (RecipeNode, ModelNode, ExperimentNode, CheckpointNode, ComponentNode) | Architecture doc Section 3.1 defines all fields. BaseNode pattern from D-02. Pydantic v2 BaseModel with Field constraints. |
| SHRD-02 | Enum RelationType per tutte le 8 relazioni del grafo | Architecture doc Section 3.2 defines all 8 relation types. Follow `str, Enum` pattern from existing models.py. |
| SHRD-03 | DerivedFromRel model con diff_patch strutturato | Architecture doc Section 3.2 + 4.2 define structure. diff_patch is `dict` with keys config/train/rewards/requirements/hyperparams. |
| SHRD-04 | Envelope operativi Worker->Master (HandshakeRequest, HandshakeResponse, CheckpointPush, SyncEvent) | Architecture doc Section 4.1 defines all fields. Add `headers: dict[str, str]` per D-04. |
| SHRD-05 | Strategy enum (NEW, RESUME, BRANCH, RETRY) | Architecture doc Section 4.1. `str, Enum` with UPPER_CASE values. |
| SHRD-06 | ConfigHasher calcola SHA256 deterministico su file trigger (config.yaml, train.py, rewards/*) | Architecture doc Section 4.2. YAML normalization via json.dumps(sort_keys=True). Python files: normalize line endings. |
| SHRD-07 | ConfigSnapshot serializzabile con aggregated_hash | Architecture doc Section 4.2. Pydantic BaseModel with snapshot_id = aggregated_hash. |
| SHRD-08 | DiffEngine produce diff git-style (line, type, content) tra snapshot | Architecture doc Section 4.2. Use `difflib.unified_diff` with `n=0` context and `@@` header parsing. |
| SHRD-09 | requirements.txt incluso nel diff testuale ma escluso dal trigger hash | ConfigHasher.TRIGGER_FILES excludes requirements.txt. DiffEngine.compute_scaffold_diff includes it. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Python 3.10+ (`X | Y` union syntax, not `Union[X, Y]`)
- Pydantic v2 for all data models
- Type hints on all public functions
- Test with pytest, lint with ruff
- `from __future__ import annotations` MUST be first import in every module
- Module docstrings required on every .py file
- Section separators: `# --- Section Name ---` (Unicode box-drawing)
- String enums use lowercase values (NOTE: Strategy enum uses UPPER_CASE values per architecture doc -- this is an exception since these are protocol constants, not YAML-serializable config values)
- Validation functions return `list[str]` of errors (empty = valid)
- Use code-review-graph MCP tools before Grep/Glob/Read for codebase exploration

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 | All data models, serialization, validation | Already a project dependency, v2 with native JSON serialization | [VERIFIED: venv pip]
| hashlib | stdlib | SHA256 hashing | Python stdlib, deterministic, no external deps | [VERIFIED: stdlib]
| difflib | stdlib | Unified diff computation | Python stdlib, standard diff algorithm | [VERIFIED: stdlib]
| json | stdlib | YAML normalization for deterministic hashing | sort_keys + ensure_ascii gives canonical form | [VERIFIED: stdlib]
| pyyaml | 6.0+ | Parse YAML config files for hashing | Already a project dependency | [VERIFIED: pyproject.toml]
| pathlib | stdlib | File path operations | Python stdlib | [VERIFIED: stdlib]

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| re | stdlib | Parse `@@` headers from difflib output | DiffEngine line number extraction |
| uuid | stdlib | Generate UUIDs for node IDs | Creating new node instances in tests |
| datetime | stdlib | Timestamp fields on nodes and snapshots | BaseNode.created_at/updated_at, ConfigSnapshot.created_at |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| difflib | unidiff (pypi) | External dep for marginal benefit; difflib is sufficient for line-level git-style diffs |
| json.dumps(sort_keys) for YAML normalization | canonical-json (pypi) | json.dumps with sort_keys=True + ensure_ascii=True is canonical enough for our use case |
| hashlib.sha256 | xxhash (pypi) | Faster but SHA256 is the standard for content-addressable hashing and is specified in the architecture doc |

**Installation:**
```bash
# No new packages needed -- all dependencies already in pyproject.toml or stdlib
```

## Architecture Patterns

### Recommended Project Structure
```
envelope/
  middleware/
    __init__.py              # Package marker (can be empty or minimal)
    shared/
      __init__.py            # Re-exports: all public classes/enums
      nodes.py               # BaseNode + 5 Neo4j node types (SHRD-01)
      relations.py           # RelationType enum + DerivedFromRel (SHRD-02, SHRD-03)
      envelopes.py           # Strategy enum + 4 transport envelopes (SHRD-04, SHRD-05)
      config_hasher.py       # ConfigHasher + ConfigSnapshot (SHRD-06, SHRD-07, SHRD-09)
      diff_engine.py         # DiffEngine (SHRD-08)
tests/
  unit/
    test_nodes.py            # Node instantiation, field validation, BaseNode inheritance
    test_relations.py        # RelationType enum, DerivedFromRel serialization
    test_envelopes.py        # Transport envelope serialization roundtrip
    test_config_hasher.py    # Deterministic hashing, trigger file filtering
    test_diff_engine.py      # Git-style diff output, edge cases
```

### Pattern 1: BaseNode Inheritance
**What:** Shared base class for all Neo4j node types with common fields.
**When to use:** All node models inherit from this.
**Example:**
```python
# Source: Architecture doc Section 3.1 + Decision D-02
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field

class BaseNode(BaseModel):
    """Base for all Neo4j node types with shared timestamp fields."""
    id: str = Field(..., description="UUID primary key")
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

### Pattern 2: Pydantic v2 Enum Pattern (matching existing codebase)
**What:** String enums following project convention.
**When to use:** All enum types in the shared layer.
**Example:**
```python
# Source: envelope/config/models.py existing pattern
from enum import Enum

class RelationType(str, Enum):
    USED_FOR = "USED_FOR"
    SELECTED_FOR = "SELECTED_FOR"
    BASED_ON = "BASED_ON"
    PRODUCED = "PRODUCED"
    DERIVED_FROM = "DERIVED_FROM"
    STARTED_FROM = "STARTED_FROM"
    RETRY_OF = "RETRY_OF"
    MERGED_FROM = "MERGED_FROM"
```

### Pattern 3: Transport Envelope with Headers
**What:** Pydantic models for HTTP transport with extensibility headers.
**When to use:** All 4 transport envelopes (per D-04).
**Example:**
```python
# Source: Architecture doc Section 4.1 + Decision D-04
class HandshakeRequest(BaseModel):
    """Worker -> Master handshake request."""
    config_hash: str
    req_hash: str
    code_hash: str
    # ... other fields ...
    headers: dict[str, str] = Field(default_factory=dict)
```

### Pattern 4: ConfigHasher Normalization
**What:** Deterministic SHA256 via parse-then-normalize.
**When to use:** ConfigHasher for all file types.
**Example:**
```python
# Source: Decision D-03, verified with pydantic 2.12.5 + pyyaml
import hashlib, json, yaml

def _hash_yaml_content(content: bytes) -> str:
    """Parse YAML, normalize to sorted JSON, then SHA256."""
    data = yaml.safe_load(content)
    normalized = json.dumps(data, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def _hash_python_content(content: bytes) -> str:
    """Normalize line endings and strip trailing whitespace, then SHA256."""
    text = content.decode("utf-8")
    lines = [line.rstrip() for line in text.splitlines()]
    normalized = "\n".join(lines)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
```

### Pattern 5: DiffEngine with difflib
**What:** Parse `difflib.unified_diff` output into structured diff entries.
**When to use:** DiffEngine.compute_file_diff.
**Example:**
```python
# Source: Architecture doc Section 4.2, verified with Python 3.10 difflib
import difflib
import re

def compute_file_diff(old_text: str, new_text: str) -> list[dict]:
    """Produce list of {line, type, content} from unified diff."""
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    result = []
    old_ln = 0
    new_ln = 0
    for line in difflib.unified_diff(old_lines, new_lines, lineterm="", n=0):
        if line.startswith("@@"):
            m = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            if m:
                old_ln = int(m.group(1)) - 1  # will be incremented on first -
                new_ln = int(m.group(3)) - 1  # will be incremented on first +
            continue
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("-"):
            old_ln += 1
            result.append({"line": old_ln, "type": "removed", "content": line[1:]})
        elif line.startswith("+"):
            new_ln += 1
            result.append({"line": new_ln, "type": "added", "content": line[1:]})
    return result
```

### Anti-Patterns to Avoid
- **Using `Optional[X]` instead of `X | None`**: Project convention requires Python 3.10+ union syntax.
- **Forgetting `from __future__ import annotations`**: MUST be first import in every module.
- **Hashing raw YAML text directly**: Key ordering in YAML is non-deterministic across tools. Always parse then normalize.
- **Using `difflib.ndiff` or `difflib.context_diff`**: Architecture doc specifies git-style (unified) diff format. Use `unified_diff` only.
- **Including `requirements.txt` in trigger hash**: Per SHRD-09, it is in diff but excluded from hash.
- **Adding `Union`, `Optional`, `Dict`, `List` imports from typing**: Use native Python 3.10+ generics.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text diffing | Custom diff algorithm | `difflib.unified_diff` | Handles edge cases (empty files, binary, insertions/deletions) correctly |
| JSON serialization | Custom datetime serializer | `model_dump_json()` / `model_validate_json()` | Pydantic v2 natively handles datetime as ISO 8601 |
| YAML canonical form | Custom YAML normalizer | `yaml.safe_load` + `json.dumps(sort_keys=True)` | Resolves anchors, normalizes key order, handles all YAML types |
| UUID generation | Custom ID scheme | `uuid.uuid4()` | Standard, collision-resistant |
| Field validation | Manual if/else checking | Pydantic `Field(gt=0)`, `Field(min_length=1)` | Declarative, automatic error messages |

**Key insight:** This phase is entirely data contracts and pure functions. No IO, no state, no concurrency. Every component is testable in isolation with no mocking required.

## Common Pitfalls

### Pitfall 1: difflib @@ Header Format Variations
**What goes wrong:** `difflib.unified_diff` omits the count in `@@` headers when count=1 (e.g., `@@ -2 +2 @@` instead of `@@ -2,1 +2,1 @@`). Also uses `@@ -0,0 +1,N @@` for pure additions and `@@ -1,N +0,0 @@` for pure deletions.
**Why it happens:** This is standard unified diff format but many implementations assume the count is always present.
**How to avoid:** Use regex `r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@"` with optional groups. Default missing count to 1.
**Warning signs:** Off-by-one line numbers in diff output. [VERIFIED: Python 3.10 difflib]

### Pitfall 2: YAML Anchors and Aliases
**What goes wrong:** Two YAML files with identical data but different anchor usage produce different raw text but should hash identically.
**Why it happens:** YAML anchors (`&anchor`) and aliases (`*anchor`) are syntactic sugar.
**How to avoid:** Decision D-03 already handles this: `yaml.safe_load` resolves all anchors before normalization. [VERIFIED: pyyaml 6.0]
**Warning signs:** Same config producing different hashes when saved by different tools.

### Pitfall 3: Empty rewards/ Directory
**What goes wrong:** ConfigHasher fails when `rewards/` directory is empty or does not exist.
**Why it happens:** `TRIGGER_DIRS = ["rewards"]` tries to glob `rewards/*.py` but finds nothing.
**How to avoid:** Handle empty/missing directories gracefully -- an empty rewards dir means no reward files contribute to the hash. The sorted file list is simply empty for that component.
**Warning signs:** `FileNotFoundError` or empty hash contribution.

### Pitfall 4: File Encoding Inconsistencies
**What goes wrong:** SHA256 differs for the same file content read on different platforms due to encoding.
**Why it happens:** Default encoding varies by OS. Windows may use UTF-16 or latin-1.
**How to avoid:** Always open files with `encoding="utf-8"` explicitly. Normalize line endings to `\n` for Python files (per D-03).
**Warning signs:** Hash mismatch between macOS development and Linux training servers.

### Pitfall 5: Pydantic v2 model_dump vs model_dump_json for Neo4j
**What goes wrong:** `model_dump()` returns Python objects (datetime as datetime), while Neo4j driver expects specific types.
**Why it happens:** Phase 1 defines models, Phase 2 will use them with Neo4j. The serialization format matters for downstream compatibility.
**How to avoid:** Models should work with both `model_dump()` (for in-memory use) and `model_dump_json()` / `model_validate_json()` (for HTTP transport). Do not add custom serializers that break either mode. Use `model_dump(mode="json")` when datetime needs to be string.
**Warning signs:** Test failures when Phase 2 tries to store node properties in Neo4j.

### Pitfall 6: Aggregated Hash Ordering Sensitivity
**What goes wrong:** Aggregated hash changes when files are discovered in different order by filesystem.
**Why it happens:** `os.listdir()` and `Path.glob()` do not guarantee order. Different filesystems return different orders.
**How to avoid:** Decision D-03 mandates sorting by relative path before concatenation. Use `sorted()` explicitly on all file discovery operations.
**Warning signs:** Same scaffold producing different aggregated_hash on different runs or machines.

### Pitfall 7: DerivedFromRel rewards Structure
**What goes wrong:** Architecture doc shows `rewards` as a dict `{filename: [diff_entries]}` in diff_patch, not a flat list like the other fields.
**Why it happens:** Multiple reward files need individual diffs keyed by filename.
**How to avoid:** DerivedFromRel.diff_patch type should be `dict[str, Any]` where `config`, `train`, `requirements`, `hyperparams` are `list[dict]` but `rewards` is `dict[str, list[dict]]`. Type this carefully.
**Warning signs:** Serialization errors when rewards has multiple files.

## Code Examples

Verified patterns from the existing codebase and architecture doc:

### Node Model with Inheritance
```python
# Source: Architecture doc Section 3.1, Decision D-02
# Follow envelope/config/models.py patterns
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field

class BaseNode(BaseModel):
    """Base for all Neo4j node types."""
    id: str = Field(..., min_length=1, description="UUID primary key")
    created_at: datetime | None = None
    updated_at: datetime | None = None

class ExperimentNode(BaseNode):
    """Experiment instance -- core tracking entity."""
    exp_id: str = Field(..., min_length=1)
    model_id: str
    status: str = "RUNNING"
    exit_status: str | None = None
    exit_msg: str | None = None
    hash_committed_code: str
    config: str         # config.yaml text snapshot
    train: str          # train.py text snapshot
    rewards: list[str] = Field(default_factory=list)
    rewards_filenames: list[str] = Field(default_factory=list)
    requirements: str = ""
    hyperparams_json: str = ""
    scaffold_local_uri: str = ""
    scaffold_remote_uri: str = ""
    usable: bool = True
    manual_save: bool = False
    metrics_uri: str = ""
    hw_metrics_uri: str = ""
    description: str = ""
```

### Transport Envelope Serialization Roundtrip Test
```python
# Source: Verified with pydantic 2.12.5
def test_handshake_request_roundtrip():
    req = HandshakeRequest(
        config_hash="abc123",
        req_hash="def456",
        code_hash="ghi789",
        scaffold_path="/tmp/setup_test",
        recipe_id="r-001",
        model_id="m-001",
        config_text="lr: 1e-4",
        train_text="import torch",
        requirements_text="torch>=2.0",
        rewards_texts=["def reward(): return 1.0"],
        rewards_filenames=["math_reward.py"],
    )
    json_str = req.model_dump_json()
    restored = HandshakeRequest.model_validate_json(json_str)
    assert req == restored
```

### ConfigHasher Determinism Test
```python
# Source: Decision D-03, verified behavior
def test_yaml_hash_deterministic_regardless_of_key_order():
    yaml_v1 = b"b: 2\na: 1\n"
    yaml_v2 = b"a: 1\nb: 2\n"
    # Both parse to {"a": 1, "b": 2} then normalize to same JSON
    assert ConfigHasher._hash_yaml_content(yaml_v1) == ConfigHasher._hash_yaml_content(yaml_v2)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `json()` / `parse_raw()` | Pydantic v2 `model_dump_json()` / `model_validate_json()` | Pydantic 2.0 (2023) | Method names changed, performance improved |
| `Optional[X]` from typing | `X \| None` native | Python 3.10 (2021) | Cleaner syntax, project convention |
| `Dict[str, Any]` from typing | `dict[str, Any]` native | Python 3.9+ (2020) | No typing imports needed |
| `@validator` (v1) | `@model_validator(mode="after")` (v2) | Pydantic 2.0 (2023) | Different API, returns self |

**Deprecated/outdated:**
- `BaseModel.json()` / `BaseModel.parse_raw()`: Use `model_dump_json()` / `model_validate_json()` instead [VERIFIED: pydantic 2.12.5]
- `BaseModel.dict()`: Use `model_dump()` instead [VERIFIED: pydantic 2.12.5]
- `@validator`: Use `@field_validator` or `@model_validator` instead [VERIFIED: pydantic 2.12.5]

## Assumptions Log

> List all claims tagged `[ASSUMED]` in this research.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Strategy enum uses UPPER_CASE values (NEW, RESUME, BRANCH, RETRY) rather than lowercase -- this deviates from the project's existing lowercase enum convention but matches the architecture doc exactly | Architecture Patterns | Low -- architecture doc is authoritative; these are protocol constants, not YAML config values |
| A2 | BaseNode `id` field name is acceptable even though each node type also has a specific ID field (exp_id, ckp_id, recipe_id) | Architecture Patterns | Medium -- if downstream code expects only specific ID fields, BaseNode.id could cause confusion. Architecture doc lists `id: UUID` on ModelNode but uses `exp_id`, `recipe_id`, `ckp_id` on others |

**Note on A2:** The architecture doc is inconsistent -- ModelNode has `id: UUID` while ExperimentNode has `exp_id: UUID`, RecipeNode has `recipe_id: str`, etc. Recommendation: use specific ID fields as the primary key per node type, and keep BaseNode with only `created_at`/`updated_at`. The `id` on BaseNode from D-02 may need to be reconsidered or made the *generic* UUID while each node also has its domain-specific ID alias. This should be clarified during implementation.

## Open Questions

1. **BaseNode.id vs node-specific IDs**
   - What we know: Architecture doc uses `recipe_id`, `exp_id`, `ckp_id`, `model_name` as unique keys per node type. Decision D-02 specifies BaseNode with `id: str`.
   - What's unclear: Should BaseNode.id be the *same* field as the node-specific ID, or an additional generic field?
   - Recommendation: Make BaseNode carry only `created_at` and `updated_at`. Each node defines its own primary key field. This matches the architecture doc precisely and avoids redundancy. If D-02's `id` is strictly required, make it an alias or drop it in favor of per-node IDs.

2. **ComponentNode UNIQUE constraint is composite (technique_code, framework_code) -- no single ID field**
   - What we know: Architecture doc Section 3.3 shows `REQUIRE (c.technique_code, c.framework_code) IS UNIQUE`. ComponentNode has no UUID field.
   - What's unclear: Should ComponentNode inherit BaseNode.id at all?
   - Recommendation: ComponentNode can skip the `id` field since its uniqueness is composite. This reinforces making BaseNode minimal (timestamps only).

3. **DiffEntry model vs plain dict**
   - What we know: Architecture doc uses `list[dict]` with keys `line`, `type`, `content`. DerivedFromRel.diff_patch is `dict`.
   - What's unclear: Whether to formalize DiffEntry as a Pydantic model or keep as typed dict.
   - Recommendation: Create a `DiffEntry(BaseModel)` with `line: int`, `type: str`, `content: str` for type safety. Use it in DerivedFromRel and DiffEngine. Serialize via model_dump() for JSON storage. This is Claude's discretion per CONTEXT.md.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `.venv/bin/python -m pytest tests/unit/test_nodes.py tests/unit/test_relations.py tests/unit/test_envelopes.py tests/unit/test_config_hasher.py tests/unit/test_diff_engine.py -x -q` |
| Full suite command | `.venv/bin/python -m pytest tests/ -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SHRD-01 | 5 node types instantiable with field validation | unit | `.venv/bin/python -m pytest tests/unit/test_nodes.py -x` | Wave 0 |
| SHRD-02 | RelationType enum with 8 members | unit | `.venv/bin/python -m pytest tests/unit/test_relations.py -x` | Wave 0 |
| SHRD-03 | DerivedFromRel model with diff_patch serialization | unit | `.venv/bin/python -m pytest tests/unit/test_relations.py -x` | Wave 0 |
| SHRD-04 | 4 transport envelopes serialize/deserialize correctly | unit | `.venv/bin/python -m pytest tests/unit/test_envelopes.py -x` | Wave 0 |
| SHRD-05 | Strategy enum with 4 values | unit | `.venv/bin/python -m pytest tests/unit/test_envelopes.py -x` | Wave 0 |
| SHRD-06 | ConfigHasher deterministic SHA256 on trigger files | unit | `.venv/bin/python -m pytest tests/unit/test_config_hasher.py -x` | Wave 0 |
| SHRD-07 | ConfigSnapshot serializable with aggregated_hash | unit | `.venv/bin/python -m pytest tests/unit/test_config_hasher.py -x` | Wave 0 |
| SHRD-08 | DiffEngine produces git-style diff | unit | `.venv/bin/python -m pytest tests/unit/test_diff_engine.py -x` | Wave 0 |
| SHRD-09 | requirements.txt in diff but excluded from trigger hash | unit | `.venv/bin/python -m pytest tests/unit/test_config_hasher.py::test_requirements_excluded_from_hash -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/bin/python -m pytest tests/unit/test_nodes.py tests/unit/test_relations.py tests/unit/test_envelopes.py tests/unit/test_config_hasher.py tests/unit/test_diff_engine.py -x -q`
- **Per wave merge:** `.venv/bin/python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_nodes.py` -- covers SHRD-01
- [ ] `tests/unit/test_relations.py` -- covers SHRD-02, SHRD-03
- [ ] `tests/unit/test_envelopes.py` -- covers SHRD-04, SHRD-05
- [ ] `tests/unit/test_config_hasher.py` -- covers SHRD-06, SHRD-07, SHRD-09
- [ ] `tests/unit/test_diff_engine.py` -- covers SHRD-08
- [ ] `envelope/middleware/__init__.py` -- package marker
- [ ] `envelope/middleware/shared/__init__.py` -- re-exports

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A -- no auth in shared layer |
| V3 Session Management | No | N/A -- no sessions |
| V4 Access Control | No | N/A -- no access control |
| V5 Input Validation | Yes | Pydantic Field constraints (min_length, gt, ge, le) |
| V6 Cryptography | No | SHA256 is used for content addressing, not security |

### Known Threat Patterns for this phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Hash collision for config identity | Spoofing | SHA256 is collision-resistant for this use case; not security-critical |
| Malformed YAML causing parse errors | Tampering | yaml.safe_load (no code execution); Pydantic validation on parsed data |
| Oversized field values in transport envelopes | Denial of Service | Pydantic Field constraints; max_length if needed on text fields (downstream concern for API layer) |

**Note:** This phase has minimal security surface. All models are data contracts with Pydantic validation. No network IO, no file writes to untrusted locations, no user-facing API. Security becomes relevant in Phase 4 (Master API) and Phase 6 (Worker).

## Sources

### Primary (HIGH confidence)
- `LINEAGE_SYSTEM_ARCHITECTURE.md` Sections 3-4 -- Complete field specifications for all nodes, relations, envelopes, ConfigHasher, DiffEngine
- `envelope/config/models.py` -- Reference Pydantic v2 patterns (verified in codebase)
- `.planning/codebase/CONVENTIONS.md` -- Naming, import, code style conventions (verified in codebase)
- `.planning/phases/01-shared-layer/01-CONTEXT.md` -- Locked decisions D-01 through D-04

### Secondary (MEDIUM confidence)
- Pydantic 2.12.5 `model_dump_json()` / `model_validate_json()` roundtrip -- [VERIFIED: tested in venv]
- `difflib.unified_diff` output format and `@@` header parsing -- [VERIFIED: tested in venv with Python 3.10.18]
- YAML normalization determinism via `yaml.safe_load` + `json.dumps(sort_keys=True)` -- [VERIFIED: tested in venv]

### Tertiary (LOW confidence)
- None -- all claims verified against codebase or runtime tests.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries are stdlib or already in pyproject.toml, versions verified
- Architecture: HIGH -- architecture doc is comprehensive, all field definitions specified
- Pitfalls: HIGH -- verified difflib behavior, YAML normalization, and Pydantic serialization through runtime tests

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (stable domain, no fast-moving dependencies)
