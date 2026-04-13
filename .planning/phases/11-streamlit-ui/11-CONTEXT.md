---
phase: 11-streamlit-ui
type: context
depends_on: [04-master-api, 02-database-layer, 01-shared-layer]
---

# Phase 11 Context: Streamlit Master UI — SFT Studio

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a Streamlit dashboard for the Master service enabling live CRUD operations on the Neo4j lineage graph. Users can:
- **a) Load & Browse Recipes** — Import YAML files (with detailed validation errors), search/filter read-only recipe list
- **b) Manage Models** — Create, read, update; delete only if not linked to experiments
- **c) Manage Components** — Create, read, update; delete only if not linked to experiments
- **d) Manage Experiments** — Create, read, update (create auto-links Recipe/Model/Component); no delete capability
- **e) Update Constraints** — All updates modify only descriptive fields (description, version, docs_url, status); never ID/URI/hash/name fields

This is the first UI for the Master service, focused on administrative operations for SFT-stage setup and tracking.

</domain>

<decisions>
## Implementation Decisions

### ID Generation & Uniqueness
- **D-01:** All node IDs (recipe_id, model_name, opt_code, exp_id) are generated as UUID v4 on creation (app-side generation)
- **D-02:** User provides display names or references (e.g., descriptive recipe name); UUID becomes immutable PK in Neo4j

### Delete Constraints (Strict for Now)
- **D-03:** Delete is blocked for ANY node that has ANY outgoing or incoming relationship (stringent: no exceptions for now)
  - Model DELETE blocked if ∃ (Experiment)-[:USES_MODEL]->(Model)
  - Component DELETE blocked if ∃ (Experiment)-[:USES_TECHNIQUE]->(Component)
  - Recipe DELETE blocked if ∃ (Experiment)-[:USES_RECIPE]->(Recipe)
  - This constraint is versioning for future relaxation (e.g., cascade vs. orphan handling)
- **D-04:** Delete validation is app-side (query before delete) with user-facing error message: "Cannot delete: {N} experiment(s) depend on this node. Delete those first or change their recipes/models."
  - App-side allows custom error UX; DB-side enforcement (APOC trigger) can be added later for safety
- **D-05:** Checkpoint nodes are never deleted via UI (implicit: not exposed in CRUD operations)

### Recipe Upload & Validation
- **D-06:** YAML validation uses Pydantic v2 EnvelopeConfig directly; if parse fails, show field-level error with location (line number, field name, expected type)
- **D-07:** Upload is all-or-nothing: single invalid recipe blocks the import (no partial uploads)
- **D-08:** Recipe YAML is stored in RecipeNode.config_yaml field (full YAML text as string); user can later re-export or reference it
- **D-09:** Recipe import creates RecipeNode with UUID recipe_id, issued=now, modified=now

### Model & Component Creation
- **D-10:** Create form has required field: user provides display name/identifier upfront
  - Model: user provides `model_name` (unique constraint)
  - Component: user provides `opt_code`, `technique_code`, `framework_code` (composite unique constraint)
- **D-11:** Version, description, doc_url are optional fields with sensible defaults (empty string)

### Experiment Creation & Relationships
- **D-12:** Experiment creation requires explicit selection: user picks Recipe, Model, Component from dropdowns (not auto-filtered)
- **D-13:** On success, UI auto-creates relations: USES_RECIPE, USES_MODEL, USES_TECHNIQUE
- **D-14:** exp_id is generated as UUID (not user-provided); optional: user can set custom description for the experiment

### Update Operations (Immutable-by-Default)
- **D-15:** Updates allow ONLY descriptive fields:
  - Recipe: description, tags (config_yaml immutable after creation)
  - Model: description, version, doc_url, url (model_name immutable)
  - Component: description, docs_url (technique_code, framework_code, opt_code immutable)
  - Experiment: description, status, exit_status, exit_msg (exp_id, recipe_id, model_id immutable)
- **D-16:** PATCH endpoint validates that request does not try to modify immutable fields; returns 400 if so

### Browse & Search
- **D-17:** Browse pages (Recipe, Model, Component, Experiment) list all nodes with pagination/virtual scroll
- **D-18:** Filter UI provided for each entity:
  - Recipe: by name, tags, issued_date_range (read-only list, no edit from browser)
  - Model: by model_name, version
  - Component: by opt_code, technique, framework
  - Experiment: by status, recipe_id, model_id, created_at_range

### Error Messaging
- **D-19:** Pydantic validation errors from Neo4j API responses are parsed and shown as user-friendly msgs (not raw stack traces)
- **D-20:** Delete-protected errors include reason: "This node has N relationships. Delete dependent items first."

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Database & API Layer
- `.planning/phases/01-shared-layer/01-CONTEXT.md` — Node types (RecipeNode, ModelNode, ComponentNode, ExperimentNode, CheckpointNode) and field definitions
- `.planning/phases/02-database-layer/02-CONTEXT.md` — UNIQUE constraints, APOC triggers, Neo4j schema
- `.planning/phases/04-master-api/04-CONTEXT.md` — Master API endpoints, error handling patterns, async repository methods
- `docs/lineage/database-layer.md` — Comprehensive DB schema, repository API, relation types (USES_RECIPE, USES_MODEL, USES_TECHNIQUE, PRODUCED_BY, DERIVED_FROM, RETRY_FROM, MERGED_FROM)
- `envelope/config/models.py` — EnvelopeConfig Pydantic schema for YAML validation
- `envelope/middleware/shared/nodes.py` — RecipeNode, ModelNode, ComponentNode, ExperimentNode definitions

### UI & Frontend
- `CLAUDE.md` (project): Standard code conventions (Pydantic v2, type hints, Click, Rich, async)
- No existing Streamlit docs yet — this is greenfield UI

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **ExperimentRepositoryAsync**: All CRUD methods available (`get_experiment()`, `create_experiment()`, `get_latest_checkpoint()`, etc.); use directly for Neo4j queries
- **Pydantic v2 Models**: RecipeNode, ModelNode, ComponentNode, ExperimentNode with validation; leverage for form validation
- **EnvelopeConfig**: Complete YAML schema; use for recipe upload validation
- **Error Hierarchy**: Custom exceptions (ExperimentAlreadyExists, RepositoryError) from Phase 2; follow pattern for UI errors

### Established Patterns
- **Async-first**: All DB operations are async; UI layer must use StreamlitAsync or handle async context via Streamlit's callback patterns
- **Semantic HTTP Status Codes**: Master API uses 404, 409, 400, 500; UI translates to user messages
- **ABC-based extensibility**: BaseStorageWriter, BaseExperimentRepository; models not impacted by UI

### Integration Points
- **Master API Endpoints** (from Phase 4): UI calls POST/PATCH/GET endpoints on master service (not direct DB access)
  - POST `/experiments` — create experiment
  - PATCH `/experiments/{exp_id}` — update experiment
  - GET `/experiments` — list/search experiments
  - (Similar for models, components, recipes — new endpoints to be defined in Phase 11 planning)
- **Neo4j Connection**: UI may connect directly to Neo4j for advanced queries (search/browse) or route through Master API
- **Docker Deployment**: UI runs as Streamlit container in docker-compose

</code_context>

<specifics>
## Specific Ideas

- **Admin Interface Feel**: Streamlit is perfect for admin tooling; keep it functional and fast, not glossy
- **Dark Mode Ready**: Use Streamlit's built-in theme support; no custom CSS needed initially
- **Recipe Import Drag-Drop**: Streamlit's `file_uploader()` with YAML preview before commit
- **Expandable Details**: Use `st.expander()` for related data (experiments using a model, lineage graph snippets, etc.)
- **Relationship Visualization**: Neo4j query results as text tables for now (future: visual browser with Cytoscape)

</specifics>

<deferred>
## Deferred Ideas

- Web-based entity graph visualization (Cytoscape/D3) — next phase
- Advanced filtering (full-text search, date range pickers) — v1.1
- Batch operations (import multiple recipes, bulk update) — v1.1
- User roles & RBAC (admin vs. read-only) — future phase
- Audit trail UI (who changed what, when) — future phase

</deferred>

---

*Phase: 11-streamlit-ui*
*Context gathered: 2026-04-13*
