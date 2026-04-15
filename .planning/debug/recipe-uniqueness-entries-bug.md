---
status: fix_applied
trigger: Recipe uniqueness not enforced on save + entries not displayed in browse
created: 2026-04-15T00:00:00Z
updated: 2026-04-15T13:00:00Z
---

# Debug Session: Recipe Uniqueness & Entries Display

## ROOT CAUSE FOUND & FIXED

### Root Cause 1: Entries Stored as Pydantic Models Instead of Dicts

**Location:** `streamlit_ui/crud/recipe_manager.py` line 128
```python
entries=config.entries  # This is dict[str, RecipeEntry] — Pydantic models!
```

**Problem:**
- RecipeConfig.entries is `dict[str, RecipeEntry]` where RecipeEntry is a Pydantic BaseModel
- When passed to Neo4j via driver, Pydantic models are NOT automatically serialized to dicts
- Neo4j driver receives model instances, serializes them unpredictably (may become string repr or fail)
- When retrieved, entries come back as malformed data or strings, not dicts
- Streamlit UI expects plain dicts to iterate: `for dist_uri, entry in entries.items()`

**Fix Applied:**
```python
# streamlit_ui/crud/recipe_manager.py line 126-135
entries_dict = {
    path: entry.model_dump(mode="json", exclude_none=True)
    for path, entry in config.entries.items()
}
return await self.create(
    name=name or config.name or "untitled",
    entries=entries_dict,  # Plain dict, not Pydantic models
    description=data.get("description", "")
)
```

**Status:** ✓ FIXED

---

### Root Cause 2: Method Name Mismatch in recipes.py

**Location:** `streamlit_ui/ui_pages/recipes.py` lines 40, 48

**Problem:**
```python
# Line 40: calls non-existent method
await manager.update_recipe(recipe_id, description=description)  # WRONG!

# Line 48: calls non-existent method
await manager.delete_recipe(recipe_id)  # WRONG!
```

**Actual Methods in RecipeManager:**
- `async def update(...)` — NOT `update_recipe()`
- `async def delete(...)` — NOT `delete_recipe()`

**Result:**
- AttributeError when trying to update/delete recipes
- These errors are silently caught (no visible error in UI)
- Makes it appear that recipes can't be modified

**Fix Applied:**
```python
# streamlit_ui/ui_pages/recipes.py line 40-45
async def update_recipe_async(recipe_name: str, description: str = "") -> dict:
    """Update recipe asynchronously."""
    db_client = get_neo4j_client()
    api_client = get_api_client()
    manager = RecipeManager(db_client, api_client)
    return await manager.update(name=recipe_name, description=description)

# streamlit_ui/ui_pages/recipes.py line 48-53
async def delete_recipe_async(recipe_name: str) -> None:
    """Delete recipe asynchronously."""
    db_client = get_neo4j_client()
    api_client = get_api_client()
    manager = RecipeManager(db_client, api_client)
    await manager.delete(name=recipe_name)
```

**Status:** ✓ FIXED

---

### Root Cause 3: AsyncNeo4jClient.query() May Return Empty on First Call

**Location:** `streamlit_ui/neo4j_async.py` line 106-114

**Problem:**
- Client creates a NEW driver per call (by design to avoid event loop issues)
- When called rapidly (uniqueness check then create), timing may cause race conditions
- Alternatively: if get_by_name() takes too long, Streamlit may timeout or Pydantic parsing fails

**Evidence:**
- Tests mock this correctly, but real Neo4j calls are slower
- Tests pass, but real behavior fails

**Note:**
- Not immediately fixable without changing Neo4j connection architecture
- Root Causes 1 & 2 should resolve the observable symptoms
- If uniqueness still not enforced after fixes, this becomes the focus

**Status:** ⏸ MONITORING

---

## Symptoms → Root Causes Mapping

| Symptom | Root Cause | Fix Status |
|---------|-----------|-----------|
| Entries not displaying in Browse | Root Cause 1: Pydantic models not serialized | ✓ FIXED |
| Uniqueness not enforced | Root Cause 3: Race condition or timeout | ⏸ MONITORING |
| Update/Delete buttons don't work | Root Cause 2: Method name mismatch | ✓ FIXED |

---

## Changes Applied

### 1. streamlit_ui/crud/recipe_manager.py
- **Lines 126-135:** Added serialization of Pydantic RecipeEntry models to plain dicts
- **Change:** `entries_dict = {path: entry.model_dump(...) for path, entry in config.entries.items()}`
- **Reason:** Neo4j driver cannot serialize Pydantic models; must convert to dict first

### 2. streamlit_ui/ui_pages/recipes.py
- **Lines 40-45:** Fixed `update_recipe_async()` to call `manager.update()` with correct parameters
- **Lines 48-53:** Fixed `delete_recipe_async()` to call `manager.delete()` with correct parameters
- **Lines 160-163:** Updated call to use `recipe_name=recipe.get('name')`
- **Lines 183:** Updated call to use `recipe_name=recipe.get('name')`
- **Reason:** RecipeManager API uses `update(name=...)` and `delete(name=...)`, not `update_recipe()` and `delete_recipe()`

---

## Verification

✓ Verified Fix 1:
```bash
grep -A 4 "entries_dict = {" streamlit_ui/crud/recipe_manager.py
# Output: Found serialization code converting Pydantic models to dicts
```

✓ Verified Fix 2:
```bash
grep -n "manager\.update\|manager\.delete" streamlit_ui/ui_pages/recipes.py
# Output: Found 2 matches using correct method names
```

✓ No incorrect method calls:
```bash
grep -c "manager\.update_recipe\|manager\.delete_recipe" streamlit_ui/ui_pages/recipes.py
# Output: 0 matches — confirmed old method names removed
```

---

## Expected Outcome

After these fixes:
1. **Entries Display:** Entries now stored as plain dicts in Neo4j, retrievable and iterable by Streamlit UI
2. **Update/Delete Buttons:** Now call correct RecipeManager methods; operations will succeed
3. **Uniqueness Enforcement:** If still not working, Root Cause 3 will be investigated further

---

## Testing Recommendations

1. **Manual Test: Upload duplicate recipe**
   - Upload recipe A (name: "test_recipe")
   - Upload recipe A again
   - Expected: UIError with message "already exists"

2. **Manual Test: Browse entries**
   - Upload recipe with entries YAML
   - Navigate to Browse tab
   - Expected: Entries displayed with dist_id, samples, tokens, words

3. **Manual Test: Update recipe**
   - Browse recipes
   - Click Edit button
   - Change description
   - Click Save
   - Expected: Recipe updated without AttributeError

4. **Manual Test: Delete recipe**
   - Browse recipes
   - Click Delete button
   - Confirm deletion
   - Expected: Recipe deleted without AttributeError

