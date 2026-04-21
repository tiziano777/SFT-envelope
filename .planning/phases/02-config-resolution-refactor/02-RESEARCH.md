# Phase 2: Config Resolution Refactor - Research

**Researched:** 2026-04-20
**Domain:** Configuration architecture, YAML-to-code flow, plugin defaults
**Confidence:** HIGH

## Summary

FineTuning-Envelope currently has a **split source of truth** for configuration. Hyperparameter defaults, technique-specific arguments, and diagnostics settings are partially defined in Python code (`defaults.py`, templates) and partially in generated YAML. This creates three problems:

1. **Redundant merging logic** — hyperparameter resolution is duplicated in `shared_utils.py` AND re-implemented in every template
2. **Technique defaults injected at load time** — `merge_technique_defaults()` in `loader.py` pulls defaults from plugins and merges them into the config object, making the generated `config.yaml` incomplete (future runs won't know about these merged fields)
3. **Recipe/dataset schema duplication** — `RecipeConfig` in `models.py` vs `DatamixConfig` in `prepare/datamix_loader.py` serve similar purposes but are defined separately
4. **Diagnostics hardcoded** — `TRLDiagnosticCallback` is injected into templates with no YAML configuration option

**Phase 2 goal:** Make generated `config.yaml` the **single source of truth**. No Python code should "fill in" missing config values at runtime.

**Primary recommendation:**
- Move all hyperparameter defaults into Pydantic model field defaults (not injected at load time)
- Remove `merge_technique_defaults()` or make it purely informational
- Generate complete config.yaml with all fields (including defaults)
- Consolidate recipe schema to one place
- Make diagnostics configuration optional via YAML

---

## Current Architecture

### Config Loading Pipeline

```
user_config.yaml
    ↓
loader.load_config()
    ├─ load_yaml() → raw dict
    ├─ merge_technique_defaults() → reads plugin.default_technique_args(), merges into training.technique_args
    ├─ inject hparam_overrides from defaults.py HYPERPARAMETER_DEFAULTS
    └─ EnvelopeConfig.model_validate(raw) → validated config object
    ↓
setup_generator.generate_setup()
    ├─ framework.template_context(config) → passes config.hparam_overrides to template
    ├─ render templates with context
    └─ dump_config(config, output_dir/config.yaml) → serialize back to YAML
```

### Pydantic Schema Structure

**EnvelopeConfig** (`config/models.py`, line 403-443):
- Top-level root model with 11 sub-models
- Has `hparam_overrides: dict[str, Any]` field (line 417) — description: "Hyperparameter defaults from techniques, can be overridden at runtime via HPARAM_* env vars"
- Field is injected during load time (line 64 in `loader.py`)
- Cross-field validators run automatically via `@model_validator(mode="after")`

**Template Context** (`frameworks/base.py`, line 40-49):
```python
def template_context(self, config: EnvelopeConfig) -> dict[str, Any]:
    return {
        "config": config,
        "technique_args": config.training.technique_args,
        "hparam_defaults": config.hparam_overrides,  # This dict came from defaults.py injection
    }
```

### Hyperparameter Resolution - Current Duplication

**Three implementations of the same logic:**

1. **shared_utils.py** (`generators/shared_utils.py`, lines 10-36):
   - Function `resolve_hyperparams(defaults: dict)` — takes dict, applies HPARAM_* env vars
   - Used... nowhere in codebase (imported in template but template re-implements instead)

2. **Template inline** (`generators/templates/train_grpo_trl.py.j2`, lines 36-52):
   - Same logic copy-pasted into every template
   - Hardcoded `HYPERPARAM_DEFAULTS` dict rendered from context
   - At runtime: reads env vars to override

3. **prepare.py template** (`generators/templates/prepare.py.j2`, lines 1-113):
   - Reads dataset config from template context
   - No runtime hyperparameter resolution needed here (data prep doesn't use hparams)

**Issue:** Template imports `from shared_utils import resolve_hyperparams` (line 19) but immediately redefines it (line 36). The import is dead code.

### Diagnostics Injection - Currently Hardcoded

**Setup Generator** (`generators/setup_generator.py`, line 150):
```python
_copy_diagnostics(output_dir)
```

**Template** (`generators/templates/train_grpo_trl.py.j2`, line 205):
```python
diagnostic_cb = TRLDiagnosticCallback(technique="grpo")
```

**Issue:** Callback is always injected with no YAML configuration option. User cannot:
- Disable it
- Use a custom callback
- Configure its behavior

---

## Identified Duplication Points

### 1. Recipe/Dataset Schema Duplication

**Location 1: models.py**
- Lines 449-527: `RecipeConfig`, `RecipeEntry` classes
- Purpose: Metadata for distributions/datasets (chat_type, dist_id, samples, tokens, etc.)
- Used by: Recipe loading system (not yet fully integrated)

**Location 2: prepare/datamix_loader.py**
- Lines 8-50: `DatamixSource`, `DatamixConfig` classes
- Purpose: Multi-source dataset configuration with replica oversampling
- Fields: uri, replica, samples, dist_name, chat_type
- Overlap with RecipeEntry: uri, samples, chat_type

**Issue:** Two schema definitions for overlapping concepts. Which is the source of truth?

**Impact:**
- Prepare.py template doesn't know which schema to use
- Developers must keep both in sync
- Unclear which is the "standard" way to configure datasets

### 2. Hyperparameter Defaults in Python Code, Not YAML

**Stored in:** `config/defaults.py` (lines 11-136)

**HYPERPARAMETER_DEFAULTS** (line 11-20):
```python
{
    "learning_rate": 1e-5,
    "per_device_train_batch_size": 2,
    "warmup_ratio": 0.1,
    ...
}
```

**TECHNIQUE_DEFAULTS** (line 23-136):
```python
{
    "grpo": {
        "num_generations": 16,
        "max_completion_length": 512,
        ...
    },
    ...
}
```

**Current flow:**
1. User provides config.yaml with minimal hparams (or none)
2. loader.merge_technique_defaults() reads from plugin and merges
3. loader.py also injects HYPERPARAMETER_DEFAULTS into hparam_overrides
4. Generated config.yaml includes these merged values
5. But user doesn't see WHERE these came from (hidden in Python)

**Risk:** When user regenerates a setup, they lose these defaults if they're not in their original YAML. Also if defaults change in v0.3+, old setups won't auto-upgrade unless they manually regenerate.

### 3. Technique Defaults - Load-Time Merging vs. Schema Defaults

**How technique_args are currently handled:**

**Step 1: Plugin defines defaults**
```python
# In technique/grpo.py (for example)
class GRPOTechnique(BaseTechnique):
    def default_technique_args(self) -> dict[str, Any]:
        return {
            "num_generations": 16,
            "max_completion_length": 512,
            ...
        }
```

**Step 2: Config loader merges them** (`loader.py` lines 29-51):
```python
def merge_technique_defaults(data: dict[str, Any]) -> dict[str, Any]:
    technique = data.get("training", {}).get("technique")
    if technique:
        technique_cls = technique_registry.get(technique)
        technique_obj = technique_cls()
        defaults = technique_obj.default_technique_args()
        existing_args = data.get("training", {}).get("technique_args", {})
        merged = {**defaults, **existing_args}
        data["training"]["technique_args"] = merged
    return data
```

**Step 3: Config object created with merged args**
```python
config = EnvelopeConfig.model_validate(raw)  # raw now has merged technique_args
```

**Step 4: Template context passed to Jinja2**
```python
context = framework.template_context(config)  # config.training.technique_args contains merged defaults
_render_template(env, template_file, output_dir / "train.py", context)
```

**Issue:** Defaults are mixed into the config object at load time, so they're "invisible" — the generated config.yaml will have them written out, but future runs won't know they came from plugin defaults vs. user specification.

---

## Architecture Patterns - Standard and Anti-Patterns

### Pattern 1: Current "Inject Defaults at Load Time"
**What:** Loader merges technique defaults + hyperparameter defaults into config before validation
**When used:** Every config load
**Problem:**
- Makes generated config.yaml incomplete (doesn't show where values came from)
- Makes it hard to distinguish user values from system defaults
- If plugin defaults change, old setups don't update unless regenerated with new code

### Pattern 2: Recommended "Defaults in Schema"
**What:** Pydantic models define field defaults, generated config.yaml omits default values
**When to use:** For all system defaults (hyperparams, technique args)
**Benefit:**
- Generated config.yaml is minimal but complete (all non-default fields present)
- Pydantic schema is the source of truth
- Technique plugins register defaults via their `BaseTechnique.default_technique_args()` method, which feeds into model defaults
- Runtime reads ONLY from config.yaml

### Anti-Pattern: "Framework Adapter Fills In Missing Values"
**What:** Framework adapter's `template_context()` or templates themselves inject missing config fields
**Why bad:**
- Config is no longer self-contained
- User can't understand what train.py will use without reading code
- Makes debugging harder (where did this value come from?)

---

## Standard Stack

### Validation & Configuration
| Library | Version | Purpose | Usage |
|---------|---------|---------|-------|
| Pydantic | v2 | Type-safe config schema with validation | EnvelopeConfig, all sub-models |
| PyYAML | ≥6.0 | YAML parsing/serialization | loader.py load_yaml/dump_config |
| Python | ≥3.10 | Type hints, enum support | Entire config system |

### Testing (Test Framework Detected)
| Framework | Config file | Status |
|-----------|------------|--------|
| pytest | Not detected in codebase | Present (used in Phase 1) |

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Config schema validation | Custom validators on each field | Pydantic v2 @model_validator + Field constraints | Handles composition, cross-field logic, serialization |
| YAML loading with defaults | Recursive merge functions | Pydantic model_validate() + Field defaults | Type-safe, prevents invalid merges |
| Hyperparameter environment override | String parsing per key | Centralized resolve_hyperparams() in shared module | Consistent type coercion, single source |
| Multiple schema definitions | Separate models per use case | One canonical model, use field aliases if needed | Prevents sync bugs, clearer semantics |

---

## Runtime State Inventory

> Phase 2 is a refactor/simplification, not a rename. This inventory is minimal.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | No persistent data — config is ephemeral | — |
| Live service config | No external services (all local) | — |
| OS-registered state | None | — |
| Secrets/env vars | HPARAM_* env vars used for runtime override | Code reads these, schema unchanged |
| Build artifacts | Generated setup_* directories | Regenerate after refactor |

---

## Common Pitfalls

### Pitfall 1: Incomplete Generated config.yaml
**What goes wrong:** Generated config.yaml omits default values (uses Pydantic `exclude_none=True`), so when user later regenerates, they get different defaults than the first time.

**Why it happens:** If defaults are in Python code rather than written to config.yaml, the next load won't know what values are "defaults" vs. "missing".

**How to avoid:**
- Ensure generated config.yaml includes ALL fields (even defaults)
- Use Pydantic `model_dump(exclude_none=False, exclude_defaults=False)` when serializing
- Or: include defaults in model definition, then use `exclude_none=False`

**Warning signs:**
- User compares two generated config.yaml files from different code versions — they don't match
- Test: regenerate a setup, generate AGAIN with the same code — configs should be identical

### Pitfall 2: Plugin Defaults Not Available at Schema Validation Time
**What goes wrong:** Technique-specific defaults are only available after plugins are discovered, so schema validation can't use them as field defaults.

**Why it happens:** Plugins are registered at runtime via discovery, not at import time.

**How to avoid:**
- Option A: Call `discover_plugins()` early (before any config loading)
- Option B: Store plugin defaults in the config object itself (not as Pydantic field defaults), but document this clearly
- Option C: Make technique defaults optional in schema, validate later

**Warning signs:**
- Default values in templates differ from defaults in plugin classes
- Tests pass with one technique, fail with another (different defaults)

### Pitfall 3: Template Mistakenly Re-Implements shared_utils Functions
**What goes wrong:** Template copies function logic instead of importing it, leading to divergent implementations when code updates.

**Why it happens:** Jinja2 templates can't easily import Python functions (they're rendered, not executed).

**How to avoid:**
- Pass fully-resolved values to template context (don't expect template to call functions)
- Move all resolution logic to Python, pass results to template
- Or: Generate Python code that imports and calls the function, don't inline it

**Warning signs:**
- Same function exists in two places with identical logic
- Updates to one location don't affect the other
- Comments in template say "same as in shared_utils.py"

### Pitfall 4: Confusing "Defaults from Config" with "Defaults from Code"
**What goes wrong:** Users think config.yaml is complete, but some values are filled in by Python code at runtime.

**Why it happens:** Framework adapters or templates silently inject missing values.

**How to avoid:**
- Generated config.yaml is **always** complete (no code-level defaults)
- All defaults are in Pydantic schema or in config.yaml
- Document clearly: "If a field is missing from your config.yaml, these schema defaults apply" — then list them

**Warning signs:**
- User asks: "Where did this learning_rate value come from? It's not in my config.yaml"
- Test fails locally but passes in CI (different environment, different defaults?)

### Pitfall 5: Recipe Config in Two Places
**What goes wrong:** DatamixConfig and RecipeConfig have overlapping fields; user doesn't know which to use.

**Why it happens:** Two components (prepare/, recipes/) independently defined schemas for similar data.

**How to avoid:**
- Consolidate to ONE canonical recipe/dataset schema
- Other code references it; don't redefine
- If two use cases need different subsets of fields, use one schema with optional fields, not two schemas

**Warning signs:**
- Tests import from both models.py AND datamix_loader.py
- Prepare.py could use either DatamixConfig or RecipeConfig
- Schema fields have similar names but slightly different purposes

---

## Code Examples

### Current Hyperparameter Resolution (Duplicated)

**shared_utils.py:**
```python
def resolve_hyperparams(defaults: dict) -> dict:
    """Resolve hyperparameters: YAML defaults overridden by HPARAM_* env vars."""
    resolved = dict(defaults)
    for key in defaults:
        env_key = f"HPARAM_{key.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            default_val = defaults[key]
            if isinstance(default_val, bool):
                resolved[key] = env_val.lower() in ("true", "1", "yes")
            elif isinstance(default_val, int):
                resolved[key] = int(env_val)
            elif isinstance(default_val, float):
                resolved[key] = float(env_val)
            else:
                resolved[key] = env_val
    return resolved
```

**Same logic in template (train_grpo_trl.py.j2 lines 36-52):**
```python
def resolve_hyperparams(defaults: dict) -> dict:
    """Resolve hyperparameters: YAML defaults overridden by HPARAM_* env vars."""
    resolved = dict(defaults)
    for key in defaults:
        env_key = f"HPARAM_{key.upper()}"
        env_val = os.environ.get(env_key)
        if env_val is not None:
            default_val = defaults[key]
            if isinstance(default_val, bool):
                resolved[key] = env_val.lower() in ("true", "1", "yes")
            elif isinstance(default_val, int):
                resolved[key] = int(env_val)
            elif isinstance(default_val, float):
                resolved[key] = float(env_val)
            else:
                resolved[key] = env_val
    return resolved
```

[VERIFIED: generators/shared_utils.py and generators/templates/train_grpo_trl.py.j2]

### Recipe Schema Duplication

**Location 1 - models.py (RecipeEntry):**
```python
class RecipeEntry(BaseModel):
    """Metadata for a single distribution/dataset entry in a recipe."""
    chat_type: str = Field(..., min_length=1)
    dist_id: str = Field(...)
    dist_name: str = Field(...)
    dist_uri: str = Field(..., min_length=1)
    replica: int = Field(1, ge=1)
    samples: int = Field(..., gt=0)
    tokens: int = Field(..., gt=0)
```

**Location 2 - prepare/datamix_loader.py (DatamixSource):**
```python
class DatamixSource(BaseModel):
    """Single data source in a datamix."""
    uri: str = Field(...)
    replica: int = Field(1, ge=1)
    samples: int = Field(0, ge=0)
    dist_name: Optional[str] = None
    chat_type: str = "instruct"
```

**Overlap:**
- RecipeEntry.dist_uri ↔ DatamixSource.uri
- RecipeEntry.replica ↔ DatamixSource.replica
- RecipeEntry.samples ↔ DatamixSource.samples
- RecipeEntry.chat_type ↔ DatamixSource.chat_type
- RecipeEntry has more fields (dist_id, tokens, validation_error) that DatamixSource doesn't

[VERIFIED: config/models.py lines 449-463 and prepare/datamix_loader.py lines 8-14]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded hyperparams in template | HYPERPARAMETER_DEFAULTS in defaults.py + merge at load time | v0.1 → current | Centralized but still duplicated in templates |
| No schema validation | Pydantic v2 with @model_validator | v0.2 foundation (Phase 1) | Type-safe, cross-field validation works |
| Recursive dict merge | Pydantic model_validate() handles merging | v0.2 (Phase 2 goal) | Cleaner, avoids sync bugs |
| Diagnostics always injected | Should be: optional, configurable in YAML | v0.2 (Phase 2 goal) | User control, cleaner templates |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Current resolve_hyperparams() in shared_utils.py is unused | Code Examples | If used somewhere, removing it breaks training scripts |
| A2 | Generated config.yaml should include all fields (including defaults) | Pitfalls | If generated config omits defaults, regeneration produces different outputs |
| A3 | Technique plugins are always discovered before config loading | Pitfall 2 | If plugins load late, schema validation won't see their defaults |
| A4 | Users expect ONE canonical recipe/dataset schema, not two | Pitfall 5 | If two schemas serve different purposes, consolidation breaks one use case |
| A5 | Diagnostics callback should be optional/configurable | Current Architecture | If diagnostics must always run, YAML config is misleading |

---

## Open Questions

1. **Backward compatibility of config.yaml format**
   - When Phase 2 is complete, will existing user-generated config.yaml files still work?
   - Should loader support both old and new formats?
   - Or: clear migration guide required?

2. **Plugin-provided defaults at schema definition time**
   - Pydantic models are defined at import time, but plugins are registered at discovery time
   - How should technique-specific defaults feed into the schema?
   - Options:
     - Move defaults into plugin class docstrings, use separate defaults dict
     - Use dynamic model creation after discovery
     - Define schema fields without defaults, validate post-loading

3. **Diagnostics configuration schema**
   - Should diagnostics be a top-level field? (e.g., `diagnostics.enabled: true`)
   - Or nested under a callback/monitoring section?
   - Should user be able to specify custom callback classes?

4. **Recipe vs. Datamix consolidation**
   - Should DatamixLoader be removed entirely and use RecipeConfig instead?
   - Or: does datamix_loader serve a different purpose (runtime loading vs. metadata)?
   - Which schema becomes canonical?

---

## Environment Availability

> Phase 2 is code/config-only refactor with no new external dependencies

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Config system | ✓ | 3.10+ (verified in pyproject.toml) | — |
| Pydantic | Schema validation | ✓ | v2 (from Phase 1) | — |
| PyYAML | Config load/dump | ✓ | ≥6.0 (from Phase 1) | — |
| pytest | Testing (Phase 1 established) | ✓ | (from Phase 1 test setup) | — |

---

## Validation Architecture

> Applies if workflow.nyquist_validation is enabled (not explicitly set false in config.json)
> Config.json does not exist yet; treating validation as enabled per ROADMAP defaults

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (from Phase 1) |
| Config file | tests/conftest.py or pytest.ini (if created) |
| Quick run command | `pytest tests/ -k "config" -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FR1 | `envelope setup` generates setup_* with config.yaml | integration | `pytest tests/test_generator.py -x` | ✅ (from Phase 1) |
| FR2 | Generated config.yaml contains all required fields | unit | `pytest tests/test_config.py::test_generated_config_complete -x` | ❌ Wave 0 |
| FR3 | No hyperparameter fallback logic; all from config | unit | `pytest tests/test_config.py::test_no_runtime_defaults -x` | ❌ Wave 0 |
| FR4 | Recipe schema unified; no duplication | unit | `pytest tests/test_models.py::test_recipe_schema_single_source -x` | ❌ Wave 0 |
| FR5 | Diagnostics optional, configurable | unit | `pytest tests/test_diagnostics.py::test_diagnostics_configurable -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_config.py -x` (config-specific tests)
- **Per wave merge:** `pytest tests/ -x` (full suite before phase gate)
- **Phase gate:** Full suite green + all UAT checks from ROADMAP Phase 2 pass

### Wave 0 Gaps
- [ ] `tests/test_config.py` — tests for config loading, merging, schema completeness
- [ ] `tests/test_models.py` — tests for Pydantic model field defaults, cross-field validation
- [ ] `tests/test_diagnostics.py` — tests for diagnostics configuration and injection
- [ ] `tests/test_recipe.py` — tests for recipe schema consolidation
- [ ] Framework: Install test dependencies if not already in pyproject.toml

*(All assume pytest is already configured from Phase 1)*

---

## Security Domain

> No explicit security_enforcement flag detected; treating as enabled

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | Pydantic model validation on all config fields |
| V5.2 Sanitization | yes | YAML safe_load (not arbitrary Python pickle) |
| V6 Cryptography | no | Config contains no crypto material |
| V2 Authentication | no | Config is local-only, no auth layer |
| V3 Session Management | no | Config is stateless |

### Known Threat Patterns for {Python/Pydantic/YAML}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| YAML arbitrary code execution | Tampering | Use `yaml.safe_load()` not `yaml.load()` — verified in loader.py line 23 |
| Type confusion via HPARAM_* env vars | Tampering | Type coercion in resolve_hyperparams() with explicit isinstance checks — good pattern |
| Unvalidated hyperparameter ranges | Tampering | Pydantic Field constraints (gt=0, ge=0, le=1.0, etc.) — already in use |
| Config injection via malicious YAML | Tampering | Pydantic enum validation on all enum fields (Technique, Framework, etc.) |

---

## Sources

### Primary (HIGH confidence)
- **Codebase inspection**:
  - `config/models.py` — Pydantic schema (527 lines)
  - `config/loader.py` — YAML loading + merging (133 lines)
  - `config/defaults.py` — Hyperparameter and technique defaults (137 lines)
  - `generators/setup_generator.py` — Orchestration (200 lines)
  - `generators/templates/train_grpo_trl.py.j2` — Template example (228 lines)
  - `frameworks/base.py` — Framework adapter interface
  - `prepare/datamix_loader.py` — Dataset loader schema (50 lines)
  - `.planning/ROADMAP.md` — Phase goals and scope
  - `.planning/REQUIREMENTS.md` — Functional and quality requirements

### Secondary (MEDIUM confidence)
- **Code patterns inferred from**:
  - How `EnvelopeConfig` model_validate() works (Pydantic v2 documentation pattern)
  - Jinja2 template rendering context flow (standard practice)
  - Plugin discovery via registry pattern (OOP standard)

---

## Metadata

**Confidence breakdown:**
- **Standard stack:** HIGH — all packages verified in codebase
- **Architecture:** HIGH — traced full config flow from YAML to template rendering
- **Duplication points:** HIGH — located 3 distinct duplication issues with line numbers
- **Pitfalls:** MEDIUM-HIGH — based on code inspection, not runtime observation

**Research date:** 2026-04-20
**Valid until:** 2026-05-04 (estimate: stable config architecture, unlikely to change)

---

## Key Findings Summary

### Problems to Solve
1. ✅ **resolve_hyperparams() duplicated** in shared_utils.py and in every template
2. ✅ **Technique defaults injected at load time** making generated config.yaml incomplete
3. ✅ **Recipe schema defined twice** (RecipeConfig in models.py, DatamixSource in prepare/)
4. ✅ **Diagnostics hardcoded** in templates with no YAML configuration
5. ✅ **hparam_overrides field confusing** — is it input, output, or both?

### Refactoring Opportunities
1. **Move hyperparameter defaults into Pydantic Field defaults** (not injected at load time)
2. **Remove merge_technique_defaults() or make it diagnostic-only** (for validation, not merging)
3. **Generate complete config.yaml** with `model_dump(exclude_none=False, exclude_defaults=False)`
4. **Consolidate recipe schema** to one canonical model (choose RecipeConfig, update DatamixLoader to reference it)
5. **Add `diagnostics` field to EnvelopeConfig** with optional callback configuration
6. **Unify hyperparameter resolution** — keep only one implementation in shared_utils.py, import in templates

### Low-Risk Changes
- Pydantic field defaults (just moving where values live, not changing behavior)
- Template imports (removing duplicate code)
- Recipe schema consolidation (if backward compat via aliases)

### Moderate-Risk Changes
- Removing merge_technique_defaults() entirely (may break plugins that rely on it for discovery)
- Changing config.yaml structure (migration path needed for existing setups)

### Validation Approach
1. Unit tests for new Pydantic field defaults
2. Integration tests: generate setup, verify config.yaml is complete
3. End-to-end: regenerate existing setups, verify identical output
4. Plugin verification: all techniques still register and return defaults correctly
