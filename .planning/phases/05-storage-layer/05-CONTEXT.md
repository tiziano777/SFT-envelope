# Phase 5: Storage Layer - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement a URI-driven storage abstraction layer that dispatches to pluggable storage backends. Master can persist and retrieve artifacts (checkpoints, metrics, configs) via URIs like `file:///path`, `s3://bucket/key`, `nfs://host/path`. The layer provides:

1. BaseStorageWriter ABC with 4 async methods: read_file, write_file, file_exists, delete_file
2. LocalStorageWriter for file:// URIs
3. S3StorageWriter and NFSStorageWriter stubs (raise NotImplementedError)
4. URIResolver for dispatch based on URI prefix
5. Configuration via .env: STORAGE_BACKENDS as JSON mapping prefix → writer class name

All new code goes into `master/storage/`. No existing files are modified. Depends on Phase 1 data contracts (used in error types).

</domain>

<decisions>
## Implementation Decisions

### Module Layout
- **D-01:** Split `master/storage/` into domain-focused modules: `base.py` (ABC), `local.py` (LocalStorageWriter), `stubs.py` (S3/NFS stubs), `resolver.py` (URIResolver), plus `__init__.py` with re-exports. Rationale: small focused files, matches phase boundaries.

### ABC Pattern
- **D-02:** BaseStorageWriter uses async methods (read_file, write_file, file_exists, delete_file). All methods are coroutines returning proper types (bytes, bool, None). Error hierarchy: StorageError (base), URINotSupported, FileNotFound.

### URI Dispatch
- **D-03:** URIResolver extracts prefix from URI (e.g., `file://` from `file:///tmp/x`), looks up in STORAGE_BACKENDS dict, instantiates the correct writer, delegates operation. Default backends: {`file://`: `LocalStorageWriter`, `s3://`: `S3StorageWriter`, `nfs://`: `NFSStorageWriter`}.

### Configuration
- **D-04:** STORAGE_BACKENDS env var as JSON dict string: `{"file://": "LocalStorageWriter", "s3://": "S3StorageWriter", ...}`. Falls back to default if missing. Parsed once at module init, cached in URIResolver. Rationale: env-driven (not hardcoded), extensible.

### Error Handling
- **D-05:** LocalStorageWriter.read_file raises FileNotFound if file doesn't exist. write_file creates parent directories. delete_file is idempotent (no error if missing). All stubs raise NotImplementedError("S3 storage not yet implemented") with clear message.

### Testing Strategy
- **D-06:** Unit tests for ABC interface contract. Unit tests for LocalStorageWriter with mocked filesystem (tmp dirs). Unit tests for S3/NFS stubs verify NotImplementedError. Integration tests with real file:// URIs and temp directories. Configuration tests verify env var parsing.

### Claude's Discretion
- Exact error messages
- Internal implementation details of LocalStorageWriter (path normalization, permission handling)
- Whether to add path validation/sanitization beyond URI prefix check
- Whether to add async context managers for cleanup

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture Specification
- `LINEAGE_SYSTEM_ARCHITECTURE.md` — Section 5 (Storage Layer) with URI patterns, backend contract, error types
- `master/storage/` — New module (this phase)

### Existing Code Patterns
- `envelope/middleware/shared/` — ABC pattern examples (BaseNode, BaseFrameworkAdapter patterns from Phase 1)
- `envelope/config/models.py` — Pydantic v2 patterns, enum definitions
- `master/neo4j/` — Async patterns, driver initialization (Phase 2 reference)

### Project Conventions
- `.planning/codebase/CONVENTIONS.md` — Naming conventions, import order, code style, async patterns
- CLAUDE.md — Type hints (X | Y syntax), no Union imports, Python 3.10+

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `envelope/config/models.py`: Pydantic v2 patterns (enums, Field constraints)
- `master/neo4j/client.py`: Async driver patterns, singleton pattern (reference for URIResolver caching)
- `envelope/middleware/shared/`: Module structure, `__init__.py` re-export pattern, ABC patterns

### Established Patterns
- Module docstrings required on every .py file
- Type hints: X | Y not Union[X, Y], dict[str, Any] not Dict[str, Any]
- Section separators: `# --- Section Name ---`
- from __future__ import annotations (MUST be first import)
- Class-level error handling, custom exception types
- Async functions: async def, await for I/O

### Integration Points
- `master/storage/` is new package — needs `__init__.py`
- Phase 6 (Worker Layer) will import URIResolver to persist state
- Phase 4 (Master API) will use storage for checkpoint/artifact persistence
- No imports from envelope.middleware.shared in THIS phase (async storage is independent)

</code_context>

<specifics>
## Specific Ideas

- LocalStorageWriter should handle Path objects and convert to str for consistency
- URIResolver should cache writer instances (singleton per prefix)
- Configuration parsing should be defensive (invalid JSON = use defaults + warning)
- file_exists should return False for directories (only files)

</specifics>

<deferred>
## Deferred Ideas

- Retry logic for transient failures (Phase 9: Testing may add this)
- Connection pooling for S3/NFS (stubs raise NotImplementedError for now)
- Streaming read/write for large files (basic in-memory for now)
- Encryption at rest (future phase)

</deferred>

---

*Phase: 05-storage-layer*
*Context gathered: 2026-04-13*
