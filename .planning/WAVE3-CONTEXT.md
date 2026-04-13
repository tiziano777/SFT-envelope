# Wave 3 Execution Context

**Phases:** 6 (Worker Layer) + 8 (Datamix) executing in parallel

---

## Phase 6: Worker Layer Decisions

### Architecture Decisions (Locked)

1. **Daemon Bootstrap Pattern**
   - Blocking handshake on startup (asyncio.wait_for with timeout)
   - Async/await throughout (no threading for daemon)
   - Atomic state persistence: tmp + rename (no partial files)
   - Fallback to degraded mode on timeout (no crash)

2. **Connection Layer**
   - BaseConnection ABC with send_metadata() + transfer_file()
   - HTTPConnection primary implementation (async httpx)
   - SSHConnection stubs (NotImplementedError for Phase 7)

3. **Event Pushing**
   - watchdog library for filesystem monitoring
   - asyncio.Queue for thread-safe deduplication
   - Exponential backoff retry (configurable intervals)
   - transfer_log.jsonl as append-only audit trail

### Implementation Order

1. **06-01:** Core daemon + state → prerequisite for 06-02 and 06-03
2. **06-02:** Connections → used by pusher in 06-03
3. **06-03:** Async pushing → final orchestration

### Dependencies

- Phase 1 ✓ (shared models, enums, transport)
- Phase 5 ✓ (storage interface, URIResolver)
- External: httpx, watchdog, aiofiles, paramiko (defer)

---

## Phase 8: Datamix Decisions

### Architecture Decisions (Locked)

1. **Config Model Extension**
   - Add DatamixSource and DatamixConfig to existing models.py
   - EnvelopeConfig supports both dataset (backward compat) and datamix
   - has_datamix and has_single_dataset helper properties

2. **Loader Pattern**
   - DatamixLoader detects mode (datamix vs single dataset)
   - _load_single_dataset() for backward compat
   - _load_datamix() loads + combines sources with oversampling
   - Replica field: N× repetition in final dataset

3. **Backward Compatibility**
   - Existing configs with single dataset field: no changes
   - New configs can use datamix section
   - Error only on missing both fields

### Implementation

Single plan: 08-01
- Extend envelope/config/models.py
- Create envelope/prepare/datamix_loader.py
- Integrate into prepare.py workflow
- 7 tests for validation + backward compat

### Dependencies

- Phase 1 ✓ (Pydantic models, ConfigSnapshot)
- External: pandas, s3fs (optional)

---

## Test Coverage

**Phase 6** (~20 tests across 3 files)
- test_daemon.py: 6 tests (bootstrap, timeout, state persistence)
- test_connections.py: 7 tests (HTTP metadata, file transfer, health)
- test_pusher.py: 4+ tests (dedup, retry, backoff, flush)
- test_watcher.py: implied (watchdog integration)

**Phase 8** (7 tests)
- test_datamix.py: backward compat, multi-source, replica, error handling

---

## File Structure After Execution

```
envelope/
├── config/
│   ├── models.py (+ DatamixSource, DatamixConfig, dataset+datamix fields)
│   └── ...
├── middleware/
│   ├── __init__.py
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── models.py (WorkerState, TransferLogEntry)
│   │   ├── connection.py (BaseConnection ABC)
│   │   ├── state.py (AtomicStateManager)
│   │   └── ...
│   └── worker/
│       ├── __init__.py
│       ├── daemon.py (WorkerDaemon)
│       ├── http_connection.py (HTTPConnection)
│       ├── ssh_connection.py (SSHConnection stubs)
│       ├── watcher.py (WorkerWatcher)
│       ├── pusher.py (AsyncPusher)
│       └── worker.py (Worker orchestration)
└── prepare/
    ├── datamix_loader.py (DatamixLoader)
    └── prepare.py (+ integrate DatamixLoader)

tests/
├── worker/
│   ├── test_daemon.py
│   ├── test_connections.py
│   ├── test_pusher.py
│   └── test_watcher.py (optional)
└── config/
    └── test_datamix.py
```

---

## Execution Notes

- **No manual database changes** (Neo4j schema finalized in Phase 2)
- **No generator changes yet** (Phase 7 handles inject_worker_middleware)
- **Tests are runnable** after each plan (pytest envelope/middleware, tests/config)
- **Atomic commits** after each plan succeeds
- **Backward compat verified** before moving to Phase 7

---

## Wave 3 Success Criteria

- [ ] Phase 6: All 3 plans executed, 20+ tests passing
- [ ] Phase 8: Plan executed, 7 tests passing, backward compat confirmed
- [ ] ROADMAP.md updated: 6/3 plans, 8/1 plans
- [ ] All commits atomic with descriptive messages
- [ ] Ready for Wave 4 (Phase 7: Generator Integration)
