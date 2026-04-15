# Quick Task: Phase 12 Recipe UI Fixes - Plan

**Date:** 2026-04-15
**Task:** Fix Phase 12 recipe UI: 1) Add Neo4j unique constraint + Pydantic validation + UI alert modal for duplicate names 2) Debug & fix recipe entries not displaying in browse tab

## Objective

Resolve two critical Phase 12 issues to enable core recipe functionality:
1. **Recipe Name Uniqueness** — Enforce unique recipe names at DB + model layer, show UI alert on duplicate
2. **Recipe Entries Display** — Debug why recipe entries don't appear in browse tab; fix backend/frontend/URI issues

## Must-Haves

- ✅ Unique constraint on `Recipe.name` in Neo4j (schema update OR app-level enforcement)
- ✅ Pydantic validation enforcing uniqueness on RecipeConfig.name
- ✅ RecipeManager returns 409 Conflict on duplicate name attempts
- ✅ UI modal/alert when user tries to save duplicate recipe name
- ✅ Recipe entries displaying in browse tab (debug + fix root cause)
- ✅ Tests passing for both fixes

## Tasks

### Task 1: Add Recipe Name Uniqueness Constraint

**Files:**
- `master/neo4j/schema.cypher` — Add UNIQUE constraint
- `envelope/config/models.py` — Add unique validation to RecipeConfig
- `streamlit_ui/crud/recipe_manager.py` — Handle constraint violation in create() method

**Action:**
1. Add `CREATE CONSTRAINT unique_recipe_name IF NOT EXISTS FOR (r:Recipe) REQUIRE r.name IS UNIQUE;` to schema.cypher
2. Add `@model_validator` to RecipeConfig.name ensuring uniqueness or add `unique=True` constraint (Pydantic v2: use Field(..., json_schema_extra={"unique": true}))
3. Update RecipeManager.create_recipe() to catch Neo4j constraint violation and raise UIError with message "Recipe name already exists"

**Verify:**
- ✓ Schema can be applied via `./scripts/neo4j-init.sh` (or manually in Neo4j)
- ✓ RecipeConfig validates single instance (no uniqueness at instance level — DB enforces globally)
- ✓ RecipeManager.create() raises UIError on duplicate

**Done:**
- Schema updated
- Validation in place
- Manager error handling ready

### Task 2: Add UI Alert Modal for Duplicate Names

**Files:**
- `streamlit_ui/ui_pages/recipes.py` — Catch UIError when creating recipe

**Action:**
1. In recipes.py Upload tab, when `create_recipe_async()` raises UIError with "already exists" message
2. Show `st.error()` or modal-like alert: "⚠️ Recipe name already exists. Change name or stop the recipe load."
3. Allow user to retry with different name

**Verify:**
- ✓ Try uploading 2 recipes with same name → second attempt shows alert
- ✓ User can retry with different name

**Done:**
- Modal/alert working

### Task 3: Debug Recipe Entries Not Displaying

**Files:**
- `streamlit_ui/crud/recipe_manager.py` — Verify entries are being saved and retrieved
- `streamlit_ui/ui_pages/recipes.py` — Check Browse tab rendering logic
- `master/neo4j/schema.cypher` — Verify Recipe node structure

**Investigation Plan:**
1. **Backend Verification:**
   - Check if entries are saved in Neo4j when recipe is created (inspect DB directly or add debug logging)
   - Verify RecipeManager.list_recipes() returns entries field populated
   - Check if entries JSON is valid (not corrupted)

2. **Frontend Verification:**
   - In Browse tab, after fetching recipes, add debug: `st.write(recipe)` to see full recipe object
   - Check if "entries" key exists in returned dict
   - Check if entries is non-empty

3. **URI Mismatch Check:**
   - Verify if recipe URIs (dist_uri) are local paths (e.g., `/data/...`) or Docker paths (e.g., `/mnt/...`)
   - Check if the app can access these paths (may need Docker volume mount adjustment)
   - Verify dist_uri is correctly formatted and accessible

4. **Root Cause Strategy:**
   - If entries is null/missing in DB → Issue is in save (create_recipe_async)
   - If entries is in DB but not in UI → Issue is in query (list_recipes_async) or rendering
   - If entries show but URIs inaccessible → Docker volume/path issue

**Verify:**
- ✓ Recipe entries appear in Browse tab
- ✓ Entries show metadata (dist_id, samples, tokens, words)
- ✓ Each entry's dist_uri is accessible (or noted if not)

**Done:**
- Entries displaying
- Root cause documented

## Execution Order

1. **First:** Task 1 (uniqueness constraint) — foundation for Task 2
2. **Then:** Task 2 (UI alert) — depends on Task 1 errorhandling
3. **Parallel:** Task 3 (entries debug) — independent, can run in parallel or sequentially

## Notes

- Phase 12 PLAN.md mentions these issues but implementation hasn't started
- RecipeEntry model already exists in envelope/config/models.py with fields: dist_id, dist_uri, samples, tokens, words, etc.
- RecipeConfig expects entries dict: `dict[str, RecipeEntry]`
- Neo4j schema currently has constraint on recipe_id but NOT on name

## Risk

- **High:** Entries debug may reveal XML/URI issues requiring Docker re-config
- **Medium:** Unique constraint may fail if duplicates already exist in DB (prior migration needed)
- **Low:** UI alert implementation straightforward with Streamlit

## Success Criteria

✅ Recipe name uniqueness enforced (Neo4j + Pydantic + UI)
✅ Duplicate name attempt shows user-friendly alert
✅ Recipe entries display in Browse tab with metadata
✅ All Phase 12 tests passing
✅ No regressions in other features
