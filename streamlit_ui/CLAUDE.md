# CLAUDE.md -- streamlit_ui/

UI subsystem for FineTuning Envelope. Streamlit frontend + Neo4j-backed CRUD layer.

## General Rules

Inherit from project CLAUDE.md:
- Python 3.10+ (union syntax `X | Y`)
- Pydantic v2 for all models
- Type hints on public functions
- TDD: pytest + quick iterations
- Think before code. Surface tradeoffs. Ask if unclear.
- Simplicity first. Minimum code. No speculative features.
- Surgical changes. Touch only what's asked. Clean up your own mess.

## UI Architecture

### Structure

```
streamlit_ui/
├── app.py                    # Main entry + page routing
├── config.py                 # Config (Neo4j URI, API URL)
├── crud/
│   ├── entities/             # Pydantic models (Recipe, Model, Experiment, Component)
│   │   ├── base.py          # BaseEntity (id, created_at, updated_at)
│   │   └── {entity}.py      # Entity models with validation
│   └── repository/           # Data layer (Neo4j queries)
│       ├── {entity}_repository.py  # CRUD ops via Cypher
│       └── manager.py        # (REMOVED) Logic moved to repository
├── ui_pages/                 # Streamlit pages
│   ├── recipes.py           # Recipe CRUD UI
│   ├── models.py            # Model CRUD UI
│   ├── experiments.py       # Experiment CRUD UI
│   ├── components.py        # Component CRUD UI
│   └── health_check.py      # DB/API status
├── db/
│   ├── neo4j_async.py       # Async Neo4j client wrapper
│   └── health.py            # Connection health checks
└── utils/
    ├── errors.py            # UIError, DuplicateRecipeError exceptions
    ├── recipe_validation.py  # YAML parsing + validation
    ├── entity_constraints.py # Cross-field validation
    └── {enums}.py           # ScopeEnum, TaskEnum
```

### Page Pattern

Each `ui_pages/{entity}.py` follows:

```python
# 1. Async helpers (wrap repository calls)
async def create_{entity}_async(...):
    db_client = get_neo4j_client()
    repo = {Entity}Repository(db_client)
    return await repo.create(...)

# 2. Main render function
def run() -> None:
    st.title(...)
    tab1, tab2 = st.tabs(["Upload", "Browse"])
    # Tab 1: Create
    # Tab 2: List + Edit + Delete (via expanders)
```

**Key:** Async helpers isolate DB calls. UI layer stays thin.

### CRUD Layer

**Entity** (Pydantic model):
- Inherits `BaseEntity` (id, created_at, updated_at)
- Validates shape + cross-field logic
- No DB knowledge

**Repository** (Neo4j queries):
- Implements: `create()`, `list_with_limit()`, `search()`, `update()`, `delete()`, `is_deletable()`
- All Cypher scripts in method bodies
- Returns dict for JSON serialization to UI

### Neo4j Schema

Version-controlled at `neo4j/`:
- `01-schema.cypher` — Node types, constraints, indexes (idempotent)
- `02-triggers.cypher` — APOC triggers for timestamps
- `03-seeds.cypher` — Seed data (Components, Models)

Loaded via `ensure_schema_initialized()` in app.py on startup (once per session).

### Error Handling

**Custom exceptions** (utils/errors.py):
- `UIError(user_message, details)` — User-safe message + log details
- `DuplicateRecipeError` — Name collision with recovery UI

**Pattern:**
```python
try:
    # CRUD op
except UIError as e:
    st.error(f"Error: {e.user_message}")
    st.caption(e.details)  # Tech details for logs
```

### Session State

Streamlit session_state for:
- `config` — Loaded from env (Neo4j URI, API URL)
- `api_token` — From MASTER_API_TOKEN env
- `current_page` — Sidebar page selection
- `schema_initialized` — One-time flag for DDL load
- `{entity}_{action}_{key}` — Per-form edit/delete toggles

### Dependencies

- **streamlit** — UI framework
- **pydantic v2** — Data validation
- **neo4j** — Async driver
- **pyyaml** — Recipe YAML parsing

### Testing

- `tests/` — pytest suite
- Import pattern: relative imports within streamlit_ui
- Fixtures in `conftest.py` (mock db_client, async loop)
- Test asyncio ops: use `pytest-asyncio`

## Metadata Fields (Recipe Example)

Root-level YAML metadata flows end-to-end:

```yaml
name: my_recipe
description: "..."
scope: sft
tasks: [task1, task2]
tags: [tag1, tag2]
derived_from: <parent-uuid>  # Optional: parent recipe reference
entries:
  dist_uri: {dist_id, dist_name, ...}
```

→ Parsed by RecipeRepository.create_from_yaml() → Entity validation → Neo4j node → UI display

All 5 metadata fields (scope, tasks, tags, derived_from, description) persist. Display in Browse tab under metadata section.

## Key Files to Touch

| Path | Role | Caution |
|------|------|---------|
| `crud/entities/{entity}.py` | Schema + validation | Schema changes require DDL + seed updates |
| `crud/repository/{entity}_repository.py` | Query logic | Test new queries in isolation |
| `ui_pages/{entity}.py` | UI render | Wrap DB calls in async helpers |
| `utils/recipe_validation.py` | YAML parsing | Only edit if format changes |
| `master/neo4j/01-schema.cypher` | DDL | Idempotent (CREATE IF NOT EXISTS) |

## Common Patterns

### Add a field to Recipe

1. Edit `crud/entities/recipe.py` → Add Pydantic field
2. Update `master/neo4j/01-schema.cypher` → Add property in MERGE
3. Update `crud/repository/recipe_repository.py` → Map field in all 6 queries (CREATE, SELECT, UPDATE, LIST, SEARCH, SEARCH_DERIVED)
4. Update `ui_pages/recipes.py` → Display in Browse tab + Edit form
5. Test: run pytest, upload YAML with new field, verify Browse display

### Fix UI Display of Field

- Check if field exists in entity (crud/entities/)
- Check if field returned by repository query (RETURN clause)
- Add display line in ui_pages page (st.write(f"**{Field}:** {recipe.get(...)}")
- Verify async syntax: no direct DB calls in run() render loop

## Sync with Project

General guidelines + tools in parent CLAUDE.md override this file for conflicts. Non-UI code (envelope/, tests/) follows envelope/ patterns, not UI patterns.

---

**Last updated:** 2026-04-17 | **Version:** 1.0
