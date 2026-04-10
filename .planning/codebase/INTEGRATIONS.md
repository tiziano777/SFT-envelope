# External Integrations

**Analysis Date:** 2026-04-10

## APIs & External Services

**HuggingFace Hub:**
- Used for model loading and dataset access in generated training scripts
- SDK/Client: `transformers` (AutoTokenizer, model classes), `datasets` (load_dataset)
- Auth: HuggingFace token via standard `huggingface-cli login` or `HF_TOKEN` env var
- Referenced in: `envelope/generators/templates/prepare.py.j2` (dataset loading), all `train_*.j2` templates (model loading)
- Model push: optional `push_to_hub` and `hub_model_id` in `OutputConfig` (`envelope/config/models.py`)

**Weights & Biases (W&B):**
- Optional experiment tracking, enabled when `"wandb"` is in `output.report_to`
- SDK/Client: `wandb>=0.16` (added to generated requirements conditionally)
- Auth: Standard `WANDB_API_KEY` env var
- Config fields: `wandb_project`, `wandb_run_name` in `OutputConfig` (`envelope/config/models.py`)
- Referenced in: all framework adapter `requirements()` methods

**TensorBoard:**
- Default experiment tracking (default value of `report_to` is `["tensorboard"]`)
- SDK/Client: `tensorboard>=2.16` (added conditionally)
- No auth required - local filesystem logging
- Referenced in: `OutputConfig.report_to` default (`envelope/config/models.py`)

## Data Storage

**Databases:**
- None - this is a code generation tool, not a running service
- All state is file-based (YAML configs, generated Python scripts, cached datasets)

**File Storage:**
- Local filesystem only
- Generated setups written to `setups/setup_{name}/` directories
- Dataset caching in `./data_cache/` within generated setup directories (`prepare.py.j2`)
- Output artifacts in `./output/` within generated setup directories

**Caching:**
- Dataset preprocessing cache via HuggingFace `datasets` library (`save_to_disk` / `load_from_disk`)
- Cache sentinel file: `.prepare_done` in `data_cache/` directory (`envelope/generators/templates/prepare.py.j2`)

## Authentication & Identity

**Auth Provider:**
- None for the envelope tool itself
- Generated setups may need:
  - HuggingFace token for private models/datasets (standard `HF_TOKEN`)
  - W&B API key for experiment tracking (standard `WANDB_API_KEY`)
  - SSH keys for remote execution (`hardware.remote` config in `envelope/config/models.py`)

## Monitoring & Observability

**Error Tracking:**
- None (no external error tracking service)
- Runtime diagnostics module: `envelope/diagnostics/runtime.py` - copied into each generated setup as `diagnostics.py`
- Diagnostics include: loss divergence, gradient explosion, reward collapse, clip ratio, KL divergence, throughput degradation
- TRL integration via `TRLDiagnosticCallback` (TrainerCallback) in `envelope/diagnostics/runtime.py`

**Logs:**
- `rich.console.Console` for CLI output (`envelope/cli.py`)
- `print()` to stderr for runtime diagnostic warnings (`envelope/diagnostics/runtime.py`)
- No structured logging framework

## CI/CD & Deployment

**Hosting:**
- Not a deployed service - local development tool
- Generated setups target GPU machines (local, SSH, or SLURM)

**CI Pipeline:**
- Not detected (no `.github/workflows/`, `.gitlab-ci.yml`, or similar CI config files)

## Environment Configuration

**Required env vars (envelope tool itself):**
- None required

**Required env vars (generated setups - runtime):**
- `HPARAM_*` - Optional runtime overrides for any hyperparameter (e.g., `HPARAM_LEARNING_RATE=1e-4`)
  - Type coercion handled in `envelope/generators/shared_utils.py`
- `HF_TOKEN` - For private HuggingFace models/datasets (standard HF convention)
- `WANDB_API_KEY` - If W&B tracking enabled (standard W&B convention)
- `MASTER_ADDR`, `MASTER_PORT` - For multi-node training with `torchrun` (from_scratch framework, `envelope/frameworks/from_scratch/fromscratch_adapter.py`)

**Secrets location:**
- No `.env` files in the project
- No secrets stored in the codebase
- All auth relies on standard tool conventions (HF CLI login, W&B CLI login, SSH keys)

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None directly from the envelope tool
- Generated TRL-based setups use `TRLDiagnosticCallback` (Transformers `TrainerCallback`) for diagnostic hooks during training (`envelope/diagnostics/runtime.py`)

## MCP Integration

**code-review-graph:**
- MCP server configured in `.mcp.json`
- Command: `uvx code-review-graph serve` (stdio transport)
- Purpose: Code knowledge graph for structural analysis, impact radius, review context
- Used by Claude Code for codebase exploration (not runtime dependency)

## Framework Adapters (Generated Code Integrations)

The envelope system generates self-contained training setups that integrate with various ML frameworks. These are not runtime dependencies of the envelope tool itself, but are critical integrations in the generated output.

**Single-Node Frameworks:**
| Framework | Adapter | Key Integration |
|-----------|---------|-----------------|
| TRL | `envelope/frameworks/single_node/trl_adapter.py` | HuggingFace Trainer API, Accelerate for multi-GPU |
| Unsloth | `envelope/frameworks/single_node/unsloth_adapter.py` | Custom CUDA kernels, single-GPU only |
| Axolotl | `envelope/frameworks/single_node/axolotl_adapter.py` | YAML-driven, Accelerate/DeepSpeed |
| Torchtune | `envelope/frameworks/single_node/torchtune_adapter.py` | PyTorch native, FSDP2 internal |

**Multi-Node Frameworks:**
| Framework | Adapter | Key Integration |
|-----------|---------|-----------------|
| veRL | `envelope/frameworks/multi_node/verl_adapter.py` | Ray orchestration, vLLM rollout |
| OpenRLHF | `envelope/frameworks/multi_node/openrlhf_adapter.py` | Ray, vLLM, DeepSpeed |
| LlamaFactory | `envelope/frameworks/multi_node/llamafactory_adapter.py` | Accelerate/FSDP, DeepSpeed |

**Custom Framework:**
| Framework | Adapter | Key Integration |
|-----------|---------|-----------------|
| from_scratch | `envelope/frameworks/from_scratch/fromscratch_adapter.py` | Raw PyTorch, torchrun, custom Triton kernels |

**Distributed Training:**
- FSDP config generation: `envelope/frameworks/accelerate_fsdp.py` (shared by TRL, Axolotl, LlamaFactory)
- DeepSpeed: supported via framework-specific configuration
- Infrastructure capability matrix: `envelope/frameworks/capability_matrix.py` tracks FSDP, Triton, SkyPilot support per framework

---

*Integration audit: 2026-04-10*
