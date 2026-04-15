# Phase 12: Recipe UI Improvements + Neo4j Re-validation

**Date:** 2026-04-14
**Status:** PLANNED
**Mode:** TDD (Test-Driven Development)

## Objective

Enhance Streamlit Recipe Management UI with:
1. Minimal sidebar (redundancy removal)
2. Recipe entry display & management
3. Edit recipe name/description
4. Delete recipe with confirmation
5. Unique constraint on recipe names
6. Full test suite execution + feedback loop
7. Re-validate Neo4j async operations

## Requirements (User Stories)

### 0. Sidebar Redundancy
**User Story:** As a user, I want a minimal sidebar with essentials only
- Current: Full 5-item menu (Recipes, Models, Components, Experiments, Health Check)
- Desired: Show only "Recipes" + "Health Check" (keep minimal)
- **Test:** `test_sidebar_minimal` - Verify no redundant nav items

### 1 & 3. Recipe Entry Display
**User Story:** As a user, I want to view all dataset entries in a recipe
- Show entries list (paths + metadata: dist_id, samples, tokens, words)
- Expandable entry details
- **Tests:**
  - `test_view_recipe_shows_entries` - Entry list displayed
  - `test_entry_expandable_details` - Shows dist_id, samples, tokens, words

### 2. Recipe Edit (Name & Description)
**User Story:** As a user, I want to edit recipe name and description
- Edit form in Browse tab
- Validation: unique name check before save
- **Tests:**
  - `test_edit_recipe_name` - Update name (with uniqueness check)
  - `test_edit_recipe_description` - Update description

### 4. Recipe Deletion
**User Story:** As a user, I want to delete recipes with confirmation
- Delete button with confirmation dialog
- Soft delete flag or hard delete from DB
- **Test:** `test_delete_recipe_with_confirmation` - Delete + confirm

### 5. Unique Constraint on Recipe Name
**User Story:** As a user, I want unique recipe names (DB + model level)
- Add unique constraint in RecipeConfig model
- Add DB-level check in RecipeManager
- Return 409 Conflict on duplicate
- **Tests:**
  - `test_recipe_name_unique_model_validation` - Pydantic validation
  - `test_recipe_name_unique_db_check` - Neo4j uniqueness

### 6. Test Execution & Feedback Loop
**Implementation:** Run tests → capture feedback → iterate improvements
- Execute full test suite: `pytest streamlit_ui/tests/`
- Review failures/gaps
- Implement improvements
- Re-run tests

### 7. Neo4j Async Re-validation
**Implementation:** Re-run Neo4j async operation tests
- Tests: `streamlit_ui/tests/test_neo4j_async.py`
- Verify: `get_driver()`, recipe CRUD async methods

---

## Acceptance Criteria (Tasks)

### Phase Delivery Checklist

✅ **T1:** RecipeConfig.name unique constraint (model + DB)
✅ **T2:** RecipeManager CRUD methods: `get_by_name()`, `update()`, `delete()`
✅ **T3:** Sidebar minimal (only Recipes + Health Check)
✅ **T4:** Recipe view shows entry list + expandable details
✅ **T5:** Recipe edit modal (name + description + uniqueness check)
✅ **T6:** Recipe delete with confirmation dialog
✅ **T7:** All tests passing (recipes + neo4j async)
✅ **T8:** Feedback loop completed

---

## Implementation Plan (TDDD Approach)

### Phase 1: Model & Backend (Tests First)

**Files:**
- `envelope/config/models.py` — Add unique constraint to RecipeConfig
- `streamlit_ui/crud/recipe_manager.py` — **NEW** CRUD manager
- `streamlit_ui/tests/test_recipes.py` — Recipe management tests
- `streamlit_ui/tests/test_neo4j_async.py` — Re-verify async operations

**Step 1.1: Define Tests** (Write test specs)
- RecipeEntry display tests
- Unique name validation tests
- CRUD operation tests (create, read, update, delete)
- Neo4j async operation tests

**Step 1.2: Implement Models**
- Add `unique=True` constraint to RecipeConfig.name
- Update RecipeEntry to ensure all fields present

**Step 1.3: Implement RecipeManager CRUD**
- `get_recipe_by_id(id)` → RecipeConfig + entries
- `get_recipe_by_name(name)` → Check uniqueness
- `update_recipe(id, name, description)` → With uniqueness check
- `delete_recipe(id)` → Remove from DB
- `list_recipes_with_entries()` → Full data

**Step 1.4: Run Tests**
- Execute: `pytest streamlit_ui/tests/test_recipes.py -v`
- Re-run: `pytest streamlit_ui/tests/test_neo4j_async.py -v`
- Fix failures iteratively

### Phase 2: Streamlit UI (After Backend Ready)

**Files:**
- `streamlit_ui/app.py` — Simplify sidebar
- `streamlit_ui/pages/recipes.py` — Refactor with tabs:
  - Upload tab (existing)
  - Browse tab (list + search)
  - View tab (entries + details)
  - Edit tab (name + description + delete)

**Step 2.1: Sidebar Minimization**
- Remove redundant nav items (Models, Components, Experiments)
- Keep only: Recipes, Health Check

**Step 2.2: Recipe View Component**
- Display entry list in table (path, dist_id, samples, tokens, words)
- Expandable row for full entry metadata

**Step 2.3: Recipe Edit Component**
- Form to edit name (with uniqueness feedback)
- Form to edit description
- Delete button with confirmation

**Step 2.4: Integrate CRUD in UI**
- Call RecipeManager methods for each operation
- Handle async/await properly
- Show error messages for conflicts (409)

### Phase 3: Integration Testing & Feedback Loop

**Step 3.1: Run Full Test Suite**
```bash
pytest streamlit_ui/tests/ -v --tb=short
```

**Step 3.2: Capture Test Results**
- List all passing/failing tests
- Note error patterns

**Step 3.3: Feedback Iteration**
- Fix test failures
- Re-test after each fix
- Document improvements

**Step 3.4: Neo4j Async Validation**
```bash
pytest streamlit_ui/tests/test_neo4j_async.py -v
```

---

## Risk & Mitigation

| Risk | Mitigation |
|------|-----------|
| Unique constraint breaks existing recipes | Migrate DB before adding constraint |
| Async operations break in tests | Mock Neo4j client properly |
| UI complexity increases | Keep components modular & testable |
| Tests fail due to dependencies | Install test dependencies first |

---

## Rollback Plan

If critical failures occur:
- Revert commits in order: edit → sidebar → models
- Restore backup DB snapshot
- Re-run tests to confirm recovery

---

## Definition of Done

- [x] Issue documented: `.planning/issues/ISSUE-RECIPE-UI-IMPROVEMENTS.md`
- [ ] Phase plan: `.planning/phases/12/PLAN.md` ← **THIS FILE**
- [ ] Tests written: `test_recipes.py` + `test_neo4j_async.py`
- [ ] Implementation complete
- [ ] All tests passing (100%)
- [ ] Feedback loop executed
- [ ] Commit with all changes
- [ ] Documentation updated

---

## Verification Checklist

After implementation, verify:

✅ Sidebar shows only: Recipes, Health Check
✅ Recipe view displays all entries with metadata
✅ Edit form updates name (unique) & description
✅ Delete button removes recipes after confirmation
✅ Unique name constraint enforced (409 error on duplicate)
✅ All 40+ tests passing
✅ Neo4j async operations working correctly
✅ No regressions in other features

---

## Next Steps

1. **Execute Phase 12 PLAN.md** with `gsd-execute-phase`
2. Run tests iteratively
3. Capture feedback
4. Update VERIFICATION.md with results
5. Archive phase as COMPLETE
