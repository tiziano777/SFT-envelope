# Codebase Concerns

**Analysis Date:** 2026-04-10

## Tech Debt

**Missing NeMo Framework Adapter:**
- Issue: `FrameworkBackend.NEMO` is defined in the enum (`envelope/config/models.py:126`) and the capability matrix (`envelope/frameworks/capability_matrix.py:19,27,47`) lists NeMo as compatible with SFT, DPO, and PPO, but no `NemoAdapter` class exists anywhere in the codebase. There is no registered plugin for `"nemo"`.
- Files: `envelope/config/models.py`, `envelope/frameworks/capability_matrix.py`
- Impact: Users who set `framework.backend: nemo` will pass enum validation but fail at runtime with a `KeyError` from the framework registry. The capability matrix also incorrectly reports NeMo as compatible with techniques.
- Fix approach: Either implement `envelope/frameworks/multi_node/nemo_adapter.py` with `@framework_registry.register("nemo")`, or remove `NEMO` from `FrameworkBackend` and all NeMo entries from `_MATRIX` in `capability_matrix.py`.

**Massive Template Gap:**
- Issue: The `_render_template()` function in `envelope/generators/setup_generator.py:135-153` silently generates placeholder files with `raise NotImplementedError(...)` when a Jinja2 template is missing. Many valid technique+framework combinations in the capability matrix have no corresponding template.
- Files: `envelope/generators/setup_generator.py:144-150`, `envelope/generators/templates/`
- Impact: Generated `setup_*/train.py` files will crash immediately with `NotImplementedError` for the following known-compatible combos that lack templates:
  - TRL: `simpo`, `kto`, `orpo`, `ppo`, `rloo` (only `sft`, `dpo`, `grpo`, `gkd`, `sdft`, `sdpo`, `gold`, `reward_modeling` have templates)
  - Unsloth: `sft`, `simpo`, `orpo`, `grpo` (only `dpo` has a template)
  - veRL: `grpo`, `dapo`, `vapo`, `reinforce_pp`, `dr_grpo`, `flowrl`, `prime` (only `ppo` has a template)
  - OpenRLHF: `sft`, `dpo`, `grpo`, `rloo`, `reinforce_pp` (only `ppo` has a template)
  - Axolotl: `dpo` (only `sft` has a template)
  - LlamaFactory: `dpo`, `kto`, `orpo` (only `sft` has a template)
  - Torchtune: `dpo` (only `sft` has a template)
- Fix approach: Prioritize templates for the most common combos: TRL+ppo, TRL+kto, TRL+simpo, veRL+grpo, Unsloth+sft, Unsloth+grpo. The placeholder fallback should at minimum emit a warning via `rich.console` during generation instead of silently producing broken output.

**Empty `envelope/rewards/__init__.py`:**
- Issue: The `envelope/rewards/` package is an empty shell -- just an `__init__.py` with no content. The reward function copying logic in `_copy_reward_modules()` (`envelope/generators/setup_generator.py:156-166`) relies on `config.reward.functions[].module_path` being a resolvable filesystem path, but there are no built-in reward functions or examples.
- Files: `envelope/rewards/__init__.py`, `envelope/generators/setup_generator.py:156-166`
- Impact: Users must write their own reward functions with no scaffold. The `_copy_reward_modules` path-resolution logic (`Path(*module_parts).with_suffix(".py")`) is fragile -- it splits on `.` and constructs a relative path, which only works if `module_path` corresponds exactly to a relative filesystem path from CWD.
- Fix approach: Add at least one example reward function (e.g., `envelope/rewards/math_correctness.py`) and improve `_copy_reward_modules` to handle Python module paths properly (use `importlib.util.find_spec()` instead of naive path construction).

**Diagnostics Module Uses Global Mutable State:**
- Issue: `envelope/diagnostics/runtime.py:58` uses a module-level `_state = DiagnosticState()` singleton. This means state persists across multiple calls in the same process, which is correct for training but breaks testability and reusability.
- Files: `envelope/diagnostics/runtime.py:58`
- Impact: If the diagnostics module is imported in a multi-run context (e.g., hyperparameter sweeps, test suites), state from previous runs leaks. The `reset_state()` function exists but must be called manually.
- Fix approach: Low priority. The current `reset_state()` approach works. Consider making `DiagnosticState` injectable rather than global if multi-run support is needed.

**Diagnostic Suggestion Strings Are Partially Italian:**
- Issue: The `suggestion` fields in diagnostic warnings use mixed Italian/English text (e.g., "Ridurre learning_rate o verificare il dataset", "Advantage signal collapsed -- verificare la reward function").
- Files: `envelope/diagnostics/runtime.py:77,94,117,136,155,179`
- Impact: Non-Italian-speaking users will not understand the actionable suggestions. These strings are user-facing -- they print to stderr during training.
- Fix approach: Translate all `suggestion` strings to English for consistency with the rest of the codebase, which is entirely English.

## Known Bugs

**`_copy_reward_modules` Silently Fails:**
- Symptoms: When `config.reward.functions` contains a reward function with a `module_path` that does not resolve to a file on disk, the function silently skips it. No error, no warning.
- Files: `envelope/generators/setup_generator.py:164-166`
- Trigger: Set `module_path: "rewards.math_correctness"` in config without having the file present at `rewards/math_correctness.py` relative to CWD.
- Workaround: Manually copy reward functions into the generated setup directory.

**`technique_registry.get()` Returns a Class, Not an Instance in `merge_technique_defaults()`:**
- Symptoms: In `envelope/config/loader.py:41`, `technique_obj = technique_registry.get(technique)` returns a class (not an instance). Then `.default_technique_args()` is called on the class directly, which works because it is instantiated as `technique_obj()` -- except the code calls it without parentheses, meaning it calls the method on the class itself.
- Files: `envelope/config/loader.py:40-41`
- Trigger: This is called on every `load_config()`. It works because `default_technique_args()` is decorated as an instance method but the registry stores classes and the code calls it on the class. This relies on the method not accessing `self` for most techniques.
- Workaround: None needed currently -- it works by accident since `default_technique_args()` in most technique implementations only returns a hardcoded dict and does not use `self`.

**`loader.py` Does Not Merge `hparam_overrides` When Present:**
- Symptoms: If the user specifies `hparam_overrides` in their YAML, the defaults from `HYPERPARAMETER_DEFAULTS` are completely ignored rather than merged.
- Files: `envelope/config/loader.py:62-63`
- Trigger: Include any `hparam_overrides:` section in the YAML config file.
- Workaround: Omit `hparam_overrides` from YAML to get all defaults.

## Security Considerations

**`trust_remote_code` Config Option:**
- Risk: `ModelConfig.trust_remote_code` defaults to `False` (`envelope/config/models.py:207`) but can be set to `True` by users. When enabled, HuggingFace Transformers will execute arbitrary Python code from the model repository.
- Files: `envelope/config/models.py:207`
- Current mitigation: Default is `False`. The generated templates pass this flag through to `AutoModelForCausalLM.from_pretrained()`.
- Recommendations: Add a validator warning when `trust_remote_code: true` is set. Consider documenting the security implications in the generated `run.sh`.

**No Input Sanitization for Jinja2 Templates:**
- Risk: User-provided config values (model names, dataset URIs, etc.) are injected directly into Jinja2 templates that generate Python code. A crafted config could inject arbitrary Python code into `train.py`.
- Files: `envelope/generators/setup_generator.py:86-91`, `envelope/generators/templates/*.j2`
- Current mitigation: `jinja2.StrictUndefined` is set (`setup_generator.py:90`), but this only prevents missing variables -- it does not sanitize input values. The `autoescape` feature is not enabled (it is off by default in Jinja2).
- Recommendations: Since the generated files are meant to be run by the same user who provides the config, the risk is self-injection. However, if configs are shared or generated by external tools, add validation that model names and URIs match expected patterns (e.g., regex for HuggingFace model IDs).

**`.gitignore` Does Not Cover Sensitive Files:**
- Risk: The `.gitignore` (`envelope/../../.gitignore`) does not exclude `.env`, `*.pem`, `*.key`, or credential files. Generated `setup_*/` directories could contain sensitive configuration.
- Files: `.gitignore`
- Current mitigation: The `setups/` directory is not in `.gitignore` either.
- Recommendations: Add `.env`, `.env.*`, `*.key`, `*.pem`, `setups/*/config.yaml` (may contain model paths), and `wandb/` to `.gitignore`.

## Performance Bottlenecks

**Sequential Generation in `RLTrainer._generate_with_logprobs()`:**
- Problem: The RL trainer generates completions one at a time in a nested loop (`for prompt in prompts: for _ in range(num_generations)`), calling `model.generate()` per-completion.
- Files: `envelope/frameworks/from_scratch/lib/rl_trainer.py:131-164`
- Cause: Each `model.generate()` call processes a single sequence. With `num_generations=16` and batch_size=2, this results in 32 sequential generation calls per training step.
- Improvement path: Batch prompts by repeating each prompt `num_generations` times and calling `model.generate()` once with the full batch. This can provide 10-50x speedup depending on GPU utilization.

**`_recompute_logprobs()` Runs One Sample at a Time:**
- Problem: The log-probability recomputation in `RLTrainer._recompute_logprobs()` iterates over each (prompt, completion) pair individually.
- Files: `envelope/frameworks/from_scratch/lib/rl_trainer.py:194-227`
- Cause: Each forward pass processes a single sample. With 32 completions per batch, this means 32 separate forward passes.
- Improvement path: Batch the forward passes by padding sequences to the same length and running a single forward pass.

**`discover_plugins()` Called Redundantly:**
- Problem: `discover_plugins()` is called in multiple places -- `load_config()`, `generate_setup()`, CLI commands, and test modules. Each call re-imports all technique and framework modules.
- Files: `envelope/registry/__init__.py:15-27`, `envelope/config/loader.py:35`, `envelope/generators/setup_generator.py:48`, `envelope/cli.py:51,84,100`
- Cause: No guard to check if plugins are already discovered.
- Improvement path: Add a `_discovered = False` flag in `envelope/registry/__init__.py` and short-circuit if already called. This is a minor optimization but reduces import overhead.

## Fragile Areas

**Capability Matrix Sync with Adapters:**
- Files: `envelope/frameworks/capability_matrix.py`, all adapter `validate_config()` methods
- Why fragile: The capability matrix (`_MATRIX` dict) and each adapter's `validate_config()` independently define which techniques are supported. These can drift apart. For example, the matrix says `("sft", "nemo"): True` but no NeMo adapter exists.
- Safe modification: When adding a new technique or framework, update both `_MATRIX` in `capability_matrix.py` AND the adapter's `validate_config()` `supported` set. Add a test that cross-checks these two sources.
- Test coverage: The tests in `tests/unit/test_frameworks.py` cover individual adapters and matrix lookups but do not verify that the matrix and adapters agree.

**`TECHNIQUE_DEFAULTS` vs. Technique Plugin Defaults:**
- Files: `envelope/config/defaults.py:23-136`, each technique plugin's `default_technique_args()` method
- Why fragile: `TECHNIQUE_DEFAULTS` in `defaults.py` and the technique plugin's `default_technique_args()` return the same data but are defined independently. If one is updated without the other, they diverge silently. The `merge_technique_defaults()` in `loader.py` uses the plugin defaults, while `HYPERPARAMETER_DEFAULTS` is used elsewhere.
- Safe modification: Consider having technique plugins reference `TECHNIQUE_DEFAULTS` directly, or remove the duplication by only using plugin defaults.
- Test coverage: Tests verify that each plugin returns valid defaults, but no test asserts consistency between `TECHNIQUE_DEFAULTS` and plugin defaults.

**Template Context Assumptions:**
- Files: `envelope/generators/templates/*.j2`, `envelope/frameworks/base.py:40-49`, adapter `template_context()` overrides
- Why fragile: Templates assume specific context variables (e.g., `config`, `technique_args`, `hparam_defaults`). The base `template_context()` provides these, but adapters can override the context. If a template expects a variable that an adapter does not provide, it will fail at generation time (caught by `jinja2.StrictUndefined` but only at runtime).
- Safe modification: When adding new templates, verify all context variables are provided by the adapter's `template_context()`. Add integration tests for each new template.
- Test coverage: Only GRPO+TRL and SFT+TRL templates are tested end-to-end. Most other templates are untested.

## Scaling Limits

**GPU Database Is Hardcoded:**
- Current capacity: 12 GPU types in `GPU_DATABASE` (`envelope/hardware/gpu_specs.py:19-32`).
- Limit: Any GPU not in the database returns `None` from `get_gpu_spec()`, causing the auto-optimizer to skip all suggestions.
- Scaling path: Add more GPU types (B100, B200, MI300X, etc.) or implement a dynamic lookup via `torch.cuda.get_device_properties()` at generation time for from_scratch setups.

**All Techniques Are Eagerly Imported:**
- Current capacity: 19 techniques, 8 frameworks -- all imported on every `discover_plugins()` call.
- Limit: As the number of techniques and frameworks grows, import time increases linearly.
- Scaling path: Use lazy imports or entry points (`importlib.metadata`) for plugin discovery instead of explicit imports.

## Dependencies at Risk

**No Pin on Major Versions:**
- Risk: `pyproject.toml` specifies minimum versions only (`pydantic>=2.0`, `jinja2>=3.1`, etc.). A breaking change in any dependency could silently break the tool.
- Impact: Pydantic v3 (if released) could break all models. A Jinja2 update could change template rendering behavior.
- Migration plan: Add upper bounds or pin to major versions (e.g., `pydantic>=2.0,<3.0`). Use `uv.lock` (already present) for reproducible installs.

## Missing Critical Features

**No Evaluation/Validation Split Support in Generated Scripts:**
- Problem: The config has `dataset.eval_uri` and `dataset.split_eval`, but most generated templates do not implement evaluation during training. No template references `eval_uri`.
- Blocks: Users cannot monitor validation loss during training without manually editing generated scripts.

**No `HPARAM_*` Override in from_scratch Trainer:**
- Problem: The `BaseFromScratchTrainer` in `envelope/frameworks/from_scratch/lib/base_trainer.py` uses a `TrainerConfig` dataclass that is set at instantiation. The `resolve_hyperparams()` utility in `envelope/generators/shared_utils.py` handles env var overrides, but it is only referenced in Jinja2 templates -- the from_scratch `base_trainer.py` does not call it.
- Files: `envelope/frameworks/from_scratch/lib/base_trainer.py`, `envelope/generators/shared_utils.py`
- Blocks: `HPARAM_*` env var overrides work for TRL/Unsloth templates but not for from_scratch setups unless the generated `train.py` template explicitly calls `resolve_hyperparams()`.

## Test Coverage Gaps

**No Tests for from_scratch Trainers:**
- What's not tested: The entire `envelope/frameworks/from_scratch/lib/` directory (587-line `base_trainer.py`, 244-line `rl_trainer.py`, 165-line `preference_trainer.py`, 73-line `sft_trainer.py`, plus all 14 technique implementations in `lib/techniques/`).
- Files: `envelope/frameworks/from_scratch/lib/base_trainer.py`, `envelope/frameworks/from_scratch/lib/rl_trainer.py`, `envelope/frameworks/from_scratch/lib/preference_trainer.py`, `envelope/frameworks/from_scratch/lib/sft_trainer.py`, `envelope/frameworks/from_scratch/lib/techniques/*.py`
- Risk: The from_scratch trainer is the most complex code in the project with full training loops, FSDP wrapping, gradient accumulation, and checkpoint management -- all completely untested.
- Priority: High -- this is the highest-risk untested area.

**No Tests for Jinja2 Template Rendering Beyond TRL+GRPO and TRL+SFT:**
- What's not tested: Template rendering for DPO, GKD, SDFT, SDPO, GOLD, reward_modeling (TRL), DPO (Unsloth), PPO (OpenRLHF/veRL), from_scratch, and all YAML-generating templates (Axolotl, Torchtune, LlamaFactory).
- Files: `envelope/generators/templates/*.j2`
- Risk: Templates may reference undefined context variables, produce syntactically invalid Python/YAML, or contain logic errors.
- Priority: Medium -- integration tests for each template are needed.

**No Tests for `shared_utils.resolve_hyperparams()`:**
- What's not tested: The `HPARAM_*` environment variable override logic.
- Files: `envelope/generators/shared_utils.py`
- Risk: Type coercion for booleans, integers, and floats via env vars is untested.
- Priority: Medium -- this is a user-facing feature.

**No Tests for `hardware/auto_optimizer.py`:**
- What's not tested: Hardware-aware optimization suggestions.
- Files: `envelope/hardware/auto_optimizer.py`
- Risk: The model memory estimation heuristic (`estimate_model_memory_gb`) and optimization suggestion logic are untested.
- Priority: Medium.

**No Tests for CLI Commands:**
- What's not tested: All Click CLI commands (`envelope setup`, `envelope validate`, `envelope techniques`, `envelope frameworks`, `envelope compatible`).
- Files: `envelope/cli.py`
- Risk: CLI regressions would go unnoticed. The CLI is the primary user interface.
- Priority: Medium.

**No Tests for Triton Kernel Registry:**
- What's not tested: The Triton kernel registry, kernel implementations (cross-entropy, RMS norm, softmax), and their integration with the from_scratch framework.
- Files: `envelope/frameworks/from_scratch/lib/kernels/*.py`
- Risk: Triton kernels could produce incorrect results or fail to load, with no test coverage to catch regressions.
- Priority: Low -- only affects from_scratch users who opt into Triton kernels.

---

*Concerns audit: 2026-04-10*
