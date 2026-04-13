"""Master API with Phoenix tracing and lineage logic.

OTEL auto-instrumented FastAPI service with manual spans on critical endpoints
(OBSV-01 through OBSV-05).
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Generator

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from master.observability.tracing import get_tracer, setup_tracing

logger = logging.getLogger(__name__)


@contextmanager
def span_context(span_name: str, attributes: dict[str, Any] | None = None) -> Generator[Any, None, None]:
    """Context manager for creating spans with attributes.

    Args:
        span_name: Name of the span (e.g., "master.api.handshake.lookup")
        attributes: Dictionary of attributes to set on the span

    Yields:
        The span object
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(span_name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span


def create_app() -> FastAPI:
    """Create and configure FastAPI app with tracing instrumentation and all endpoints."""
    app = FastAPI(
        title="Master API",
        description="Lineage tracking for LLM fine-tuning experiments",
        version="1.0.0",
    )

    # Auto-instrument FastAPI (OBSV-04: no double-instrumentation)
    FastAPIInstrumentor.instrument_app(app, excluded_urls=".*health.*|.*metrics.*")

    # --- Health Check Endpoint ---

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    # --- Critical Endpoints with Manual Spans ---

    @app.post("/handshake")
    async def handshake(req: dict[str, Any]) -> dict[str, Any]:
        """Handshake endpoint with manual tracing spans (OBSV-05).

        Spans:
        - master.api.handshake.lookup_experiment
        - master.api.handshake.determine_strategy
        """
        tracer = get_tracer()

        # Span 1: lookup_experiment
        with tracer.start_as_current_span("master.api.handshake.lookup_experiment") as span:
            span.set_attribute("recipe_id", req.get("recipe_id", "unknown"))
            span.set_attribute("exp_id", req.get("exp_id", "new"))
            span.set_attribute("config_hash", req.get("config_hash", "unknown"))
            # TODO: db.find_experiment_by_hashes(req)

        # Span 2: determine_strategy
        with tracer.start_as_current_span("master.api.handshake.determine_strategy") as span:
            strategy = "NEW"  # TODO: Strategy logic
            span.set_attribute("strategy", strategy)

        return {"strategy": strategy, "exp_id": req.get("exp_id", "new")}

    @app.post("/checkpoint_push")
    async def checkpoint_push(req: dict[str, Any]) -> dict[str, Any]:
        """Checkpoint push endpoint with manual spans (OBSV-05)."""
        tracer = get_tracer()

        # Span 1: validate
        with tracer.start_as_current_span("master.api.checkpoint_push.validate") as span:
            span.set_attribute("exp_id", req.get("exp_id"))
            span.set_attribute("checkpoint_id", req.get("checkpoint_id"))
            span.set_attribute("has_uri", bool(req.get("uri")))

        # Span 2: persist_to_neo4j
        with tracer.start_as_current_span("master.api.checkpoint_push.persist_to_neo4j") as span:
            span.set_attribute("exp_id", req.get("exp_id"))
            span.set_attribute("checkpoint_id", req.get("checkpoint_id"))

        # Span 3: handle_artifacts (conditional)
        if req.get("uri"):
            with tracer.start_as_current_span("master.api.checkpoint_push.handle_artifacts") as span:
                span.set_attribute("uri", req.get("uri"))

        return {"status": "ok", "checkpoint_id": req.get("checkpoint_id")}

    @app.post("/status_update")
    async def status_update(req: dict[str, Any]) -> dict[str, Any]:
        """Status update endpoint with manual spans (OBSV-05)."""
        tracer = get_tracer()

        with tracer.start_as_current_span("master.api.status_update.validate"):
            pass

        with tracer.start_as_current_span("master.api.status_update.upsert_checkpoint"):
            pass

        return {"status": "ok"}

    @app.post("/merge")
    async def merge(req: dict[str, Any]) -> dict[str, Any]:
        """Merge endpoint with manual spans (OBSV-05)."""
        tracer = get_tracer()

        with tracer.start_as_current_span("master.api.merge.validate"):
            pass

        with tracer.start_as_current_span("master.api.merge.retrieve_source"):
            pass

        with tracer.start_as_current_span("master.api.merge.merge_lineage"):
            pass

        with tracer.start_as_current_span("master.api.merge.persist"):
            pass

        return {"status": "ok"}

    @app.post("/sync_event")
    async def sync_event(req: dict[str, Any]) -> dict[str, Any]:
        """Sync event endpoint with manual spans (OBSV-05)."""
        tracer = get_tracer()

        with tracer.start_as_current_span("master.api.sync_event.validate"):
            pass

        with tracer.start_as_current_span("master.api.sync_event.process_event"):
            pass

        with tracer.start_as_current_span("master.api.sync_event.upsert_data"):
            pass

        return {"status": "ok"}

    logger.info("Master API initialized with Phoenix tracing (OBSV-01 through OBSV-05)")
    return app


def setup_master_api() -> FastAPI:
    """Setup and return configured Master API (alias for create_app)."""
    return create_app()


# Create global FastAPI app
app = create_app()

# Initialize tracing at startup
setup_tracing(service_name="master-api", phoenix_endpoint="http://localhost:4317")
