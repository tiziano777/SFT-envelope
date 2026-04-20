# v0.2 Recovery Roadmap

**Goal**: Fix broken scaffold generator post-export. Simplify via KISS. Make `make setup` work end-to-end.

**Timeline**: < 2 weeks, iterative. Quality > perfection.

---

## Phase 1: Make Scaffold Foundation
**Depends**: None
**Goal**: Fix `make setup NAME=X CONFIG=Y` to generate functioning scaffold
**Status**: ✅ COMPLETE (45 min)
**Plans**: 1 plan
- [x] 01-01-PLAN.md — Populate requirements.txt, create example configs, write E2E tests, verify Makefile

**Scope**:
- Fix/create Makefile with `setup`, `validate`, `test-scaffold` targets
- Audit `pyproject.toml` dependencies (pin versions, verify completeness)
- Fix empty `requirements.txt` → consolidate all deps
- Verify `setup_generator.py` orchestration logic works with templates
- Test: Generate 1 real setup_grpo-test/, inspect all generated files

**UAT**:
- [x] `make setup NAME=grpo-test CONFIG=examples/grpo_qlora_qwen.yaml` succeeds
- [x] setup_grpo-test/ contains: prepare.py, train.py, config.yaml, requirements.txt, modules/
- [x] All files syntactically valid Python/YAML
- [x] CLI commands work: `envelope setup`, `envelope validate`, `envelope compatible`

**Artifacts**: requirements.txt (6 pinned deps), configs/examples/{sft_baseline.yaml, grpo_qlora_qwen.yaml}, tests/test_setup_generator.py

---

## Phase 2: Config Resolution Refactor (YAML-only)
**Depends**: Phase 1
**Goal**: Kill redundant merging. Hyperparams live in config.yml only, not Python code.
**Status**: 📋 PLANNED (7 tasks across 3 waves)
**Plans**: 1 plan
- [ ] 02-01-PLAN.md — Move defaults to schema, consolidate recipe, unify resolve_hyperparams, make diagnostics optional, generate complete config.yaml

**Scope**:
- Move hyperparameter defaults from loader injection → Pydantic Field defaults
- Consolidate recipe schema (RecipeConfig as canonical, remove DatamixConfig duplication)
- Unify resolve_hyperparams() — remove template duplication, single implementation in shared_utils
- Add diagnostics field to EnvelopeConfig (optional, configurable in YAML)
- Remove merge_technique_defaults() load-time injection
- Generate complete config.yaml with exclude_defaults=False
- Integration tests: verify config completeness + regenerability

**Wave Structure**:
- **Wave 1** (2 tasks): Schema consolidation (Field defaults, recipe schema)
- **Wave 2** (3 tasks): Unification (remove injection, add diagnostics, unify resolve_hyperparams)
- **Wave 3** (2 tasks): Generation + verification (complete config.yaml, integration tests)

**UAT**:
- [ ] Generated config.yaml contains ALL fields (hparam_overrides, technique_args, diagnostics)
- [ ] Regenerating from generated config.yaml produces identical file (reproducible)
- [ ] resolve_hyperparams() exists only in shared_utils.py (removed from templates)
- [ ] RecipeConfig is canonical; no DatamixConfig duplication
- [ ] Diagnostics optional + configurable in config.yaml
- [ ] Phase 1 tests still pass (no breaking changes to scaffold generation)
- [ ] pytest tests/test_config_resolution.py -v (all green)

**Risk Mitigation**:
- Backward compat: hparam_overrides and diagnostics have sensible defaults
- Recipe consolidation: use aliases if needed to prevent import breaks
- Regeneration test catches any issues with incomplete config.yaml

---

## Phase 3: Complexity Audit & Simplification (KISS)
**Depends**: Phase 2
**Goal**: Reduce overcomplicated flows. Keep simple + reliable code untouched.
**Status**: ⏳ PENDING Phase 2
**Scope**:
- List all "overcomplicated" classes (>50 lines, multiple responsibilities): adapters with custom framework logic, recipe loaders, diagnostics
- For each: decide KEEP (working), REFACTOR (simplify), REMOVE (dead)
- Remove duplicate recipe/dataset resolution (model.py + prepare/ redundancy)
- Simplify diagnostics injection — TRLDiagnosticCallback should be pluggable, not auto-injected
- Verify no-touch zones (registry.py, base.py, simple adapters) unchanged
- Delete truly dead code (enums used via config validation are NOT dead — mark as verified)

**UAT**:
- [ ] No class > 100 lines (consolidate methods or split responsibility)
- [ ] Recipe config defined in ONE place only
- [ ] Diagnostics callback is optional, user-configurable in config.yml
- [ ] All 11 communities in graph have clear, single purpose

**Risks**: Accidental deletion of used code (run tests after each removal)

---

## Phase 4: Validation & Cleanup
**Depends**: Phase 3
**Goal**: Verify scaffold generation end-to-end. Document architecture. Commit polish.
**Status**: ⏳ PENDING Phase 3
**Scope**:
- Full test: Generate 3 real setups (sft, dpo, grpo) with different frameworks (trl, unsloth, openrlhf)
- Verify each setup runs `python prepare.py` + `python train.py --help` without errors
- Update workflow.md to reflect new reality (if config format changed)
- Audit dead code report — confirm all flagged symbols are either plugins or actual dead
- Create simple CLI help: `envelope --help`, `make --help`
- Git commit: atomic commits per phase with clear messages

**UAT**:
- [ ] 3 test scaffolds generated + validate passes
- [ ] `prepare.py` runs without import errors
- [ ] `train.py` loads config, doesn't crash on startup
- [ ] Dead code report cleaned up (mark false positives as verified plugins)
- [ ] Documentation reflects final architecture

**Success Criteria**: `make setup` produces working, minimal setup. No feature creep. KISS maintained.

---

## Excluded / Backlog

- **SkyPilot HW optimization** → v0.3 (depends on v0.2 foundation)
- **New frameworks** → after refactor stabilizes
- **Extended diagnostics** → post-recovery

---

## Git Strategy

- 1 commit per phase (atomic, squashed from micro-commits)
- Tag: `v0.2-recovery-phase-N` after each phase UAT passes
- Branch: `feature/v0.2-recovery` for work, merge to main after Phase 4

---

## Phase Milestones

| Phase | Goal | Tasks | Duration | Status |
|-------|------|-------|----------|--------|
| 1 | Foundation (make setup works) | 4 | ~45min | ✅ DONE |
| 2 | Config refactor (single source of truth) | 7 | ~120min | 📋 PLANNING |
| 3 | Simplify (KISS) | TBD | ~90min | ⏳ PENDING |
| 4 | Validation (E2E) | TBD | ~60min | ⏳ PENDING |
