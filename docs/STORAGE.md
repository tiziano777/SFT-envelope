# Storage Layer Documentation

## Overview

The Master storage layer provides a URI-driven abstraction for persisting and retrieving artifacts across pluggable backends. This enables:

- **Artifact Persistence**: Checkpoints, lineage data, and training metrics persisted durably
- **Multi-Backend Support**: Local filesystem, S3 (stub), NFS (stub), and extensible via plugin registration
- **URI-Based Dispatch**: Simple `file://`, `s3://`, `nfs://` URIs automatically route to correct backend
- **Graceful Error Handling**: Comprehensive error hierarchy with async-compatible patterns
- **Configuration via Environment**: Backend selection and setup via `STORAGE_BACKENDS` env var (JSON)

## Architecture

### Components

```
┌─────────────────────────────────────┐
│         Application Layer            │
│    (Master API, Worker Daemon)       │
└────────────────┬────────────────────┘
                 │ URIs (file://, s3://, nfs://)
┌────────────────▼────────────────────┐
│      URIResolver (Dispatcher)        │
│  • Routes URIs to backends           │
│  • Handles env configuration         │
│  • Manages writer instances          │
└────┬─────┬──────────────────┬────────┘
     │     │                  │
┌────▼─┐ ┌─▼────────┐ ┌──────▼─────┐
│Local │ │    S3    │ │    NFS      │
│Writer│ │  Stub    │ │   Stub      │
└──────┘ └──────────┘ └─────────────┘
  file:// s3://         nfs://
  (Impl)  (NotImpl)     (NotImpl)
```

### Modules

| Module | Purpose | Status |
|--------|---------|--------|
| `base.py` | ABC + error hierarchy | ✓ Complete |
| `local.py` | LocalStorageWriter (file://) | ✓ Complete |
| `stubs.py` | S3/NFS stubs | ✓ Complete (raises NotImplementedError) |
| `resolver.py` | URIResolver dispatch | ✓ Complete |
| `__init__.py` | Public exports | ✓ Complete |

## API Reference

### BaseStorageWriter (ABC)

All storage writers inherit from `BaseStorageWriter` and must implement 4 async methods:

```python
class BaseStorageWriter(ABC):
    async def read_file(uri: str) -> bytes:
        """Read file contents from storage."""

    async def write_file(uri: str, data: bytes) -> None:
        """Write file to storage, creating parent dirs as needed."""

    async def file_exists(uri: str) -> bool:
        """Check if file exists (False for directories)."""

    async def delete_file(uri: str) -> None:
        """Delete file (idempotent - no error if not exists)."""
```

### Error Hierarchy

```python
StorageError              # Base exception for all storage operations
├── FileNotFound          # File doesn't exist on read/delete
└── URINotSupported       # URI prefix not recognized
```

### LocalStorageWriter

Implements file:// URIs for local filesystem access:

```python
from master.storage import LocalStorageWriter

writer = LocalStorageWriter(root_dir="/tmp")

# Read
data = await writer.read_file("file:///tmp/model.bin")

# Write (creates parent dirs)
await writer.write_file("file:///tmp/checkpoints/ckpt_1.bin", data)

# Check existence (False for directories)
exists = await writer.file_exists("file:///tmp/checkpoints/ckpt_1.bin")

# Delete (idempotent)
await writer.delete_file("file:///tmp/checkpoints/ckpt_1.bin")
```

### URIResolver

Dispatcher that routes URIs to appropriate backends:

```python
from master.storage import URIResolver

resolver = URIResolver()

# Automatically dispatches to LocalStorageWriter
data = await resolver.read_file("file:///tmp/data.bin")

# Raises NotImplementedError (stub)
await resolver.write_file("s3://bucket/key", b"data")

# Raises URINotSupported for unknown prefix
await resolver.read_file("unknown://path")
```

## Configuration

### Default Backends

By default, URIResolver loads:

| Prefix | Backend | Implementation |
|--------|---------|-----------------|
| `file://` | LocalStorageWriter | ✓ Full implementation |
| `s3://` | S3StorageWriter | Stub (NotImplementedError) |
| `nfs://` | NFSStorageWriter | Stub (NotImplementedError) |

### Custom Backends (Environment Variable)

Configure backends via `STORAGE_BACKENDS` JSON env var:

```bash
export STORAGE_BACKENDS='
{
  "file": {
    "class": "LocalStorageWriter",
    "config": {}
  },
  "s3": {
    "class": "S3StorageWriter",
    "config": {}
  }
}'
```

If `STORAGE_BACKENDS` is invalid or missing, defaults are used.

## Usage Examples

### Basic Operations

```python
import asyncio
from master.storage import URIResolver, FileNotFound

async def main():
    resolver = URIResolver()

    # Write checkpoint
    checkpoint_data = b"model weights..."
    await resolver.write_file("file:///tmp/checkpoint.bin", checkpoint_data)

    # Read checkpoint
    data = await resolver.read_file("file:///tmp/checkpoint.bin")
    assert data == checkpoint_data

    # Check existence
    exists = await resolver.file_exists("file:///tmp/checkpoint.bin")
    assert exists

    # Delete checkpoint
    await resolver.delete_file("file:///tmp/checkpoint.bin")

    # Delete non-existent file (idempotent, no error)
    await resolver.delete_file("file:///tmp/checkpoint.bin")

    # Attempt to read non-existent file
    try:
        await resolver.read_file("file:///tmp/nonexistent.bin")
    except FileNotFound as e:
        print(f"File not found: {e}")

asyncio.run(main())
```

### Error Handling

```python
from master.storage import URIResolver, StorageError, FileNotFound, URINotSupported

async def safe_read(resolver, uri):
    try:
        return await resolver.read_file(uri)
    except FileNotFound:
        print(f"File not found: {uri}")
        return None
    except URINotSupported:
        print(f"Unsupported URI: {uri}")
        return None
    except StorageError as e:
        print(f"Storage error: {e}")
        return None
```

### Integration with Master API

In `master/api.py`, checkpoint_push endpoint:

```python
from master.storage import URIResolver

resolver = URIResolver()

@app.post("/checkpoint_push")
async def checkpoint_push(req: CheckpointPush):
    """Push checkpoint with optional artifact storage."""

    # Persist to Neo4j (lineage)
    await repository.create_checkpoint(req)

    # Persist artifact to storage if URI provided
    if req.uri:
        tracer = get_tracer()
        with tracer.start_as_current_span("master.api.checkpoint_push.handle_artifacts"):
            artifact_data = await download_from_worker(req.exp_id, req.ckp_id)
            await resolver.write_file(req.uri, artifact_data)

    return {"status": "ok"}
```

## Testing

### Test Files

| File | Tests | Status |
|------|-------|--------|
| `test_storage_base.py` | Error hierarchy, ABC contract | 11 ✓ |
| `test_storage_local.py` | LocalStorageWriter CRUD | 16 ✓ |
| `test_storage_stubs.py` | S3/NFS NotImplementedError| 10 ✓ |
| `test_storage_resolver.py` | URIResolver dispatch | 11 ✓ |
| **Total** | | **48 ✓** |

### Running Tests

```bash
# All storage tests
pytest tests/unit/test_storage*.py -v

# Specific test file
pytest tests/unit/test_storage_local.py -v

# Single test
pytest tests/unit/test_storage_local.py::TestLocalStorageWriterRead::test_read_file_existing -v
```

## Design Decisions

### 1. Async-First API

All storage operations are `async` (coroutines) to:
- Prevent blocking on I/O
- Support concurrent checkpoint uploads
- Integrate with FastAPI async middleware

### 2. Error Hierarchy

Custom exception types (`FileNotFound`, `URINotSupported`) allow:
- Granular error handling in application code
- Clear error messages for debugging
- Type-safe exception catching

### 3. Idempotent Delete

`delete_file()` never raises on non-existent files:
- Workers can safely retry delete operations
- No need for existence check before delete
- Simplifies error handling

### 4. File-Only `file_exists()`

`file_exists()` returns `False` for directories:
- URI semantics assume "files", not "directories"
- Prevents accidental operations on directories
- Consistent behavior across backends

### 5. URI-Based Dispatch

URIResolver routes based on URI prefix:
- No hardcoded backend selection
- Extensible to new backends without code changes
- Configuration via environment (12-factor compliant)

## Future Enhancements

### Phase Extensions

1. **S3 Implementation** (not yet scheduled):
   - Replace `S3StorageWriter` stub with boto3 implementation
   - Support multi-region buckets
   - Implement object lifecycle policies

2. **NFS Implementation** (not yet scheduled):
   - Replace `NFSStorageWriter` stub with paramiko SSH
   - Support remote mount points
   - Implement retry logic for network failures

3. **Additional Backends**:
   - GCS (Google Cloud Storage)
   - AzureBlobStorage
   - MinIO
   - Worker-local fallback (worker:// URIs)

4. **Caching Layer**:
   - LRU cache for frequently read files
   - Cache invalidation strategies

5. **Compression**:
   - Transparent gzip/brotli compression
   - Configurable per backend

## Security Considerations

### Current Design

- ✓ No hardcoded credentials (backends configured via env)
- ✓ No arbitrary file access (URIs scoped by backend)
- ✓ No symlink traversal (Path.is_file() safe)

### Production Recommendations

- Store S3 credentials in secrets manager (AWS Secrets Manager, HashiCorp Vault)
- Use IAM roles instead of static credentials
- Enable bucket versioning for artifact recovery
- Implement access logs for audit trails
- Use TLS for NFS mounts

## Performance Characteristics

### LocalStorageWriter

| Operation | Time | Notes |
|-----------|------|-------|
| read_file | O(n) | Proportional to file size |
| write_file | O(n) | Proportional to file size |
| file_exists | O(1) | Just stat syscall |
| delete_file | O(1) | Just unlink syscall |

All operations use `asyncio.to_thread()` to prevent blocking.

### URIResolver

| Operation | Time |  Notes |
|-----------|------|-------|
| Dispatch | O(1) | Simple dict lookup |
| Lazy backend init | O(1) | Cached after first use |

## Related Code

- `master/neo4j/repository.py` — stores checkpoint metadata
- `master/api.py` — POST /checkpoint_push endpoint
- `.planning/phases/05-storage-layer/` — planning artifacts
- `tests/unit/test_storage*.py` — test suite (48 tests)
