---
phase: 02-database-layer
plan: "02a"
slug: "repository-implementation-crud"
type: execute
wave: 2
depends_on:
  - "01"
  - "02-01"
files_modified:
  - master/neo4j/repository.py
  - tests/lineage/test_repository_impl.py
autonomous: true
requirements:
  - DB-05
  - DB-06
  - DB-07
must_haves:
  truths:
    - "ExperimentRepositoryAsync implements BaseExperimentRepository ABC"
    - "create_experiment uses MERGE for idempotency"
    - "upsert_checkpoint performs atomic transaction"
    - "find_experiment_by_hashes queries all 3 hash fields"
    - "get_latest_checkpoint returns max epoch"
created: 2026-04-13
tdd_pattern: true
---

# Phase 2-02a: Repository CRUD Implementation

## Plan Goal
Implement ExperimentRepositoryAsync with idempotent CRUD operations and async/await patterns.

## Tasks

### T01-T04: Repository Methods
- create_experiment (MERGE-based idempotency)
- upsert_checkpoint (atomic transaction)
- find_experiment_by_hashes (query all 3)
- get_latest_checkpoint (order DESC)

**Done:** ✓ All 4 methods implemented and tested

## Verification
```bash
pytest tests/lineage/test_repository_impl.py -xvs
```
