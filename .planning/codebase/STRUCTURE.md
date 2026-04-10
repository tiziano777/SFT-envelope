# Codebase Structure

**Analysis Date:** 2026-04-10

## Directory Layout

```
FineTuning-Envelope/
├── envelope/                   # Main Python package
│   ├── __init__.py             # Package init, version
│   ├── cli.py                  # Click CLI entry point
│   ├── config/                 # Configuration schema, loading, validation
│   │   ├── __init__.py         # Re-exports: EnvelopeConfig, load_config, validate_config
│   │   ├── models.py           # Pydantic v2 models (EnvelopeConfig root + all sub-models, enums)
│   │   ├── defaults.py         # HYPERPARAMETER_DEFAULTS + TECHNIQUE_DEFAULTS dicts
│   │   ├── loader.py           # YAML loading, technique default merging, config construction
│   │   └── validators.py       # Cross-field validation functions
│   ├── registry/               # Plugin registry system
│   │   ├── __init__.py         # Singleton registries + discover_plugins()
│   │   └── base.py             # Generic Registry class
│   ├── techniques/             # Training technique plugins
│   │   ├── __init__.py
│   │   ├── base.py             # BaseTechnique ABC
│   │   ├── sft/                # Stage 1: Supervised Fine-Tuning
│   │   │   ├── __init__.py
│   │   │   └── full_sft.py     # SFT technique plugin
│   │   ├── preference/         # Stage 2: Preference optimization
│   │   │   ├── __init__.py
│   │   │   ├── dpo.py          # DPO technique
│   │   │   ├── simpo.py        # SimPO technique
│   │   │   ├── kto.py          # KTO technique
│   │   │   └── orpo.py         # ORPO technique
│   │   ├── rl/                 # Stage 3: Reinforcement Learning
│   │   │   ├── __init__.py
│   │   │   ├── grpo.py         # GRPO technique
│   │   │   ├── ppo.py          # PPO technique
│   │   │   ├── dapo.py         # DAPO technique
│   │   │   ├── vapo.py         # VAPO technique
│   │   │   ├── rloo.py         # RLOO technique
│   │   │   ├── reinforce_pp.py # REINFORCE++ technique
│   │   │   └── dr_grpo.py      # Dr. GRPO technique
│   │   ├── flow/               # Flow-based RL
│   │   │   ├── __init__.py
│   │   │   ├── flowrl.py       # FlowRL technique
│   │   │   └── prime.py        # PRIME technique
│   │   ├── distillation/       # Knowledge distillation
│   │   │   ├── __init__.py
│   │   │   ├── gkd.py          # GKD technique
│   │   │   ├── sdft.py         # SDFT technique
│   │   │   ├── sdpo.py         # SDPO technique
│   │   │   └── gold.py         # GOLD technique
│   │   └── reward/             # Reward modeling
│   │       ├── __init__.py
│   │       └── reward_modeling.py  # Reward modeling technique
│   ├── frameworks/             # Framework adapters
│   │   ├── __init__.py
│   │   ├── base.py             # BaseFrameworkAdapter ABC
│   │   ├── capability_matrix.py # Technique x framework compatibility + infra capability matrix
│   │   ├── accelerate_fsdp.py  # Shared FSDP accelerate config writer
│   │   ├── single_node/        # Single-node framework adapters
│   │   │   ├── __init__.py
│   │   │   ├── trl_adapter.py      # HuggingFace TRL
│   │   │   ├── unsloth_adapter.py  # Unsloth
│   │   │   ├── axolotl_adapter.py  # Axolotl
│   │   │   └── torchtune_adapter.py # TorchTune
│   │   ├── multi_node/         # Multi-node framework adapters
│   │   │   ├── __init__.py
│   │   │   ├── verl_adapter.py       # veRL (ByteDance)
│   │   │   ├── openrlhf_adapter.py   # OpenRLHF
│   │   │   └── llamafactory_adapter.py # LlamaFactory
│   │   └── from_scratch/       # Raw PyTorch framework with bundled library
│   │       ├── __init__.py
│   │       ├── fromscratch_adapter.py  # Framework adapter
│   │       └── lib/             # Bundled training library (copied to setups)
│   │           ├── __init__.py
│   │           ├── base_trainer.py      # BaseFromScratchTrainer ABC + training loop
│   │           ├── sft_trainer.py       # SFT trainer
│   │           ├── preference_trainer.py # Preference trainer base
│   │           ├── rl_trainer.py        # RL trainer base
│   │           ├── techniques/          # Technique-specific trainers
│   │           │   ├── __init__.py
│   │           │   ├── grpo.py, ppo.py, dapo.py, vapo.py, rloo.py
│   │           │   ├── reinforce_pp.py, dr_grpo.py
│   │           │   ├── dpo.py, simpo.py, kto.py, orpo.py
│   │           │   ├── flowrl.py, prime.py
│   │           │   └── (14 technique trainer files total)
│   │           └── kernels/             # Custom Triton kernels
│   │               ├── __init__.py
│   │               ├── registry.py      # Kernel registry
│   │               ├── cross_entropy.py # Triton cross-entropy
│   │               ├── rms_norm.py      # Triton RMS norm
│   │               ├── softmax.py       # Triton softmax
│   │               └── ops.py           # Kernel ops utilities
│   ├── generators/             # Setup generation orchestration
│   │   ├── __init__.py
│   │   ├── setup_generator.py  # Main generate_setup() function
│   │   └── templates/          # Jinja2 templates for generated files
│   │       ├── run.sh.j2                    # Shell launcher
│   │       ├── prepare.py.j2               # Data preparation script
│   │       ├── requirements.txt.j2          # Pip requirements
│   │       ├── train_sft_trl.py.j2          # TRL SFT training script
│   │       ├── train_grpo_trl.py.j2         # TRL GRPO training script
│   │       ├── train_dpo_trl.py.j2          # TRL DPO training script
│   │       ├── train_dpo_unsloth.py.j2      # Unsloth DPO training script
│   │       ├── train_ppo_openrlhf.py.j2     # OpenRLHF PPO training script
│   │       ├── train_ppo_verl.sh.j2         # veRL PPO launch script
│   │       ├── train_gkd_trl.py.j2          # TRL GKD distillation script
│   │       ├── train_gold_trl.py.j2         # TRL GOLD distillation script
│   │       ├── train_sdft_trl.py.j2         # TRL SDFT distillation script
│   │       ├── train_sdpo_trl.py.j2         # TRL SDPO distillation script
│   │       ├── train_reward_modeling_trl.py.j2 # TRL reward modeling script
│   │       ├── train_sft_axolotl.yaml.j2    # Axolotl SFT config
│   │       ├── train_sft_torchtune.yaml.j2  # TorchTune SFT config
│   │       ├── train_sft_llamafactory.yaml.j2 # LlamaFactory SFT config
│   │       └── train_fromscratch.py.j2      # From-scratch training script
│   ├── hardware/               # GPU specs and optimization suggestions
│   │   ├── __init__.py
│   │   ├── gpu_specs.py        # GPUSpec dataclass + GPU_DATABASE dict
│   │   └── auto_optimizer.py   # suggest_optimizations() function
│   ├── diagnostics/            # Runtime training diagnostics
│   │   ├── __init__.py
│   │   └── runtime.py          # Diagnostic rules + TRL callback (copied to setups)
│   └── rewards/                # Reward functions placeholder
│       └── __init__.py         # Empty -- user provides reward modules
├── configs/                    # Example YAML configurations
│   └── examples/
│       ├── grpo_qlora_qwen.yaml        # GRPO + QLoRA on Qwen2.5-7B
│       ├── grpo_lora_velvet2b.yaml     # GRPO + LoRA on Velvet-2B
│       ├── grpo_fromscratch.yaml       # GRPO from-scratch
│       ├── sft_lora_llama3.yaml        # SFT + LoRA on Llama3
│       ├── sft_fsdp_trl.yaml           # SFT with FSDP via TRL
│       ├── dpo_qlora_unsloth.yaml      # DPO + QLoRA via Unsloth
│       ├── gkd_lora_trl.yaml           # GKD distillation via TRL
│       └── reward_modeling_trl.yaml    # Reward modeling via TRL
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── unit/                   # Unit tests
│   │   ├── __init__.py
│   │   ├── test_config_models.py
│   │   ├── test_validators.py
│   │   ├── test_registry.py
│   │   ├── test_techniques.py
│   │   ├── test_frameworks.py
│   │   ├── test_fsdp.py
│   │   ├── test_diagnostics.py
│   │   ├── test_distillation_techniques.py
│   │   ├── test_reward_modeling.py
│   │   └── test_setup_generator.py
│   └── integration/            # Integration tests
│       ├── __init__.py
│       └── test_make_setup.py
├── setups/                     # Generated setup directories (gitignored output)
│   └── setup_grpo-velvet2b/    # Example generated setup
│       ├── train.py
│       ├── prepare.py
│       ├── run.sh
│       ├── requirements.txt
│       ├── config.yaml
│       └── rewards/
├── examples/                   # Additional example YAML configs
│   ├── distillation-gkd.yaml
│   ├── qlofa-sft.yaml
│   └── torchtune-sft.yaml
├── docs/                       # Project documentation
│   ├── architecture.md
│   ├── config.md
│   ├── diagnostics.md
│   ├── distillation.md
│   ├── frameworks.md
│   ├── from-scratch.md
│   ├── fsdp.md
│   ├── generator.md
│   ├── hardware.md
│   ├── registry.md
│   └── techniques.md
├── pyproject.toml              # Project metadata, dependencies, scripts, tool config
├── Makefile                    # Development commands (setup, validate, test, lint, format)
├── CLAUDE.md                   # Claude Code project instructions
├── README.md                   # Project README
├── LINEAGE_SYSTEM_ARCHITECTURE.md # Detailed lineage system design doc
├── workflow.md                 # Workflow documentation
├── uv.lock                     # UV lockfile
└── .planning/                  # GSD planning directory
    └── codebase/               # Auto-generated codebase analysis docs
```

## Directory Purposes

**`envelope/`:**
- Purpose: Main Python package containing all source code
- Contains: CLI, config schema, registry, technique plugins, framework adapters, generator, hardware specs, diagnostics
- Key files: `cli.py` (entry point), `config/models.py` (schema), `generators/setup_generator.py` (orchestrator)

**`envelope/config/`:**
- Purpose: Configuration management -- schema, loading, defaults, validation
- Contains: Pydantic models, YAML loader, default values, cross-field validators
- Key files: `models.py` (443 lines, 20+ enums, 15+ sub-models, root `EnvelopeConfig`), `defaults.py` (technique-specific default args), `validators.py` (7 validation functions)

**`envelope/registry/`:**
- Purpose: Plugin registration and discovery infrastructure
- Contains: Generic `Registry` class, singleton registry instances, plugin import trigger
- Key files: `base.py` (71 lines, `Registry` generic class), `__init__.py` (30 lines, `technique_registry`, `framework_registry`, `discover_plugins()`)

**`envelope/techniques/`:**
- Purpose: Training technique plugin definitions
- Contains: 18 technique plugins organized in 6 sub-packages by training stage
- Key files: `base.py` (63 lines, `BaseTechnique` ABC), `rl/grpo.py` (reference technique implementation)

**`envelope/frameworks/`:**
- Purpose: Framework adapter implementations and compatibility matrix
- Contains: 8 framework adapters, compatibility matrix, FSDP config writer, from_scratch bundled library
- Key files: `base.py` (64 lines, `BaseFrameworkAdapter` ABC), `capability_matrix.py` (160 lines, 86 technique x framework entries + 24 infra entries), `single_node/trl_adapter.py` (reference adapter)

**`envelope/frameworks/from_scratch/lib/`:**
- Purpose: Bundled raw PyTorch training library copied into generated `setup_*` dirs
- Contains: Base trainer with full training loop, stage-level trainers (SFT, preference, RL), 14 technique-specific trainer subclasses, 4 Triton kernel implementations
- Key files: `base_trainer.py` (588 lines, `BaseFromScratchTrainer` with complete training loop + FSDP support), `kernels/` (custom Triton kernels)

**`envelope/generators/`:**
- Purpose: Setup directory generation orchestration and templates
- Contains: Generator function and 18 Jinja2 templates
- Key files: `setup_generator.py` (174 lines, `generate_setup()` function), `templates/` (18 `.j2` template files)

**`envelope/hardware/`:**
- Purpose: GPU specification database and hardware-aware optimization suggestions
- Contains: GPU specs dataclass with 12 GPU models, optimization suggestion engine
- Key files: `gpu_specs.py` (52 lines, `GPUSpec` + `GPU_DATABASE`), `auto_optimizer.py` (111 lines, `suggest_optimizations()`)

**`envelope/diagnostics/`:**
- Purpose: Runtime training diagnostics module (copied to generated setups)
- Contains: 6 diagnostic rules, rate-limited warning system, TRL callback integration
- Key files: `runtime.py` (242 lines, self-contained)

**`configs/examples/`:**
- Purpose: Reference YAML configurations demonstrating various technique/framework/config combinations
- Contains: 8 example configs covering GRPO, SFT, DPO, GKD, reward modeling

**`tests/`:**
- Purpose: Test suite -- unit tests for all core modules, integration tests for end-to-end setup generation
- Contains: 12 test files (11 unit, 1 integration)
- Key files: `unit/test_setup_generator.py`, `unit/test_config_models.py`, `integration/test_make_setup.py`

**`docs/`:**
- Purpose: Detailed project documentation per subsystem
- Contains: 11 markdown docs covering architecture, config, frameworks, techniques, etc.

**`setups/`:**
- Purpose: Output directory for generated setup directories
- Contains: Immutable `setup_*` directories (each has `train.py`, `prepare.py`, `run.sh`, `requirements.txt`, `config.yaml`)
- Generated: Yes
- Committed: Only example setups

## Key File Locations

**Entry Points:**
- `envelope/cli.py`: CLI entry point registered as `envelope` command via `pyproject.toml`
- `envelope/generators/setup_generator.py`: Core `generate_setup()` function

**Configuration:**
- `pyproject.toml`: Project metadata, deps, CLI script registration, ruff/pytest config
- `Makefile`: Dev commands (setup, validate, test, lint, format)
- `envelope/config/models.py`: Complete Pydantic v2 schema (single source of truth)
- `envelope/config/defaults.py`: Hyperparameter and technique-specific defaults

**Core Logic:**
- `envelope/generators/setup_generator.py`: Setup generation orchestrator
- `envelope/config/loader.py`: Config loading pipeline
- `envelope/config/validators.py`: Cross-field validation
- `envelope/registry/base.py`: Plugin registry
- `envelope/frameworks/capability_matrix.py`: Compatibility matrix

**Testing:**
- `tests/unit/`: Unit tests for all modules
- `tests/integration/test_make_setup.py`: End-to-end setup generation test

## Naming Conventions

**Files:**
- Technique plugins: `{technique_name}.py` (e.g., `grpo.py`, `dpo.py`, `simpo.py`)
- Framework adapters: `{framework}_adapter.py` (e.g., `trl_adapter.py`, `verl_adapter.py`)
- Jinja2 templates: `train_{technique}_{framework}.py.j2` (e.g., `train_grpo_trl.py.j2`, `train_fromscratch.py.j2`)
- Tests: `test_{module_name}.py` (e.g., `test_config_models.py`, `test_validators.py`)

**Directories:**
- Technique sub-packages: Named by training stage (`sft/`, `preference/`, `rl/`, `flow/`, `distillation/`, `reward/`)
- Framework sub-packages: Named by scale (`single_node/`, `multi_node/`, `from_scratch/`)

**Classes:**
- Technique classes: `{TechniqueName}Technique` (e.g., `GRPOTechnique`, `DPOTechnique`)
- Framework classes: `{FrameworkName}Adapter` (e.g., `TRLAdapter`, `VeRLAdapter`)
- From-scratch trainers: `{TechniqueName}Trainer` (e.g., `GRPOTrainer`, `SFTTrainer`)

**Registry Keys:**
- Technique keys: lowercase technique name (e.g., `"grpo"`, `"dpo"`, `"sft"`)
- Framework keys: lowercase framework name (e.g., `"trl"`, `"verl"`, `"from_scratch"`)

## Where to Add New Code

**New Training Technique:**
1. Create `envelope/techniques/{stage}/{technique_name}.py`
2. Implement `BaseTechnique` ABC and decorate with `@technique_registry.register("{name}")`
3. Add default technique args to `envelope/config/defaults.py` TECHNIQUE_DEFAULTS dict
4. Add `Technique.{NAME}` enum value to `envelope/config/models.py`
5. Add `TECHNIQUE_STAGE_MAP` entry in `envelope/config/models.py`
6. Add compatibility entries to `envelope/frameworks/capability_matrix.py`
7. Import the module in `envelope/registry/__init__.py` `discover_plugins()` (if in new sub-package)
8. Add Jinja2 template: `envelope/generators/templates/train_{technique}_{framework}.py.j2`
9. Add tests: `tests/unit/test_techniques.py` (or new test file)

**New Framework Adapter:**
1. Create `envelope/frameworks/{single_node|multi_node}/{framework}_adapter.py`
2. Implement `BaseFrameworkAdapter` ABC and decorate with `@framework_registry.register("{name}")`
3. Add `FrameworkBackend.{NAME}` enum value to `envelope/config/models.py`
4. Add compatibility entries to `envelope/frameworks/capability_matrix.py`
5. Add infra capability entries to `_INFRA_MATRIX` in `capability_matrix.py`
6. Import the module in `envelope/registry/__init__.py` `discover_plugins()`
7. Add Jinja2 templates: `envelope/generators/templates/train_{technique}_{framework}.py.j2`
8. Add tests: `tests/unit/test_frameworks.py`

**New Validator:**
1. Add private function `_validate_{what}(config) -> list[str]` in `envelope/config/validators.py`
2. Call it from `validate_config()` function
3. Add tests in `tests/unit/test_validators.py`

**New GPU Spec:**
1. Add entry to `GPU_DATABASE` dict in `envelope/hardware/gpu_specs.py`

**New Diagnostic Rule:**
1. Add function in `envelope/diagnostics/runtime.py` following existing rule signature
2. Add to `ALL_RULES` list in same file
3. Add tests in `tests/unit/test_diagnostics.py`

**New Jinja2 Template:**
1. Place in `envelope/generators/templates/`
2. Name following convention: `train_{technique}_{framework}.py.j2` (or `.yaml.j2`, `.sh.j2`)
3. Template receives context from `framework.template_context(config)` plus `suggestions`, `technique_plugin`, `framework_plugin`

**New Example Config:**
1. Place in `configs/examples/{technique}_{details}.yaml`
2. Must validate: `make validate CONFIG=configs/examples/{file}.yaml`

**Utilities:**
- Shared framework utilities: `envelope/frameworks/` (e.g., `accelerate_fsdp.py`)
- Config helpers: `envelope/config/`
- No dedicated `utils/` directory exists -- add one if needed at `envelope/utils/`

## Special Directories

**`setups/`:**
- Purpose: Output directory for generated experiment setups
- Generated: Yes (by `envelope setup` command)
- Committed: Selectively (example setups may be committed)
- Immutable: Once generated, setup directories should not be modified

**`envelope/frameworks/from_scratch/lib/`:**
- Purpose: Bundled training library that gets copied wholesale into generated setups as `fromscratch/` package
- Generated: No (source code, not generated)
- Committed: Yes
- Note: This directory is a library distributed via file copy, not pip install. Changes here affect all future generated setups.

**`envelope/generators/templates/`:**
- Purpose: Jinja2 templates rendered into generated setup files
- Generated: No
- Committed: Yes
- Note: Templates receive context dict from framework adapters; use `{{ config.training.technique.value }}` style access

**`.planning/`:**
- Purpose: GSD planning and codebase analysis documents
- Generated: Yes (by GSD tools)
- Committed: Yes

---

*Structure analysis: 2026-04-10*
