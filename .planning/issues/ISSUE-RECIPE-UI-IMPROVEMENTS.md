# Issue: Streamlit Recipe Management UI Improvements

**Status:** NEW
**Severity:** HIGH
**Date:** 2026-04-14
**Related:** ISSUE-RECIPE-NAME-ATTRIBUTE (previous fix)

## Problems & Requirements

### 0. Sidebar Redundancy
- **Current:** Full sidebar with recipe navigation
- **Required:** Minimal, essentials only

### 1. Recipe View - Missing Entry Display
- **Current:** View shows recipe metadata only
- **Required:** Display all dataset entries (paths + metadata)

### 2. Recipe Edit - Limited Functionality
- **Current:** Cannot modify description or name after creation
- **Required:** Edit description & name in recipe management

### 3. Recipe Entry Display
- **Current:** No way to view individual entry details
- **Required:** List & view entry data (dist_id, samples, tokens, etc.)

### 4. Recipe Deletion
- **Current:** No delete functionality
- **Required:** Delete recipe with confirmation

### 5. Unique Recipe Names
- **Current:** Names may be duplicated
- **Required:** Enforce unique constraint on recipe.name

### 6. Test Execution & Feedback Loop
- **Required:** Run full test suite + improvement iterations

### 7. Neo4j Client Re-validation
- **Current:** Modified in previous session
- **Required:** Re-run tests for neo4j async operations

## Affected Files

- `streamlit_ui/pages/recipes.py` — Main recipe UI
- `streamlit_ui/app.py` — Sidebar layout
- `streamlit_ui/crud/` — May need RecipeManager creation
- `streamlit_ui/neo4j_async.py` — Neo4j operations (retest)
- `envelope/config/models.py` — Add unique constraint to RecipeConfig
- Tests: `streamlit_ui/tests/test_recipes.py`

## Acceptance Criteria

✅ Sidebar minimal (only essential sections)
✅ Recipe view shows all entries with expandable details
✅ Recipe edit: modify name & description
✅ Recipe entry viewer with full metadata
✅ Delete recipe with confirmation dialog
✅ Unique constraint on recipe.name (DB + model level)
✅ All tests passing (recipes + neo4j)
✅ Feedback loop executed

## Implementation Approach

**TDDD Mode:** Tests first, then implementation

1. Define test scenarios for each feature
2. Implement backend (models, CRUD, validators)
3. Update Streamlit UI components
4. Run full test suite
5. Improvement feedback loop
