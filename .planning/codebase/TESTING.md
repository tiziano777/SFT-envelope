# Testing Patterns

**Analysis Date:** 2026-04-10

## Test Framework

**Runner:**
- pytest >= 8.0
- Config: `pyproject.toml` section `[tool.pytest.ini_options]`
- Test paths configured: `testpaths = ["tests"]`

**Coverage:**
- pytest-cov >= 5.0 (installed as dev dependency)

**Assertion Library:**
- Native pytest assertions (no third-party assertion libraries)
- `pytest.raises` for exception testing
- `pytest.mark.parametrize` used extensively

**Run Commands:**
```bash
make test                    # Run all tests (pytest tests/ -v)
pytest tests/ -v             # Direct pytest invocation
pytest tests/unit/ -v        # Unit tests only
pytest tests/integration/ -v # Integration tests only
pytest tests/ --cov=envelope # With coverage
```

## Test File Organization

**Location:**
- Separate `tests/` directory at project root (NOT co-located with source)
- Split into `tests/unit/` and `tests/integration/`

**Naming:**
- Files: `test_{module_name}.py` matching the source module being tested
- No `conftest.py` files exist (no shared fixtures across test files)

**Structure:**
```
tests/
├── unit/
│   ├── test_config_models.py       # Tests envelope/config/models.py
│   ├── test_validators.py          # Tests envelope/config/validators.py
│   ├── test_techniques.py          # Tests all technique plugins
│   ├── test_distillation_techniques.py  # Tests distillation subset
│   ├── test_reward_modeling.py     # Tests reward_modeling technique
│   ├── test_frameworks.py          # Tests framework adapters + capability matrix
│   ├── test_registry.py            # Tests envelope/registry/base.py + discover_plugins
│   ├── test_setup_generator.py     # Tests envelope/generators/setup_generator.py
│   ├── test_diagnostics.py         # Tests envelope/diagnostics/runtime.py
│   └── test_fsdp.py               # Tests FSDP across config/validators/adapters
└── integration/
    └── test_make_setup.py          # End-to-end: YAML -> load -> validate -> generate -> verify
```

## Test Structure

**Suite Organization:**
- Tests are organized in classes grouped by logical concept
- Classes are prefixed with `Test` and named after the concept being tested
- Each class tests one concern or component
- Helper functions use underscore prefix and live at module top level

**Pattern from `tests/unit/test_config_models.py`:**
```python
"""Unit tests for envelope/config/models.py -- Pydantic v2 config models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from envelope.config.models import (
    EnvelopeConfig,
    ExperimentConfig,
    # ... other imports
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_config_dict(**overrides) -> dict:
    """Return the smallest dict that can produce a valid EnvelopeConfig."""
    base = {
        "experiment": {"name": "test-exp"},
        "model": {"name_or_path": "meta-llama/Llama-3.1-8B"},
        "dataset": {"train_uri": "tatsu-lab/alpaca"},
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Section Name
# ---------------------------------------------------------------------------


class TestExperimentConfig:
    def test_minimal(self):
        cfg = ExperimentConfig(name="exp1")
        assert cfg.name == "exp1"
        assert cfg.seed == 42

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ExperimentConfig(name="")
```

**Test naming convention:**
- Method names: `test_{what_is_being_tested}` in snake_case
- Descriptive names: `test_qlora_auto_sets_nf4`, `test_bf16_on_v100_errors`, `test_default_args_valid`
- Negative tests: `test_{condition}_raises`, `test_{condition}_errors`
- Positive tests: `test_{condition}_ok`, `test_{condition}_returns_none`

**Section separators in test files:**
```python
# ---------------------------------------------------------------------------
# Section Name
# ---------------------------------------------------------------------------
```

## Parametrize Patterns

**Heavy use of `pytest.mark.parametrize` for exhaustive coverage:**

```python
# Testing all enum values
@pytest.mark.parametrize(
    "member,value",
    [
        (Technique.SFT, "sft"),
        (Technique.DPO, "dpo"),
        (Technique.GRPO, "grpo"),
        # ... all members
    ],
)
def test_technique_values(self, member, value):
    assert member.value == value
```

```python
# Testing all technique plugins with expected metadata
ALL_TECHNIQUES = [
    ("sft", Stage.SFT, "Supervised Fine-Tuning"),
    ("dpo", Stage.PREFERENCE, "Direct Preference Optimization"),
    ("grpo", Stage.RL, "Group Relative Policy Optimization"),
    # ... all techniques
]

class TestTechniqueMetadata:
    @pytest.mark.parametrize("name,expected_stage,expected_display", ALL_TECHNIQUES)
    def test_stage(self, name, expected_stage, expected_display):
        t = _get_technique(name)
        assert t.stage == expected_stage
```

```python
# Parametrized integration tests (class-level)
@pytest.mark.parametrize(
    "config_path,setup_name,expected_technique,expected_framework",
    [
        (GRPO_CONFIG, "int-grpo", "grpo", "trl"),
        (SFT_CONFIG, "int-sft", "sft", "trl"),
    ],
    ids=["grpo-qlora-qwen", "sft-lora-llama3"],
)
class TestEndToEndSetupGeneration:
    # ... all tests get parametrized values
```

## Fixtures

**Fixture patterns used:**

1. **`tmp_path` fixture** (built-in pytest): Used for file generation tests
```python
@pytest.fixture()
def setup_dir(self, tmp_path: Path) -> Path:
    return generate_setup(
        config_path=GRPO_CONFIG,
        name="grpo-test",
        output_base=tmp_path,
    )
```

2. **`autouse` fixture** for state reset:
```python
@pytest.fixture(autouse=True)
def _reset_diagnostic_state():
    """Reset diagnostic state before each test for isolation."""
    reset_state()
    yield
    reset_state()
```

3. **Module-level setup** via `discover_plugins()`:
```python
# At module level, before test classes
discover_plugins()
```

**No conftest.py:** Each test file is self-contained with its own helpers and fixtures.

## Helper Factory Functions

**Every test module with config tests defines a `_make_config` or `_minimal_config_dict` helper:**

```python
def _make_config(**overrides) -> EnvelopeConfig:
    """Build a minimal valid EnvelopeConfig with optional overrides."""
    base = {
        "experiment": {"name": "val-test"},
        "model": {"name_or_path": "meta-llama/Llama-3.1-8B"},
        "dataset": {"train_uri": "tatsu-lab/alpaca"},
    }
    base.update(overrides)
    return EnvelopeConfig.model_validate(base)
```

**Plugin access helper:**
```python
def _get_technique(name: str) -> BaseTechnique:
    cls = technique_registry.get(name)
    return cls()

def _get_adapter(name: str) -> BaseFrameworkAdapter:
    cls = framework_registry.get(name)
    return cls()
```

**These are duplicated across test files** (no shared conftest.py). When writing new tests, copy the pattern from the closest existing test file.

## Mocking

**No mocking framework used.** Tests use:

1. **Real objects:** All tests construct real Pydantic models and real plugin instances
2. **`tmp_path`:** For filesystem tests (setup generation), pytest's built-in `tmp_path` fixture provides isolated temp directories
3. **Module-level state reset:** `reset_state()` function for diagnostics tests
4. **`capsys`:** pytest built-in for capturing stdout/stderr
```python
def test_prints_to_stderr(self, capsys):
    """Warnings should be printed to stderr."""
    run_diagnostics(step=1, metrics={"loss": 1.0})
    run_diagnostics(step=2, metrics={"loss": 100.0})
    captured = capsys.readouterr()
    assert "[ENVELOPE DIAGNOSTIC]" in captured.err
```

**What to Mock:** Nothing currently. The codebase has no external API calls or database connections in core logic.

**What NOT to Mock:**
- Pydantic model construction (always use real models)
- Plugin registry lookup (always call `discover_plugins()` then use real registry)
- File generation (use `tmp_path` for isolated filesystem operations)

## Test Data and Fixtures

**Config data:**
- Tests use inline dicts passed to `_make_config()` or `_minimal_config_dict()`
- Override only the fields relevant to the test
- Example configs from `configs/examples/` are used in integration tests:
```python
CONFIGS_DIR = Path(__file__).resolve().parents[2] / "configs" / "examples"
GRPO_CONFIG = CONFIGS_DIR / "grpo_qlora_qwen.yaml"
SFT_CONFIG = CONFIGS_DIR / "sft_lora_llama3.yaml"
```

**No fixture files or factory libraries.** All test data is constructed inline.

## Coverage

**Requirements:** None formally enforced. Coverage tool (pytest-cov) is installed but no threshold is configured.

**View Coverage:**
```bash
pytest tests/ --cov=envelope --cov-report=html
pytest tests/ --cov=envelope --cov-report=term-missing
```

## Test Types

**Unit Tests (`tests/unit/`):**
- Test individual models, validators, techniques, frameworks, registry, diagnostics
- No filesystem I/O except `test_setup_generator.py` (uses `tmp_path`)
- Fast execution, no external dependencies
- Comprehensive coverage: every enum value, every technique plugin, every framework adapter
- Validation tests: both valid and invalid inputs, boundary conditions

**Integration Tests (`tests/integration/`):**
- End-to-end pipeline: YAML file -> `load_config` -> `validate_config` -> `generate_setup` -> verify output
- Uses real YAML config files from `configs/examples/`
- Checks generated file existence, content correctness, executable permissions
- Parametrized across multiple config files (GRPO + SFT)

**E2E Tests:**
- Not implemented separately. The integration tests in `tests/integration/test_make_setup.py` serve as the E2E tests.

## Common Assertion Patterns

**Default values:**
```python
def test_defaults(self):
    cfg = PeftConfig()
    assert cfg.method == PeftMethod.NONE
    assert cfg.r == 16
    assert cfg.use_dora is False
```

**Validation error testing:**
```python
def test_empty_name_rejected(self):
    with pytest.raises(ValidationError):
        ExperimentConfig(name="")
```

**Error list assertion (custom validators):**
```python
def test_rl_without_reward_errors(self):
    config = _make_config(training={"technique": "grpo"})
    errors = validate_config(config)
    assert any("reward" in e.lower() for e in errors)
```

**Filtering errors by keyword:**
```python
def test_no_peft_with_gptq_ok(self):
    config = _make_config(...)
    errors = validate_config(config)
    peft_quant_errors = [e for e in errors if "quantization" in e.lower() and "peft" in e.lower()]
    assert len(peft_quant_errors) == 0
```

**Generated file content checks:**
```python
def test_train_py_mentions_model(self, setup_dir: Path):
    content = (setup_dir / "train.py").read_text()
    assert "Qwen/Qwen2.5-7B-Instruct" in content

def test_run_sh_executable(self, setup_dir):
    import os
    assert os.access(setup_dir / "run.sh", os.X_OK)
```

**Exception matching:**
```python
def test_check_or_raise_invalid(self):
    with pytest.raises(ValueError, match="does not support"):
        check_or_raise("dapo", "trl")
```

## Writing New Tests

**For a new technique plugin:**
1. Add parametrize entries to `ALL_TECHNIQUES` list in `tests/unit/test_techniques.py`
2. Add to `REWARD_REQUIRED` or `REFERENCE_REQUIRED` sets if applicable
3. Add invalid arg tests to `TestValidateTechniqueArgsInvalid`
4. If distillation, also add to `tests/unit/test_distillation_techniques.py`

**For a new framework adapter:**
1. Add to `ALL_FRAMEWORKS` list in `tests/unit/test_frameworks.py`
2. Add template_name, requirements, validate_config, and launch_command tests
3. Add capability matrix entries and test in `TestCapabilityMatrix`

**For a new config model:**
1. Add to `tests/unit/test_config_models.py`
2. Test defaults, required fields, validation constraints
3. Test integration with `EnvelopeConfig` root model

**For a new validator:**
1. Add to `tests/unit/test_validators.py`
2. Test both error and no-error cases
3. Use `_make_config()` helper with targeted overrides

**For new cross-cutting features (like FSDP):**
- Create a dedicated test file (e.g., `tests/unit/test_fsdp.py`) that tests across layers: config model, validators, adapters, capability matrix, auto-optimizer

---

*Testing analysis: 2026-04-10*
