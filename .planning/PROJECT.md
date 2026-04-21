# FineTuning Envelope — Project Context

## Project Summary

**Envelope** is a zero-config setup generator for reproducible LLM fine-tuning experiments. Reads a YAML config specifying model, technique, dataset, and hardware → generates a self-contained `setup_NAME/` directory with all code + dependencies to run training.

**Status**: v0.1 stable (19 techniques, 8 frameworks). v0.2 in recovery (post-export refactor).

---

## v0.1 Timeline (completed)

| Date | Milestone | Notes |
|------|-----------|-------|
| 2025-Q4 | Initial design | 19 techniques (SFT, DPO, RL, etc), 8 frameworks (TRL, Unsloth, Axolotl, ...) |
| 2026-02 | Framework matrix | Capability matrix, compatibility checks |
| 2026-03 | Setup generator | Jinja2 templates, config loader, generate setup_*/ |
| 2026-04 | Export to single repo | Codebase extracted from monorepo, lost some integration |

---

## v0.2 Goals

**Recovery & Refactor** — restore functionality post-export, simplify via KISS.

### Guiding Principles

1. **KISS (Keep It Simple, Stupid)**
   - No feature creep. Scaffold generation must be minimal but complete.
   - No speculative abstractions. One responsibility per class.
   - Dead code audit + cleanup (but preserve working plugins).

2. **Single Source of Truth**
   - Config.yml contains ALL hyperparameters, dataset specs, HW config.
   - No runtime discovery, no "fallback" merging in Python code.
   - Framework adapters read from config, don't patch it.

3. **Leave Working Code Alone**
   - Registry system, base classes, simple adapters → no changes.
   - Only refactor obviously overcomplicated flows.
   - Confirm before deleting anything.

4. **Reproducibility**
   - Generated setups must work end-to-end (prepare → train).
   - Config.yml = provenance. Pin all deps. Cache data.
   - No hidden dependencies or machine-specific logic.

---

## v0.2 Structure

**4 Phases** (fast-track refactor):

1. **Phase 1**: Make Scaffold Foundation
   - Fix Makefile, requirements.txt, pyproject.toml
   - Test setup generation end-to-end
   - Verify templates render correctly

2. **Phase 2**: Config Resolution Refactor
   - Remove redundant config merging (`resolve_hyperparams()`)
   - Consolidate recipe/dataset config (one source, not two)
   - Verify config.yml as single source of truth

3. **Phase 3**: Complexity Audit & Simplification (KISS)
   - Identify overcomplicated classes/flows
   - Simplify (split, consolidate, remove)
   - Dead code + false positive audit

4. **Phase 4**: Validation & Cleanup
   - Test 3 real scaffolds (sft, dpo, grpo)
   - Verify prepare.py + train.py work
   - Update documentation, atomic commits

---

## Architecture (v0.1 stable)

### Core Layers

| Layer | Purpose | Key Files |
|-------|---------|-----------|
| **Config** | YAML parsing, Pydantic models | `config/models.py`, `config/loader.py` |
| **Registry** | Plugin system (techniques, frameworks) | `registry/base.py`, decorators |
| **Techniques** | 19 training methods | `techniques/sft/`, `techniques/rl/`, etc. |
| **Frameworks** | 8 backend adapters | `frameworks/single_node/`, `frameworks/multi_node/` |
| **Generation** | Template rendering, scaffold creation | `generators/setup_generator.py` |
| **Prepare** | Dataset loading, caching | `prepare/datamix_loader.py` |

### Communities (11 detected)

1. **frameworks** — all backend adapters + capability matrix
2. **rl-technique** — RL-specific techniques (GRPO, PPO, etc.)
3. **config-config** — Pydantic models, schema, validation
4. **diagnostics** — runtime logging (TRL callback injection)
5. **from_scratch** — PyTorch raw implementation (kernels, trainers)
6. **prepare** — data loading, caching
7. **sft** — supervised fine-tuning
8. **preference** — preference optimization (DPO, KTO, etc.)
9. **distillation** — model distillation (GKD, etc.)
10. **merge** — model merging
11. **reward** — reward modeling

---

## Known Issues (v0.1 → v0.2)

### Issue 1: Export Broke Integration
- Makefile missing
- requirements.txt empty (deps in pyproject.toml)
- setup_generator not wired to CLI
- Templates possibly missing/untested

### Issue 2: Redundant Config
- Recipe/dataset config in BOTH: `config/models.py` AND `prepare/datamix_loader.py`
- Hyperparameters resolved at runtime via `shared_utils.py:resolve_hyperparams()`
- Should be: single config.yml file, schema validation, no runtime merging

### Issue 3: Dead Code
- 218 symbols flagged as unused
- FALSE POSITIVES: 95% are plugins/enums used via dynamic registration
- TRUE DEAD: diagnostics callback, some prepare/ functions

### Issue 4: Complexity Creep
- Some adapters over-engineered (>100 lines, multiple responsibilities)
- Diagnostics auto-injected (should be optional)
- No clear separation between "generator config" and "runtime config"

---

## Dependencies (external)

```toml
python = "^3.10"
pydantic = "^2.0"
click = "^8.0"
rich = "^13.0"
jinja2 = "^3.0"
pyyaml = "^6.0"
transformers = "^4.40"
torch = "^2.1"
```

---

## Team & Scope

- **Owner**: T. Finizzi
- **Team**: Solo (AI-assisted)
- **Duration**: < 2 weeks
- **Focus**: Quality refactor, not feature additions

---

## Versioning

- **v0.1**: Stable. 19 techniques, 8 frameworks.
- **v0.2**: Recovery & KISS simplification (this milestone).
- **v0.3**: SkyPilot HW optimization (planned, post-v0.2).

---

## References

- **Workflow**: `workflow.md` (step-by-step usage guide)
- **CLAUDE.md**: Project conventions (KISS, TDD, modularity)
- **Docs**: `docs/architecture.md`, `docs/config.md`, `docs/techniques.md`, `docs/frameworks.md`

