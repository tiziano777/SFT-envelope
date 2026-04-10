# Technology Stack

**Analysis Date:** 2026-04-10

## Languages

**Primary:**
- Python 3.10+ - All application code, CLI, config models, generators, techniques, frameworks

**Secondary:**
- Jinja2 templating - Template language for generated training scripts (`envelope/generators/templates/*.j2`)
- YAML - Configuration format for experiment definitions (`configs/examples/*.yaml`)
- Bash - Generated launch scripts (`run.sh.j2`) and `Makefile` targets

## Runtime

**Environment:**
- Python >=3.10 (uses `X | Y` union syntax, not `Union[X, Y]`)
- Target version configured as `py310` in ruff

**Package Manager:**
- **uv** - Primary package manager (evidenced by `uv.lock` at project root)
- **pip** - Secondary, used in generated setup directories and `Makefile` install target
- Lockfile: `uv.lock` present (3590 lines)

## Frameworks

**Core:**
- **Pydantic** v2 (`>=2.0`) - All data models and configuration schema (`envelope/config/models.py`)
- **Click** (`>=8.0`) - CLI framework (`envelope/cli.py`)
- **Rich** (`>=13.0`) - Terminal output formatting, tables, colored output (`envelope/cli.py`)
- **Jinja2** (`>=3.1`) - Template rendering for generated training scripts (`envelope/generators/setup_generator.py`)
- **PyYAML** (`>=6.0`) - YAML configuration loading and serialization (`envelope/config/loader.py`)

**Testing:**
- **pytest** (`>=8.0`) - Test runner, configured in `pyproject.toml` with `testpaths = ["tests"]`
- **pytest-cov** (`>=5.0`) - Coverage reporting

**Build/Dev:**
- **Hatchling** - Build backend (`pyproject.toml` build-system)
- **ruff** (`>=0.4`) - Linting and formatting (configured: `target-version = "py310"`, `line-length = 120`)
- **Make** - Task runner for common operations (`Makefile`)

## Key Dependencies

**Critical (project runtime):**
- `pydantic>=2.0` - Schema validation, model_validator decorators, cross-field validation
- `pyyaml>=6.0` - YAML config parsing via `yaml.safe_load`
- `jinja2>=3.1` - Template rendering with `StrictUndefined` for safety
- `click>=8.0` - CLI command groups, options, arguments
- `rich>=13.0` - Console output, Table rendering

**Generated Setup Dependencies (not installed locally, but emitted into requirements.txt):**
- `torch>=2.1` - PyTorch (all frameworks)
- `transformers>=4.40` - HuggingFace Transformers (most frameworks)
- `trl>=1.0.0` - HuggingFace TRL for RL/preference training
- `datasets>=2.18` - HuggingFace Datasets for data loading
- `accelerate>=0.30` - HuggingFace Accelerate for distributed training
- `peft>=0.11` - Parameter-efficient fine-tuning (LoRA, QLoRA)
- `bitsandbytes>=0.43` - Quantization (NF4, INT8)
- `flash-attn>=2.5` - Flash Attention optimization
- `vllm>=0.4` - vLLM for RL rollout generation
- `ray>=2.30` - Ray for veRL/OpenRLHF distributed orchestration
- `deepspeed>=0.14` - DeepSpeed ZeRO optimization
- `unsloth>=2024.8` - Unsloth accelerated training
- `axolotl>=0.4` - Axolotl fine-tuning framework
- `torchtune>=0.3` - PyTorch native fine-tuning
- `torchao>=0.4` - Torchtune quantization support
- `llamafactory>=0.8` - LlamaFactory fine-tuning
- `openrlhf>=0.4` - OpenRLHF RLHF framework
- `verl>=0.2` - veRL (ByteDance) RL framework
- `triton>=3.0` - Triton custom kernels (from_scratch framework)
- `tensorboard>=2.16` - Training logging
- `wandb>=0.16` - Weights & Biases experiment tracking

## Configuration

**Environment:**
- No `.env` files - project does not use environment variables at build/dev time
- Generated setups support `HPARAM_*` env vars for runtime hyperparameter overrides (see `envelope/generators/shared_utils.py`)
- `WANDB_PROJECT`, `WANDB_RUN_NAME` configurable via `output` section in YAML

**Build:**
- `pyproject.toml` - Project metadata, dependencies, build config, ruff config, pytest config
- `Makefile` - Dev workflow: `make install`, `make test`, `make lint`, `make format`
- `uv.lock` - Dependency lockfile
- `.mcp.json` - MCP server config for code-review-graph tool (uses `uvx code-review-graph serve`)

**CLI Entry Point:**
- `envelope = "envelope.cli:main"` defined in `pyproject.toml` `[project.scripts]`
- Also runnable via `python -m envelope.cli`

## Platform Requirements

**Development:**
- Python >=3.10
- uv package manager (recommended) or pip
- No OS-specific requirements - pure Python project
- Install: `pip install -e ".[dev]"` or `make install`

**Production (Generated Setups):**
- NVIDIA GPU with CUDA support (varies by config: A100, H100, H200, L40S, L4, T4, V100, RTX4090, RTX3090)
- GPU specs tracked in `envelope/hardware/gpu_specs.py` with VRAM, compute capability, TFLOPS
- Linux (for CUDA/distributed training) - generated `run.sh` scripts use bash
- SSH or SLURM for remote execution (optional, configured via `hardware.remote`)

---

*Stack analysis: 2026-04-10*
