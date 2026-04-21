# v0.2 Recovery Requirements

**Milestone**: Recovery & Refactor — fix scaffold generation, simplify via KISS

**Version**: v0.2

**Timeframe**: < 2 weeks, iterative

---

## Functional Requirements

### FR1: Make Commands Work
- `make setup NAME=X CONFIG=Y` generates setup_X/ with all required files
- `make validate CONFIG=Y` checks YAML schema without generating
- `make test-scaffold` runs basic unit tests on generator logic
- `make clean` removes all generated setups

### FR2: Scaffold Output Minimal & Complete
Generated scaffold must contain:
- `prepare.py` — loads dataset from config.yml, caches in .cache/
- `train.py` — reads config.yml, imports from modules/, runs training
- `config.yaml` — complete configuration (no runtime discovery)
- `requirements.txt` — pip dependencies for that scaffold only
- `modules/` directory structure (rewards/, hooks/, etc. as needed)

### FR3: Config as Single Source of Truth
- All hyperparameters live in generated config.yml
- No "fallback" logic in Python code (e.g., `resolve_hyperparams()` removed)
- Framework adapters must NOT inject missing config values
- Schema validation catches missing fields before generation

### FR4: No Redundant Configuration
- Recipe/dataset config defined in ONE place (never in model.py AND prepare/)
- Dataset resolution logic centralized (DatamixLoader or single recipe loader)
- Framework-specific overrides live in config.yml, not code

### FR5: Diagnostics Optional & Configurable
- TRLDiagnosticCallback is pluggable (not auto-injected)
- Can be enabled/disabled in config.yml
- User can override with custom callbacks

---

## Quality Requirements

### QR1: Code Simplicity (KISS)
- No class > 100 lines (split or consolidate)
- Each class has single responsibility
- No speculative abstractions ("might be useful later")
- Dead code removed (after confirmation)

### QR2: No-Touch Zones (Reliable Code)
- `registry/` — no changes
- `techniques/base.py` — no changes
- Simple framework adapters — no changes
- Utilities (loaders, validators) — minimal changes only

### QR3: Testability
- Each phase must pass UAT before proceeding
- Generated scaffolds must run `prepare.py` + `python train.py --help` without errors
- Dead code audit must be verified (false positives = plugins)

---

## Non-Functional Requirements

### NFR1: Documentation
- `workflow.md` updated to reflect final architecture
- `docs/config-schema.md` documents generated config.yml structure
- Phase commits include clear rationale

### NFR2: Extensibility
- Adding new techniques requires only plugin registration (no refactoring)
- Adding new frameworks requires subclass + registration (no core changes)
- Config schema can be extended without breaking existing setups

### NFR3: Performance
- Scaffold generation < 1 second
- No unnecessary deep copies or merges
- Config validation runs once at setup time, not per training step

---

## Constraints

### C1: Breaking Changes
- Do NOT modify working, simple modules
- Do NOT change user-visible CLI (unless backward-compat'd)
- Existing plugins must still register (`@registry.register()`)

### C2: Scope Boundaries
- SkyPilot HW optimization → v0.3
- New frameworks → after v0.2 stabilizes
- Extended diagnostics → post-recovery

### C3: Dependencies
- Phase 2 depends on Phase 1 success
- Phase 3 depends on Phase 2 refactor completion
- Phase 4 is final validation + cleanup

---

## Success Criteria

- [ ] `make setup NAME=test CONFIG=examples/sft_baseline.yaml` succeeds
- [ ] Generated setup_test/ has all required files
- [ ] `cd setup_test && python prepare.py` completes without error
- [ ] `cd setup_test && python train.py --help` shows usage
- [ ] No Python file > 100 LOC (single responsibility)
- [ ] Recipe config appears in ONE place (not duplicated)
- [ ] Config.yml is source-of-truth (no runtime discovery)
- [ ] Diagnostics can be toggled in config.yml
- [ ] Dead code audit complete + verified
- [ ] workflow.md accurate
- [ ] 3 test scaffolds (sft, dpo, grpo) working
- [ ] Phase 1-4 completed with atomic commits

---

## Assumptions

- Python 3.10+ available
- Pydantic v2 API unchanged (no dependency updates planned)
- Click CLI framework stable (no migration planned)
- Template language (Jinja2) stable (no changes to rendering)

