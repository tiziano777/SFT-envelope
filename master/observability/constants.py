"""OTEL instrumentation constants and conventions."""

# Service name
SERVICE_NAME = "master-api"

# Phoenix/OTEL endpoint (must match docker-compose.yml gRPC port)
OTEL_ENDPOINT = "http://localhost:4317"

# OTEL exporter timeout (seconds) — prevent hangs if Phoenix slow
OTEL_TIMEOUT_SECONDS = 10

# Span name hierarchy: master.api.{operation}.{substep}
SPAN_NAMES = {
    # Auto-instrumented (FastAPI middleware provides these)
    "fastapi_middleware": "master.api.{method} {path}",

    # Manual spans on critical endpoints
    "handshake": {
        "lookup_experiment": "master.api.handshake.lookup_experiment",
        "determine_strategy": "master.api.handshake.determine_strategy",
    },
    "checkpoint_push": {
        "validate": "master.api.checkpoint_push.validate",
        "persist_to_neo4j": "master.api.checkpoint_push.persist_to_neo4j",
        "handle_artifacts": "master.api.checkpoint_push.handle_artifacts",
    },
    "status_update": {
        "validate": "master.api.status_update.validate",
        "upsert_checkpoint": "master.api.status_update.upsert_checkpoint",
    },
    "merge": {
        "validate": "master.api.merge.validate",
        "retrieve_source": "master.api.merge.retrieve_source",
        "merge_lineage": "master.api.merge.merge_lineage",
        "persist": "master.api.merge.persist",
    },
    "sync_event": {
        "validate": "master.api.sync_event.validate",
        "process_event": "master.api.sync_event.process_event",
        "upsert_data": "master.api.sync_event.upsert_data",
    },
}

# Standard attributes for all spans
SPAN_ATTRIBUTES_BASE = {
    "service.name": SERVICE_NAME,
    "service.version": "0.1.0",  # Will be overridden at runtime
}

# HTTP request/response attributes (OTEL semantic conventions)
SPAN_ATTRIBUTES_HTTP = {
    "http.method": str,  # Set by instrumentation
    "http.url": str,     # Set by instrumentation
    "http.status_code": int,  # Set by instrumentation
}
