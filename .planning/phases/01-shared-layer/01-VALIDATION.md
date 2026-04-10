---
phase: 1
slug: shared-layer
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-10
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `python -m pytest tests/unit/test_nodes.py tests/unit/test_relations.py tests/unit/test_envelopes.py tests/unit/test_config_hasher.py tests/unit/test_diff_engine.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command (phase test files)
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-T1 | 01 | 1 | SHRD-01 | — | N/A | unit | `pytest tests/unit/test_nodes.py -x -q` | ❌ W0 | ⬜ pending |
| 01-01-T2 | 01 | 1 | SHRD-02, SHRD-03, SHRD-04, SHRD-05 | — | N/A | unit | `pytest tests/unit/test_relations.py tests/unit/test_envelopes.py -x -q` | ❌ W0 | ⬜ pending |
| 01-02-T1 | 02 | 2 | SHRD-06, SHRD-07, SHRD-09 | — | N/A | unit | `pytest tests/unit/test_config_hasher.py -x -q` | ❌ W0 | ⬜ pending |
| 01-02-T2 | 02 | 2 | SHRD-08, SHRD-09 | — | N/A | unit | `pytest tests/unit/test_diff_engine.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_nodes.py` — stubs for SHRD-01 (created by Plan 01 T1)
- [ ] `tests/unit/test_relations.py` — stubs for SHRD-02, SHRD-03 (created by Plan 01 T2)
- [ ] `tests/unit/test_envelopes.py` — stubs for SHRD-04, SHRD-05 (created by Plan 01 T2)
- [ ] `tests/unit/test_config_hasher.py` — stubs for SHRD-06, SHRD-07, SHRD-09 (created by Plan 02 T1)
- [ ] `tests/unit/test_diff_engine.py` — stubs for SHRD-08, SHRD-09 (created by Plan 02 T2)
- [ ] No new framework install needed — pytest already in dev dependencies

*Test files created inline by TDD tasks within each plan.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-10
