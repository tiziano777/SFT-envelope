# Phase 1: Shared Layer - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Define all Pydantic data contracts and utility functions used across Worker and Master: 5 Neo4j node types, 8 relation types (including DerivedFromRel with diff_patch), 4 transport envelopes, Strategy enum, ConfigHasher (SHA256), ConfigSnapshot, and DiffEngine (git-style diffs). All new code goes into `envelope/middleware/shared/`. No existing files are modified.

</domain>

<decisions>
## Implementation Decisions

### Module Layout
- **D-01:** Split `middleware/shared/` into domain-focused modules: `nodes.py`, `relations.py`, `envelopes.py`, `config_hasher.py`, `diff_engine.py`, plus `__init__.py` with re-exports. Rationale: small focused files, easy to navigate, matches the phase's natural domain boundaries.

### Model Base Pattern
- **D-02:** Create a `BaseNode(BaseModel)` with shared Neo4j fields (`id: str`, `created_at: datetime | None = None`, `updated_at: datetime | None = None`). All 5 node types (RecipeNode, ModelNode, ExperimentNode, CheckpointNode, ComponentNode) inherit from it. Avoids field duplication, enforces consistent Neo4j schema.

### Hash Determinism
- **D-03:** ConfigHasher uses a "parse + normalize" strategy for deterministic SHA256 hashes:
  - YAML files: parse with PyYAML, then `json.dumps(data, sort_keys=True, ensure_ascii=True)` before hashing
  - Python files (.py) and reward modules: normalize line endings to `\n`, strip trailing whitespace per line
  - Files sorted by relative path before concatenation
  - `requirements.txt` is included in the textual diff but excluded from the trigger hash (per SHRD-09)

### Serialization Format
- **D-04:** Use Pydantic native `.model_dump_json()` / `.model_validate_json()` for HTTP transport. Add a `headers: dict[str, str] = Field(default_factory=dict)` field on all transport envelopes for future extensibility (custom metadata, versioning, routing info). FastAPI handles this natively — zero custom protocol overhead.

### Claude's Discretion
- Exact field names and types for each node/relation (follow architecture doc specifications)
- Internal implementation details of DiffEngine (algorithm choice, output format within the git-style spec)
- `__init__.py` re-export structure and `__all__` contents
- Whether to add a `BaseRelation` model or keep relations as standalone models

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture Specification
- `LINEAGE_SYSTEM_ARCHITECTURE.md` — Complete data model specification (Sections 2-4: nodes, relations, envelopes, ConfigHasher, DiffEngine, Cypher constraints). This is the primary source of truth for field definitions, types, and behaviors.

### Existing Code Patterns
- `envelope/config/models.py` — Reference for Pydantic v2 patterns, enum definitions, BaseModel usage, model_validator patterns
- `envelope/config/defaults.py` — Reference for constant/default value organization

### Project Conventions
- `.planning/codebase/CONVENTIONS.md` — Naming conventions, import order, code style, Pydantic model design patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `envelope/config/models.py`: Existing Pydantic v2 patterns (enums as `str, Enum`, `Field(...)` with constraints, `model_validator(mode="after")`) — follow same patterns in lineage models
- `from __future__ import annotations` — MUST be first import in every new module (project convention)

### Established Patterns
- String enums use lowercase values: `class Technique(str, Enum): GRPO = "grpo"`
- Module-level section separators: `# ─── Section Name ───`
- Module docstrings required on every .py file
- Type hints use Python 3.10+ syntax: `X | Y` not `Union[X, Y]`, `dict[str, Any]` not `Dict[str, Any]`
- Validation functions return `list[str]` of errors (empty = valid)

### Integration Points
- `envelope/middleware/shared/` is a new package — needs `__init__.py` at `middleware/` and `middleware/shared/` levels
- Phase 2 (DB Layer) will import node/relation models directly
- Phase 4 (Master API) will import transport envelopes for request/response schemas
- Phase 6 (Worker Layer) will import envelopes and ConfigHasher/DiffEngine

</code_context>

<specifics>
## Specific Ideas

- Transport envelopes must include `headers: dict[str, str]` for future extensibility — user explicitly requested this to avoid locked-in protocol
- ConfigHasher parse+normalize approach: YAML gets JSON-serialized with sorted keys before hashing, Python files get line-ending normalization

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-shared-layer*
*Context gathered: 2026-04-10*
