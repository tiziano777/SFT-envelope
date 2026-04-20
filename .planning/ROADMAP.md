# ROADMAP: FineTuning-Envelope Recovery

**Updated**: 2026-04-20
**Milestone**: Recovery v0.1
**Total Phases**: 4 + Archive

---

## Phase 1: Audit & Cleanup (Foundational)

**Goal**: Stabilize codebase, fix tooling, identify real dead code

**User Stories**:
1. Generate requirements.txt from live codebase imports → R-BUILD-1
2. Audit "dead code" report, classify plugins vs. garbage → R-QA-1
3. Create Makefile (install, test, lint, clean) → R-BUILD-2
4. Fix .gitignore for cache/output/venv → R-BUILD-3
5. Verify CLI works: all subcommands execute → implicit

**Acceptance**:
- `make install` succeeds
- `make test` runs (may fail — OK, documents gaps)
- `make lint` passes or lists non-blocking issues
- requirements.txt pins correctly
- Dead code report reviewed + false positives removed

**Depends**: (none — starting phase)

**Estimate**: 2–3 hours (caveman)

---

## Phase 2: Scaffold Standardization (Core)

**Goal**: Generate complete, runnable experiment folders

**User Stories**:
1. Create train.py template → R-SCAFFOLD-1
2. Create prepare.py template → R-SCAFFOLD-2
3. Ensure config.yml is 100% source of truth → R-SCAFFOLD-3
4. Standardize modules/ structure → R-SCAFFOLD-4
5. Update setup_generator to produce standard file list → R-SCAFFOLD-5
6. Test: generate setup for SFT + TRL, verify file list

**Acceptance**:
- `envelope setup --name test_sft --config examples/sft_config.yml` produces setup_test_sft/
- Setup folder contains: requirements.txt, config.yml (copy), train.py, prepare.py, run.sh, modules/, .cache/ (if prepare ran)
- `bash setup_test_sft/run.sh` executes without errors (may not train fully, OK — just verify script structure)
- config.yml read correctly, no hardcoded values in train.py

**Depends**: Phase 1 ✓

**Estimate**: 3–4 hours (caveman)

---

## Phase 3: SkyPilot Integration (Infrastructure)

**Goal**: Auto-provision cloud HW if requested

**User Stories**:
1. Replace auto_optimizer hardcoded logic with sky.yaml generator → R-HW-1
2. Add cloud provider cost/availability suggestions → R-HW-2
3. Integrate SkyPilot (optional dep — graceful fallback)
4. Document hardware config workflow
5. Test: generate sky.yaml for A100 × 4 setup

**Acceptance**:
- `envelope validate --config cfg.yml --remote` suggests HW + generates sky.yaml
- `sky launch sky.yaml` works (if SkyPilot available)
- Fallback: if SkyPilot not installed, suggests config but doesn't fail
- Config HW section fully respected (GPU type, count, CPU per GPU, etc)

**Depends**: Phase 2 ✓

**Estimate**: 2–3 hours (caveman)

---

## Phase 4: Docs & Complexity Reduction (Polish)

**Goal**: Clean documentation, assess simplification opportunities

**User Stories**:
1. Create/update workflow.md (end-to-end process) → R-DOC-1
2. Auto-generate README.md in each setup folder → R-DOC-2
3. Update root README → R-DOC-3
4. Audit from_scratch/ framework usage → R-SIMPLIFY-1
5. Config validation test coverage audit → R-QA-3
6. Final integration test: full pipeline SFT+TRL → setup → execute snippet

**Acceptance**:
- workflow.md complete (all config fields documented)
- Generated setup folder includes README with instructions
- from_scratch/ assessment documented (decision: keep/deprecate/remove)
- Linting + tests still pass
- Example workflow runs end-to-end (or documents why not)

**Depends**: Phase 3 ✓

**Estimate**: 2–3 hours (caveman)

---

## Archive: Completed Recovery

**Goal**: Finalize recovery, prepare for v0.1 release

**Tasks**:
- [ ] All phases execute
- [ ] All tests pass (pytest + ruff)
- [ ] Git log clean (1 commit per phase + follow-ups)
- [ ] README + workflow.md finalized
- [ ] Tag v0.1-recovery in git
- [ ] Update PROJECT.md with completion date

---

## Summary Table

| Phase | Goal | Key Deliverable | Duration | Depends On |
|-------|------|---|---|---|
| 1 | Foundational | requirements.txt, Makefile, .gitignore | 2–3h | — |
| 2 | Core | train.py, prepare.py templates, setup folder structure | 3–4h | Ph1 |
| 3 | Infra | SkyPilot integration, HW provisioning | 2–3h | Ph2 |
| 4 | Polish | workflow.md, docs, complexity audit | 2–3h | Ph3 |
| Archive | Release | v0.1-recovery tag | — | Ph4 |

**Total: ~10–13 hours (caveman mode, parallel where possible)**

