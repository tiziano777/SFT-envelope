# FineTuning-Envelope: Recovery & Infrastructure

**Status**: Exported codebase → Recovery phase
**Date started**: 2026-04-20
**Goal**: Stabilize + standardize experiment generation system for LLM fine-tuning

---

## Context

### What This Is
FineTuning-Envelope = two-level experiment generator for reproducible LLM fine-tuning setups.
- Level 1: YAML config (`config.yml`) → defines entire experiment
- Level 2: Setup folder (`setup_{name}/`) → self-contained, runnable training environment

### Why Recovery Needed
- Codebase exported as standalone → missing `requirements.txt`, `Makefile`, template scaffolds
- HW optimization hardcoded → needs SkyPilot integration for cloud provisioning
- Prepare/train scripts not templated → scaffold generation incomplete
- Diagnostics/registry working but undocumented

### What Works Now
✓ Plugin system (techniques, frameworks)
✓ Pydantic config schema covering all training modes
✓ Template generation via Jinja2
✓ Cross-field config validation
❌ No shell commands to run training
❌ No cloud provisioning logic
❌ Scaffold templates incomplete

---

## Architecture (Current)

```
envelope/
├── config/          # Pydantic models + YAML loader + validators
├── techniques/      # @registry plugins (SFT, DPO, PPO, etc)
├── frameworks/      # Adapter pattern for TRL, Unsloth, Axolotl, etc
├── hardware/        # GPU specs, auto_optimizer (hardcoded)
├── prepare/         # Data prep (datamix_loader exists, recipe partial)
├── generators/      # setup_generator orchestrates template rendering
├── rewards/         # Custom reward function stubs
├── diagnostics/     # TRL callbacks + runtime monitoring
├── registry/        # Plugin registration system
├── cli.py           # Click CLI (setup, validate, techniques, frameworks)
└── .venv/           # Virtual env (present locally)
```

---

## Success Criteria (Recovery Complete)

1. **Buildability**: `make install && make test` passes
2. **CLI**: `envelope setup --name exp1 --config config.yml` generates working setup folder
3. **Setup scaffold standard**:
   - `requirements.txt` (tech + framework specific)
   - `config.yml` (copy of input, no logic needed)
   - `prepare.py` (loads data per config → .cache/)
   - `train.py` (runs training per config)
   - `modules/` (custom rewards, adapters if needed)
   - `.cache/` + `.env` (ignored)
4. **HW optimization**: Auto-suggest GPU configs via SkyPilot
5. **Docs**: workflow.md explains end-to-end process
6. **Zero runtime hparam resolution**: All hyperparams in config.yml, no env var magic

---

## Gaps vs. Goals

| Gap | Impact | Recovery Phase |
|-----|--------|---|
| No requirements.txt | Can't run envelope CLI | 1: Audit & Fix |
| No Makefile | No standard dev commands | 1: Audit & Fix |
| Incomplete train.py template | Can't execute training | 2: Scaffold Standardization |
| Incomplete prepare.py template | Data never reaches training | 2: Scaffold Standardization |
| auto_optimizer hardcoded | No cloud cost/availability logic | 3: SkyPilot Integration |
| Diagnostics undocumented | Uncertain if TRLCallback injected correctly | 1: Audit & Fix |
| Hyperparams resolved at runtime | Config.yml incomplete, env vars leak logic | 2: Scaffold Standardization |

---

## Recovery Phases (4-phase plan)

### Phase 1: Audit & Cleanup (foundational)
- Identify real dead code vs. @registry plugins
- Generate requirements.txt from graph imports
- Create Makefile (test, lint, install, setup)
- Fix .gitignore (exclude .cache/, output/)

### Phase 2: Scaffold Standardization
- Create train.py template (config-driven, no hardcode)
- Create prepare.py template (recipe → .cache/)
- Document config.yml schema expectations
- Standardize modules/* structure (rewards/, custom adapters)

### Phase 3: SkyPilot Integration
- Replace auto_optimizer with sky.yaml generation
- Add cloud provider cost/availability logic
- Auto-provision infra if --remote flag set
- Document HW config workflow

### Phase 4: Complexity Reduction & Docs
- Audit from_scratch/* framework (likely 80% dead)
- Simplify framework adapters to template-driven
- Update workflow.md with end-to-end process
- Add generated README to setup folders

---

## Constraints
- No external service dependencies (SkyPilot is optional, local-only fallback OK)
- Minimal scaffold — goal is "start point", not "production-ready"
- Config.yml is source of truth; Python is plumbing only
- All plugins (techniques, frameworks) stay — they work, even if "dead" to static analysis

---

## Definition of Done
- [ ] All phases executed
- [ ] `envelope setup` generates working folder for ≥1 technique + framework combo
- [ ] Tests pass (pytest)
- [ ] Linting passes (ruff)
- [ ] README + workflow.md updated
- [ ] Git history clean (atomic commits per phase)
