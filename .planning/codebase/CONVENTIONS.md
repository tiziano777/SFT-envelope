# Coding Conventions

**Analysis Date:** 2026-04-10

## Naming Patterns

**Files:**
- Use `snake_case.py` for all Python source files
- Technique plugins: `envelope/techniques/{category}/{technique_name}.py` (e.g., `grpo.py`, `dpo.py`)
- Framework adapters: `envelope/frameworks/{scope}/{framework}_adapter.py` (e.g., `trl_adapter.py`, `verl_adapter.py`)
- Test files: `test_{module_name}.py` (always prefixed with `test_`)
- Templates: `{type}_{technique}_{framework}.{ext}.j2` (e.g., `train_grpo_trl.py.j2`)

**Classes:**
- PascalCase for all classes
- Technique plugins: `{NAME}Technique` (e.g., `GRPOTechnique`, `DPOTechnique`)
- Framework adapters: `{Name}Adapter` (e.g., `TRLAdapter`, `UnslothAdapter`)
- Pydantic models: descriptive PascalCase ending in `Config` (e.g., `EnvelopeConfig`, `PeftConfig`, `HardwareConfig`)
- Enums: PascalCase (e.g., `Stage`, `Technique`, `PeftMethod`)
- Test classes: `Test{Concept}` (e.g., `TestEnums`, `TestPeftConfig`, `TestCapabilityMatrix`)

**Functions:**
- `snake_case` for all functions and methods
- Public functions: descriptive names (e.g., `load_config`, `generate_setup`, `suggest_optimizations`)
- Private/internal functions: underscore prefix `_validate_peft_quantization`, `_render_template`, `_copy_reward_modules`
- Helper factory functions in tests: underscore prefix (e.g., `_minimal_config_dict`, `_make_config`, `_get_technique`)

**Variables:**
- `snake_case` for all variables
- Module-level constants: `UPPER_SNAKE_CASE` (e.g., `HYPERPARAMETER_DEFAULTS`, `TECHNIQUE_STAGE_MAP`, `ALL_TECHNIQUES`, `TEMPLATES_DIR`)
- Private module-level state: underscore prefix (e.g., `_state`)

**Enums:**
- Members use `UPPER_SNAKE_CASE` (e.g., `Stage.SFT`, `Technique.GRPO`, `PeftMethod.QLORA`)
- String enums use lowercase values: `"sft"`, `"grpo"`, `"qlora"`
- Integer enums use sequential integers: `Stage.SFT = 1`, `Stage.PREFERENCE = 2`, `Stage.RL = 3`

**Type aliases:**
- Use inline `X | Y` union syntax (Python 3.10+), never `Union[X, Y]`
- Example: `str | Path`, `float | None`, `dict[str, int | float | str]`

## Code Style

**Formatting:**
- Tool: `ruff format`
- Line length: 120 characters (configured in `pyproject.toml`)
- Run: `make format` or `ruff format envelope/ tests/`

**Linting:**
- Tool: `ruff check`
- Target version: Python 3.10 (`target-version = "py310"`)
- Run: `make lint` or `ruff check envelope/ tests/`
- Suppressed warnings use `# noqa: F401` for intentional unused imports (plugin discovery in `envelope/registry/__init__.py`)

**Python version features:**
- Use `from __future__ import annotations` at the top of EVERY module (enables PEP 604 `X | Y` syntax at runtime for Python 3.10)
- Use Python 3.10+ syntax: `dict[str, Any]` not `Dict[str, Any]`, `list[str]` not `List[str]`
- Use `X | None` not `Optional[X]`

## Import Organization

**Order:**
1. `from __future__ import annotations` (ALWAYS first)
2. Standard library imports (`pathlib`, `typing`, `abc`, `enum`, `sys`, `os`, etc.)
3. Third-party imports (`pydantic`, `yaml`, `click`, `rich`, `jinja2`, `pytest`)
4. Local package imports (`from envelope.config.models import ...`, `from envelope.registry import ...`)

**Style:**
- Use `from X import Y` style for specific symbols, not bare `import X` (except for `yaml`, `jinja2`, `shutil`, `os`, `re`)
- Group related imports from same package on separate lines
- Example from `envelope/generators/setup_generator.py`:
```python
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import jinja2

from envelope.config.loader import dump_config, load_config
from envelope.config.models import EnvelopeConfig
from envelope.config.validators import validate_config_or_raise
from envelope.frameworks.base import BaseFrameworkAdapter
```

**Lazy imports:**
- CLI commands (`envelope/cli.py`) use lazy imports inside function bodies to keep startup fast:
```python
@main.command()
def validate(config: str):
    from envelope.config.loader import load_config
    from envelope.config.validators import validate_config
    from envelope.hardware.auto_optimizer import suggest_optimizations
    from envelope.registry import discover_plugins
```

**Path Aliases:**
- No aliases configured. Use full relative import paths (`from envelope.config.models import ...`)

## Module Organization

**Module docstrings:**
- Every module starts with a triple-quoted docstring describing purpose
- Pattern: one-liner summary, blank line, extended description if needed
```python
"""YAML configuration loader with default merging and validation."""
```

**Section separators:**
- Use Unicode box-drawing comments to separate logical sections:
```python
# ─── Enums ───
# ─── Sub-models ───
# ─── Root Config ───
# ─── Public API ───
# ─── Diagnostic Rules ───
```

**`__all__` exports:**
- Used in `envelope/registry/__init__.py`:
```python
__all__ = ["technique_registry", "framework_registry", "discover_plugins"]
```
- Not consistently used in other modules. Follow existing pattern: add `__all__` to `__init__.py` modules.

## Plugin Architecture

**Technique plugins:**
- Inherit from `BaseTechnique` (ABC) at `envelope/techniques/base.py`
- Register via `@technique_registry.register("name")` decorator
- Implement required abstract methods: `name`, `stage`, `display_name`, `default_technique_args`, `validate_technique_args`, `required_dataset_fields`
- Override optional properties: `requires_reference_model`, `requires_reward`, `requires_teacher_model`
- Example pattern (`envelope/techniques/rl/grpo.py`):
```python
@technique_registry.register("grpo")
class GRPOTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "grpo"

    @property
    def stage(self) -> Stage:
        return Stage.RL

    def default_technique_args(self) -> dict[str, Any]:
        return {"num_generations": 16, "beta": 0.04, ...}

    def validate_technique_args(self, args: dict[str, Any]) -> list[str]:
        errors = []
        if "beta" in args and args["beta"] < 0:
            errors.append(f"GRPO beta must be >= 0, got {args['beta']}")
        return errors
```

**Framework adapters:**
- Inherit from `BaseFrameworkAdapter` (ABC) at `envelope/frameworks/base.py`
- Register via `@framework_registry.register("name")` decorator
- Implement required abstract methods: `name`, `display_name`, `template_name`, `requirements`
- Override optional methods: `template_context`, `launch_command`, `validate_config`, `extra_setup_files`

**Plugin discovery:**
- Call `discover_plugins()` from `envelope/registry/__init__.py` before accessing registries
- Discovery imports all plugin modules to trigger `@register` decorators
- Discovery is idempotent (safe to call multiple times)

## Error Handling

**Validation errors (config):**
- Pydantic `ValidationError` for schema-level validation (types, ranges, required fields)
- Custom `ConfigValidationError` (in `envelope/config/validators.py`) for cross-field validation
- Pattern: collect errors as `list[str]`, raise or return
```python
def validate_config(config: EnvelopeConfig) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_peft_quantization(config))
    errors.extend(_validate_hardware_precision(config))
    return errors

def validate_config_or_raise(config: EnvelopeConfig) -> None:
    errors = validate_config(config)
    if errors:
        raise ConfigValidationError(errors)
```

**File/runtime errors:**
- Use built-in exceptions: `FileNotFoundError`, `ValueError`, `KeyError`
- Registry raises `KeyError` for unknown keys with helpful message listing available options
- Registry raises `ValueError` for duplicate registration
- CLI catches `Exception` at top level, prints with Rich formatting, exits with `SystemExit(1)`

**Validation return pattern:**
- Functions that validate return `list[str]` of error messages
- Empty list means valid
- Each error message is a complete, actionable sentence

## Logging

**Framework:** Console output only via `rich.console.Console`
- Module-level: `console = Console()` in `envelope/cli.py`
- Rich markup for colors: `[bold blue]`, `[bold green]`, `[bold red]`, `[yellow]`, `[cyan]`, `[dim]`
- Diagnostic warnings: `print(warning.format(), file=sys.stderr, flush=True)` (no Rich in runtime diagnostics)

**Patterns:**
- CLI success: `console.print(f"[bold green]...[/]")`
- CLI error: `console.print(f"[bold red]Error:[/] {e}")`
- CLI info: `console.print(f"[bold blue]...[/]")`
- No Python `logging` module is used; all output goes through Rich or stderr

## Comments

**Module-level docstrings:** Required on every `.py` file. Use triple-quoted string.

**Inline comments:**
- Explain "why" not "what"
- Used sparingly for non-obvious logic
- Example: `# Backward compat: convert fsdp: true/false to fsdp: {enabled: true/false}`

**Block section comments:**
- Use `# ─── Section Name ───` with Unicode box-drawing characters for major sections
- Use `# ---------------------------------------------------------------------------` in test files

**`# noqa` comments:**
- Use for intentional suppression only: `import envelope.techniques.sft  # noqa: F401`

## Pydantic Model Design

**Base class:** All config models inherit from `pydantic.BaseModel`

**Field patterns:**
- Required fields: `name: str = Field(..., min_length=1, description="...")`
- Optional with default: `revision: str = "main"`
- Optional nullable: `run_id: str | None = None`
- Nested models with defaults: `peft: PeftConfig = Field(default_factory=PeftConfig)`
- Lists: `tags: list[str] = Field(default_factory=list)`
- Constrained values: `r: int = Field(16, gt=0)`, `lora_dropout: float = Field(0.05, ge=0.0, le=1.0)`

**Validators:**
- Use `@model_validator(mode="after")` for intra-model cross-field validation
- Use `@model_validator(mode="before")` with `@classmethod` for input coercion (backward compat)
- Return `self` from after-mode validators
- Technique-specific validation via `validate_technique_args()` returning `list[str]`

**Enum integration:**
- String enums (`str, Enum`) for YAML-serializable values
- Integer enums (`int, Enum`) for ordered stages
- Pydantic automatically coerces string values to enum members

## Function Design

**Size:** Functions are focused and concise, typically 10-40 lines

**Parameters:**
- Use `str | Path` for file path parameters
- Use keyword arguments with defaults for optional configuration
- Use `dict[str, Any]` for flexible config/args dicts
- Use `**_kwargs: object` for unused keyword arguments in callbacks

**Return values:**
- Validation functions return `list[str]` (empty = valid)
- Generator functions return `Path` (output directory)
- Config loaders return typed model instances (`EnvelopeConfig`)
- Diagnostic checks return `DiagnosticWarning | None`

**Docstrings:**
- Use Google-style docstrings for public functions:
```python
def generate_setup(
    config_path: str | Path,
    name: str,
    output_base: str | Path = "setups",
) -> Path:
    """Generate a self-contained setup directory from a YAML config.

    Args:
        config_path: Path to the YAML config
        name: Experiment name (used in folder name: setup_{name})
        output_base: Base directory for generated setups

    Returns:
        Path to the generated setup directory
    """
```
- Short one-liner docstrings for simple/obvious functions

## Data Structures

**Constants:**
- Module-level typed dicts: `HYPERPARAMETER_DEFAULTS: dict[str, int | float | str] = {...}`
- Module-level typed sets: `REFERENCE_FREE_TECHNIQUES = {Technique.SFT, ...}`
- Module-level mapping dicts: `TECHNIQUE_STAGE_MAP: dict[Technique, Stage] = {...}`

**Dataclasses:**
- Used for simple value types: `@dataclass class DiagnosticWarning`

**Registry pattern:**
- Generic `Registry[T]` class using `TypeVar("T")`
- Singleton instances at module level: `technique_registry = Registry("technique")`

---

*Convention analysis: 2026-04-10*
