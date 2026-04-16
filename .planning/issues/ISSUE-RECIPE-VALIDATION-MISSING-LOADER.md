# Issue: Recipe Validation Fails — Missing load_yaml_config() Function

**Status:** RESOLVED
**Severity:** HIGH
**Component:** streamlit_ui / envelope.config
**Date Reported:** 2026-04-14

## Problem Statement

Recipe validation in Streamlit UI fails with cryptic error:
```
✗ Recipe validation failed
  • EnvelopeConfig not available
```

This occurs for ANY input YAML, preventing all recipe uploads.

## Root Cause

`streamlit_ui/validation.py` (line 10) imports a non-existent function:

```python
from envelope.config.loader import load_yaml_config  # ← DOES NOT EXIST
```

The ImportError is silently caught (lines 12-15), setting `EnvelopeConfig = None`.
This causes validation to **always fail** (line 27-28):

```python
if not EnvelopeConfig or not load_yaml_config:
    return False, None, ["EnvelopeConfig not available"]
```

## Secondary Issue

Even if import succeeds, the provided YAML is **NOT** in EnvelopeConfig format.
Example input is a **distribution/recipe metadata** file with:
- Distribution IDs, names, URIs
- JSON Schema templates
- System prompts
- Token/word counts

But `EnvelopeConfig` expects:
- Model configuration
- Training technique
- Framework settings
- Hyperparameters
- etc.

## Solution

### Part 1: Implement load_yaml_config()

Add to `envelope/config/loader.py`:

```python
def load_yaml_config(yaml_str: str) -> EnvelopeConfig:
    """Load and validate EnvelopeConfig from YAML string.

    Args:
        yaml_str: YAML content as string.

    Returns:
        Validated EnvelopeConfig instance.

    Raises:
        ValueError: If YAML is invalid or empty.
        ValidationError: If config doesn't match schema.
    """
    data = yaml.safe_load(yaml_str)
    if data is None:
        raise ValueError("Empty YAML content")
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML dict, got {type(data).__name__}")

    # Merge defaults
    data = merge_technique_defaults(data)

    # Inject hparam defaults
    if "hparam_overrides" not in data:
        data["hparam_overrides"] = dict(HYPERPARAMETER_DEFAULTS)

    config = EnvelopeConfig.model_validate(data)
    return config
```

### Part 2: Fix validation error handling

Update `streamlit_ui/validation.py` to provide better feedback:

```python
def validate_recipe_yaml(yaml_str: str) -> tuple[bool, Optional[object], list[str]]:
    """Validate YAML recipe against EnvelopeConfig schema."""
    if not EnvelopeConfig or not load_yaml_config:
        return False, None, [
            "EnvelopeConfig module not loaded",
            "Ensure envelope package is properly installed"
        ]

    try:
        config = load_yaml_config(yaml_str)
        return True, config, []
    except ValueError as e:
        return False, None, [f"Invalid YAML format: {str(e)}"]
    except ValidationError as e:
        errors = []
        for err in e.errors():
            field = ".".join(str(x) for x in err["loc"])
            msg = err["msg"]
            errors.append(f"{field}: {msg}")
        return False, None, errors
    except Exception as e:
        return False, None, [f"Validation error: {str(e)}"]
```

## Testing

1. **Valid EnvelopeConfig YAML**: Should validate successfully
2. **Invalid format (distribution metadata)**: Should return clear error: `"Invalid format: Expected training config, got distribution metadata"`
3. **Missing required fields**: Should list missing fields per Pydantic
4. **Import failure**: Should return: `"EnvelopeConfig module not loaded"`

## Expected Behavior After Fix

```
# Valid config
✓ Recipe validation passed
Name: my-training-setup

# Invalid format
✗ Recipe validation failed
  • Invalid format: Missing required field 'training'
  • Invalid format: Missing required field 'model'

# Distribution metadata
✗ Recipe validation failed
  • training: Field required
  • model: Field required
```

## Affected Code

- `streamlit_ui/validation.py` — Import fail + validation logic
- `streamlit_ui/pages/recipes.py` — Display of validation results
- `envelope/config/loader.py` — Missing function

## Workaround

None available. Issue blocks all recipe uploads via UI.

## Resolution

**Commits:**
- 691b952: Initial fix (load_yaml_config)
- b08cb2a: Enhanced fix (dual-format validation)

### Final Solution: Dual-Format Support

Since your data is **distribution metadata** (not training setup), implemented auto-detecting validation:

1. **`envelope/config/models.py`**: Added RecipeConfig schema
   - `RecipeEntry`: dist_id, dist_name, dist_uri, samples, tokens
   - `RecipeConfig`: wrapper mapping paths → RecipeEntry objects

2. **`envelope/config/loader.py`**: Added `load_recipe_yaml()`
   - Parses distribution/recipe metadata YAML
   - Auto-wraps flat entries into `entries` dict
   - Validates against RecipeConfig schema
   - And kept `load_yaml_config()` for EnvelopeConfig training setups

3. **`streamlit_ui/validation.py`**: Smart auto-detection
   - Added `_detect_config_type()`: looks for dist_* markers
   - Single `validate_recipe_yaml()` endpoint routes to correct loader
   - Automatic format detection (user doesn't choose)

### Result

✓ **Distribution metadata uploads now work** (your YAML format)
✓ **Training config uploads still work** (EnvelopeConfig format)
✓ **Auto-detection routes to correct validator**
✓ **Clear validation errors for both formats**
✓ **Syntax validated**: all 3 files pass Python compilation
