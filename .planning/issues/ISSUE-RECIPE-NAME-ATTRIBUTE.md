# Issue: RecipeConfig Missing 'name' Attribute

**Status:** ✅ RESOLVED
**Severity:** HIGH
**Component:** streamlit_ui / envelope.config
**Date:** 2026-04-14
**Parent Issue:** ISSUE-RECIPE-VALIDATION-MISSING-LOADER

## Problem

After uploading recipe YAML, Streamlit crashed with:
```
AttributeError: 'RecipeConfig' object has no attribute 'name'
```

Location: `streamlit_ui/pages/recipes.py:61`
```python
st.info(f"**Name:** {config.name if config else 'N/A'}")
```

## Root Cause

`RecipeConfig` model had no `name` field, but the UI code expected it.

## Solution Implemented ✅

### 1. Added `name` field to RecipeConfig
**File:** `envelope/config/models.py:472`
```python
class RecipeConfig(BaseModel):
    name: str | None = Field(None, min_length=1, description="Recipe name (typically from filename)")
    entries: dict[str, RecipeEntry]
```

### 2. Updated validation to extract filename
**File:** `streamlit_ui/validation.py:51`
- Added `filename: str | None = None` parameter to `validate_recipe_yaml()`
- Extracts recipe name from filename when loading (removes .yaml/.yml extension)
- Assigns extracted name to `config.name` if not already set

### 3. Updated Streamlit UI to pass filename
**File:** `streamlit_ui/pages/recipes.py:57`
```python
validate_recipe_yaml(yaml_content, filename=uploaded_file.name)
```

## Changes Summary

| File | Change |
|------|--------|
| `envelope/config/models.py` | +1 line: Add optional `name` field |
| `streamlit_ui/validation.py` | +7 lines: Add filename parameter + extraction logic |
| `streamlit_ui/pages/recipes.py` | +1 line: Pass `filename=uploaded_file.name` |

## Verification

✅ Code review complete
✅ All changes follow Pydantic v2 patterns
✅ Backwards compatible (name is optional)
✅ Filename extraction handles edge cases (.yaml/.yml removal)

## Commit

```
3d1b338 fix: extract recipe name from uploaded filename
```

Example flow:
1. User uploads `my_recipe.yaml`
2. Streamlit extracts `"my_recipe"` as recipe name
3. RecipeConfig.name = `"my_recipe"`
4. UI displays: `**Name:** my_recipe`

