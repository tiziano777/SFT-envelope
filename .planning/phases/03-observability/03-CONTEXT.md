# Phase 3: Observability — Context & Implementation Decisions

## Phase Boundary

**What We Deliver:**
- Production-ready tracing infrastructure for Master API
- Phoenix UI (Docker Compose service) receiving traces from Master via OTEL gRPC
- All Master API requests traced automatically (FastAPI middleware)
- Manual spans on critical endpoints (handshake, checkpoint_push, status_update, merge, sync_event)
- Graceful degradation when Phoenix is unreachable (no crash, no hang, no error logs to user)

**What We DO NOT Deliver:**
- Worker daemon tracing (Phase 6)
- Custom trace export backends (only OTEL gRPC to Phoenix)
- Trace persistence layer (that's observability infrastructure, not our scope)
- Dashboard customization in Phoenix

**Tech Stack:**
- OpenTelemetry Python (otel-api, otel-sdk)
- OpenTelemetry FastAPI Instrumentation (`opentelemetry-instrumentation-fastapi`)
- OTEL gRPC exporter (`opentelemetry-exporter-trace-otlp-proto-grpc`)
- Phoenix (via Docker Compose on port 4317 for gRPC, 6006 for UI)

---

## Implementation Decisions

### D-01: Tracing Setup Pattern — Module-Level Singleton

**Decision:** Module-level singleton function `setup_tracing()` called once at `master/api.py` startup, not per-request.

**Why:**
- OTEL exporters are stateful (maintain gRPC connections, batch buffers)
- Per-request setup would create resource leaks
- Singleton pattern follows OTEL best practices

**Implementation:**
```python
# master/observability/tracing.py
_tracer_provider: Optional[TracerProvider] = None
_tracer: Optional[Tracer] = None

def setup_tracing(service_name: str = "master-api",
                  phoenix_endpoint: str = "http://localhost:4317") -> None:
    """
    Initialize global tracer. Call once at startup.

    Fails silently (logs warning, returns) if Phoenix unreachable.
    """
    global _tracer_provider, _tracer
    ...

def get_tracer() -> Tracer:
    """Return global tracer. Raises if setup_tracing() not called."""
    ...
```

---

### D-02: Span Naming Convention — service.operation.step

**Decision:** Spans use dotted hierarchy: `master.api.handshake`, `master.api.checkpoint_push.validate`, `master.api.checkpoint_push.save`

**Why:**
- Mirrors hierarchical trace views in Phoenix UI
- Matches OTEL semantic conventions (service.operation hierarchy)
- Enables fine-grained filtering/grouping in queries

**Examples:**
- Auto-instrumented (FastAPI middleware): `master.api.POST /handshake`
- Manual spans on handshake: `master.api.handshake.lookup_experiment`, `master.api.handshake.determine_strategy`
- Manual spans on checkpoint_push: `master.api.checkpoint_push.validate`, `master.api.checkpoint_push.persist_to_neo4j`

---

### D-03: Error Handling — Graceful Degradation, No Propagation

**Decision:**
- `setup_tracing()` catches ALL exceptions (socket errors, auth errors, timeouts) and logs warning (not error)
- Returns normally (does not raise)
- Sets fallback no-op tracer if initialization fails
- Individual `with tracer.start_as_current_span()` blocks do NOT raise; they swallow exceptions

**Why:**
- OBSV-02 requirement: "succeeds silently when Phoenix is unreachable"
- Tracing must NEVER block training or API requests
- User should never see "ConnectionRefusedError" in logs

**Implementation:**
```python
def setup_tracing(...) -> None:
    try:
        # Initialize tracer...
        _tracer = ...
    except Exception as e:
        # Log WARNING (not ERROR), use no-op fallback
        logger.warning(f"Tracing init failed: {e}. Using no-op tracer.")
        _tracer = NoOpTracer()  # OTEL built-in
        return

def get_tracer() -> Tracer:
    global _tracer
    if _tracer is None:
        # Someone forgot to call setup_tracing(), return no-op
        return NoOpTracer()
    return _tracer
```

---

### D-04: FastAPI Auto-Instrumentation — No Double-Instrumentation

**Decision:**
- Call `FastAPIInstrumentor.instrument_app(app)` EXACTLY ONCE after creating FastAPI instance
- Do NOT call it in middleware initialization or on every request
- Use `skip_paths` to exclude health checks, metrics endpoints if needed

**Why:**
- Double-instrumentation creates duplicate spans and overhead
- FastAPI instrumentation hooks directly into starlette middleware chain
- OTEL design expects single initialization

**Implementation:**
```python
# master/api.py
app = FastAPI()
setup_tracing()  # Initialize global tracer

FastAPIInstrumentor.instrument_app(app)  # Hook ONCE

@app.post("/handshake")
async def handshake(req: HandshakeRequest):
    # Middleware already creates outer span "POST /handshake"
    # Our manual span code adds inner span "master.api.handshake.lookup_experiment"
    ...
```

---

### D-05: Manual Spans on Critical Endpoints

**Decision:**
- Five endpoints get explicit `with get_tracer().start_as_current_span()` blocks:
  1. POST /handshake — lookup_experiment, determine_strategy substeps
  2. POST /checkpoint_push — validate, persist_to_neo4j, artifacts substeps
  3. POST /status_update — validate, upsert_checkpoint substeps
  4. POST /merge — validate, retrieve_source, merge_lineage, persist substeps
  5. POST /sync_event — validate, process_event, upsert_data substeps

- Each span includes: `attributes` dict with context (exp_id, recipe_id, etc.), `events` for checkpoints, `set_attribute()` calls for dynamic values

**Why:**
- OBSV-05 requirement: "Manual spans on critical endpoints"
- Gives visibility into request processing stages
- Attributes enable tracing/filtering by experiment ID, recipe, user, etc.

**Implementation:**
```python
with get_tracer().start_as_current_span("master.api.handshake.lookup_experiment") as span:
    span.set_attribute("recipe_id", req.recipe_id)
    span.set_attribute("exp_id", req.exp_id or "new")
    exp = await db.find_experiment_by_hashes(...)
    span.add_event("experiment_found", {"source": exp.created_from or "new"})
```

---

### D-06: Testing Strategy — Mock Phoenix, Real Docker in Integration Tests

**Decision:**
- Unit tests: Mock OTEL exporter, verify span creation logic (no Docker needed)
- Integration tests: Real `docker-compose` with Phoenix service, verify end-to-end trace flow

**Why:**
- Unit tests run fast (no Docker spin-up)
- Integration tests catch real transport/serialization issues
- Docker fixtures via `pytest-docker` or custom conftest

**Test Layers:**
- Unit: `test_tracing.py` — mock exporter, verify setup succeeds/fails gracefully
- Unit: `test_api_instrumentation.py` — verify FastAPI middleware attached, no double-instrumentation
- Unit: `test_manual_spans.py` — verify span attributes, nesting
- Integration: `test_tracing_e2e.py` — real Phoenix container, verify traces appear

---

## Canonical References

- **OTEL Python docs:** https://opentelemetry.io/docs/instrumentation/python/
- **OTEL FastAPI instrumentation:** https://opentelemetry-instrumentation-fastapi.readthedocs.io/
- **OTEL Semantic Conventions:** https://opentelemetry.io/docs/reference/specification/trace/semantic_conventions/
- **Phoenix docs:** https://docs.arize.com/phoenix/
- **Graceful degradation pattern:** https://opentelemetry.io/docs/instrumentation/python/manual/#handling-errors

---

## Key Constraints & Risks

| Constraint | Handling |
|-----------|----------|
| Phoenix may not be running | setup_tracing() catches all exceptions, returns normally |
| Network timeout (Phoenix unreachable) | OTEL gRPC exporter has configurable timeout (default 10s), wrapped in try/catch |
| Double-instrumentation regression | Code review catches; tests verify single middleware attachment |
| Tracer not initialized | get_tracer() returns no-op fallback, safe to call anytime |
| Span overhead | OTEL sampling can be configured post-deployment; tracing OFF by default for tests |

---

## Phase Success Criteria

All 5 OBSV requirements met + all tests passing:

1. **OBSV-01**: Phoenix UI accessible on localhost:6006, shows traces from Master API
2. **OBSV-02**: setup_tracing() returns normally when Phoenix unreachable (no crash, no hang)
3. **OBSV-03**: get_tracer() returns functional tracer when OTEL available, no-op fallback otherwise
4. **OBSV-04**: FastAPI auto-instrumentation active without double-instrumentation
5. **OBSV-05**: Manual spans exist on handshake, checkpoint_push, status_update, merge, sync_event

---

## Coordination Notes

- Phase 3 runs in parallel with Phase 2 (Database) and Phase 5 (Storage)
- Phase 4 (Master API) depends on this phase — must complete Phase 3 setup before wiring endpoints
- No direct dependency on Phase 2 (database) — tracing is orthogonal to data layer
