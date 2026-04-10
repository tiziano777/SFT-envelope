# Architecture

**Analysis Date:** 2026-04-10

## Pattern Overview

**Overall:** Plugin-based code generation system (Config-Driven + Strategy Pattern)

**Key Characteristics:**
- YAML config is loaded, validated, and merged with technique defaults into a single `EnvelopeConfig` Pydantic model
- Training techniques and framework adapters are registered as plugins via decorator-based registries
- Jinja2 templates are rendered into self-contained `setup_*` directories containing `train.py`, `run.sh`, `prepare.py`, `requirements.txt`, and frozen `config.yaml`
- Generated setups are immutable after creation; runtime overrides happen via `HPARAM_*` env vars
- Two registries (technique, framework) combine to form a 2D compatibility matrix that gates valid combinations

## Layers

**CLI Layer:**
- Purpose: User-facing command interface (Click-based)
- Location: `envelope/cli.py`
- Contains: Click commands (`setup`, `validate`, `techniques`, `frameworks`, `compatible`)
- Depends on: Config layer, Registry layer, Generator layer, Hardware layer
- Used by: End users via `envelope` CLI or `python -m envelope.cli`

**Config Layer:**
- Purpose: Schema definition, YAML loading, default merging, cross-field validation
- Location: `envelope/config/`
- Contains: Pydantic v2 models (`models.py`), centralized defaults (`defaults.py`), YAML loader (`loader.py`), cross-field validators (`validators.py`)
- Depends on: Registry (for technique default discovery)
- Used by: All other layers -- `EnvelopeConfig` is the universal data structure

**Registry Layer:**
- Purpose: Plugin discovery and lookup for techniques and frameworks
- Location: `envelope/registry/`
- Contains: Generic `Registry` class (`base.py`), singleton instances and `discover_plugins()` (`__init__.py`)
- Depends on: Nothing (standalone)
- Used by: CLI, Generator, Config (loader calls `discover_plugins()`)

**Technique Layer:**
- Purpose: Define training technique metadata, defaults, and validation
- Location: `envelope/techniques/`
- Contains: `BaseTechnique` ABC (`base.py`) and concrete plugins organized by category (sft, preference, rl, flow, distillation, reward)
- Depends on: Registry (for self-registration), Config models
- Used by: Generator (resolved via registry), Config loader (for default_technique_args)

**Framework Layer:**
- Purpose: Translate EnvelopeConfig into framework-specific artifacts (templates, requirements, launch commands)
- Location: `envelope/frameworks/`
- Contains: `BaseFrameworkAdapter` ABC (`base.py`), concrete adapters organized as single_node and multi_node, plus `from_scratch` with bundled library, capability matrix (`capability_matrix.py`), FSDP accelerate config writer (`accelerate_fsdp.py`)
- Depends on: Registry (for self-registration), Config models
- Used by: Generator (resolved via registry)

**Generator Layer:**
- Purpose: Orchestrate setup directory creation by wiring config, technique, and framework together
- Location: `envelope/generators/`
- Contains: `setup_generator.py` (main orchestrator), `templates/` directory with Jinja2 templates
- Depends on: Config layer, Registry layer, Technique layer, Framework layer, Hardware layer
- Used by: CLI (`setup` command)

**Hardware Layer:**
- Purpose: GPU spec database and hardware-aware optimization suggestions
- Location: `envelope/hardware/`
- Contains: GPU spec dataclass and database (`gpu_specs.py`), auto-optimizer (`auto_optimizer.py`)
- Depends on: Config models
- Used by: Generator, CLI (`validate` command)

**Diagnostics Layer:**
- Purpose: Runtime training monitoring with structured warnings
- Location: `envelope/diagnostics/runtime.py`
- Contains: Diagnostic rules (loss divergence, gradient explosion, reward collapse, clip ratio, KL divergence, throughput degradation), TRL callback integration
- Depends on: Nothing at generation time (self-contained module copied into setups)
- Used by: Generated `setup_*` directories at training runtime

**From-Scratch Library:**
- Purpose: Bundled PyTorch training library for `from_scratch` framework
- Location: `envelope/frameworks/from_scratch/lib/`
- Contains: `BaseFromScratchTrainer` ABC (`base_trainer.py`), stage-level trainers (`sft_trainer.py`, `preference_trainer.py`, `rl_trainer.py`), technique-specific trainers in `techniques/`, custom Triton kernels in `kernels/`
- Depends on: PyTorch, transformers (at runtime only)
- Used by: Generated setups when `framework.backend = "from_scratch"` (copied as `fromscratch/` package)

## Data Flow

**Setup Generation (primary flow):**

1. User runs `envelope setup --name NAME --config CONFIG.yaml`
2. CLI calls `generate_setup(config_path, name, output_base)` in `envelope/generators/setup_generator.py`
3. `discover_plugins()` imports all technique/framework modules, triggering `@register` decorators
4. `load_config(path)` in `envelope/config/loader.py`: loads YAML, calls `merge_technique_defaults()` (looks up technique plugin for `default_technique_args()`), injects `HYPERPARAMETER_DEFAULTS`, validates via `EnvelopeConfig.model_validate()`
5. `validate_config_or_raise(config)` runs cross-field validators in `envelope/config/validators.py`
6. Technique and framework plugins are resolved from registries by their string keys
7. `check_or_raise(technique, framework)` verifies compatibility in `envelope/frameworks/capability_matrix.py`
8. Technique-specific and framework-specific validation run
9. `suggest_optimizations(config)` in `envelope/hardware/auto_optimizer.py` generates HW suggestions
10. Jinja2 environment loads templates from `envelope/generators/templates/`
11. Framework adapter provides `template_context()`, `template_name()`, `launch_command()`, `requirements()`
12. Generator renders: `train.py`, `prepare.py`, `run.sh`, `requirements.txt`
13. Frozen `config.yaml` is dumped
14. Reward modules are copied if RL technique with reward functions
15. Framework-specific extra files copied (e.g., `fromscratch/` lib, `accelerate_config.yaml`)
16. `diagnostics.py` is copied from `envelope/diagnostics/runtime.py`
17. `run.sh` is made executable

**Config Validation (secondary flow):**

1. User runs `envelope validate --config CONFIG.yaml`
2. `discover_plugins()` -> `load_config()` -> `validate_config()` -> `suggest_optimizations()`
3. Results displayed via Rich console

**State Management:**
- No persistent state. Each `envelope setup` run is stateless and produces an immutable directory.
- Plugin registries are populated lazily via `discover_plugins()` (called at entry point)
- Hyperparameter overrides at training runtime via `HPARAM_*` env vars (resolved in generated `train.py`)

## Key Abstractions

**EnvelopeConfig:**
- Purpose: Single source of truth for all configuration. Deeply nested Pydantic v2 model.
- Location: `envelope/config/models.py`
- Pattern: Root model with typed sub-models (ExperimentConfig, ModelConfig, TrainingConfig, DatasetConfig, RewardConfig, HardwareConfig, OptimizationConfig, FrameworkConfig, OutputConfig, etc.)
- Contains model_validators for cross-field auto-correction (stage inference, QLoRA quantization, FSDP mixed precision)

**Registry:**
- Purpose: Generic plugin registry with decorator-based registration and type-safe lookup
- Location: `envelope/registry/base.py`
- Pattern: Singleton instances (`technique_registry`, `framework_registry`) in `envelope/registry/__init__.py`
- Usage: `@technique_registry.register("grpo")` on class definition, `technique_registry.get("grpo")` for lookup

**BaseTechnique:**
- Purpose: Contract for training technique plugins
- Location: `envelope/techniques/base.py`
- Pattern: ABC with abstract properties (`name`, `stage`, `display_name`) and abstract methods (`default_technique_args()`, `validate_technique_args()`, `required_dataset_fields()`) plus optional property overrides (`requires_reference_model`, `requires_reward`, `requires_teacher_model`)
- Implementations: 18 techniques across 6 sub-packages (sft, preference, rl, flow, distillation, reward)

**BaseFrameworkAdapter:**
- Purpose: Contract for framework adapters that translate config into generated artifacts
- Location: `envelope/frameworks/base.py`
- Pattern: ABC with abstract methods (`template_name()`, `requirements()`) and default-implemented methods (`template_context()`, `launch_command()`, `validate_config()`, `extra_setup_files()`)
- Implementations: 8 frameworks -- TRL, Unsloth, Axolotl, TorchTune (single_node), veRL, OpenRLHF, LlamaFactory (multi_node), FromScratch

**Capability Matrix:**
- Purpose: 2D lookup of supported (technique, framework) and (capability, framework) combinations
- Location: `envelope/frameworks/capability_matrix.py`
- Pattern: Dict-based matrix with `(technique_str, framework_str) -> bool` entries plus `(capability_str, framework_str) -> support_level` for infrastructure features (FSDP, Triton, SkyPilot)

**BaseFromScratchTrainer:**
- Purpose: Concrete training loop base class for from_scratch framework
- Location: `envelope/frameworks/from_scratch/lib/base_trainer.py`
- Pattern: Template Method -- concrete `train()` loop calls abstract `compute_loss()` and `collate_fn()`, with lifecycle hooks (`on_train_begin`, `on_step_end`, `on_epoch_end`, `on_save`, `on_train_end`)
- Handles: single-GPU, multi-GPU FSDP, multi-node FSDP, gradient accumulation, mixed precision, checkpointing

## Entry Points

**CLI Entry Point:**
- Location: `envelope/cli.py` (function `main`)
- Triggers: `envelope` command (registered in `pyproject.toml` as `project.scripts`)
- Responsibilities: Parse CLI args, dispatch to sub-commands, display Rich output

**Module Entry Point:**
- Location: `envelope/cli.py` (`if __name__ == "__main__"`)
- Triggers: `python -m envelope.cli`

**Generator Entry Point:**
- Location: `envelope/generators/setup_generator.py` (function `generate_setup`)
- Triggers: Called by CLI `setup` command
- Responsibilities: Full setup generation pipeline (load, validate, resolve plugins, render templates, copy files)

**Plugin Discovery Entry Point:**
- Location: `envelope/registry/__init__.py` (function `discover_plugins`)
- Triggers: Called by loader, CLI commands, and generator before registry access
- Responsibilities: Import all technique and framework modules to trigger `@register` decorators

## Error Handling

**Strategy:** Multi-layer validation with descriptive error messages

**Patterns:**
- **Pydantic model_validators:** Auto-correct (stage inference, quantization defaults) and validate at model level in `envelope/config/models.py`
- **Cross-field validators:** Return `list[str]` of error messages from `validate_config()` in `envelope/config/validators.py`; `validate_config_or_raise()` wraps into `ConfigValidationError`
- **Plugin validation:** Both `BaseTechnique.validate_config()` and `BaseFrameworkAdapter.validate_config()` return `list[str]` of errors
- **Compatibility check:** `check_or_raise()` in `envelope/frameworks/capability_matrix.py` raises `ValueError` for unsupported combinations
- **Registry lookup:** `Registry.get()` raises `KeyError` with available keys listed
- **CLI:** Top-level try/except catches all exceptions, prints via Rich, exits with code 1
- **Template fallback:** Missing Jinja2 templates produce a placeholder file with `raise NotImplementedError`

## Cross-Cutting Concerns

**Logging:** Rich console for CLI output (`envelope/cli.py`). No structured logging framework. Generated setups use `print()` with flush. Diagnostics module uses `print(warning, file=sys.stderr)`.

**Validation:** Three validation tiers: (1) Pydantic field-level (types, ranges, constraints), (2) Pydantic model_validators (cross-field auto-correction), (3) External validators in `envelope/config/validators.py` (hardware/precision compatibility, technique/framework compatibility, FSDP constraints, teacher model requirements). Technique and framework plugins add a fourth tier of custom validation.

**Authentication:** Not applicable -- no external services or auth. Config may reference HuggingFace model IDs or dataset URIs resolved at training runtime, not generation time.

**Plugin Discovery:** Eager import-based discovery via `discover_plugins()`. All technique/framework modules are imported on first call, triggering decorator side-effects. Idempotent (registering same key twice raises error).

---

*Architecture analysis: 2026-04-10*
