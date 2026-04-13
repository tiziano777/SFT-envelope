"""Master API with Phoenix tracing and lineage logic.

OTEL auto-instrumented FastAPI service with manual spans on critical endpoints
(OBSV-01 through OBSV-05).
"""

from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from typing import Any, Generator

from fastapi import FastAPI, HTTPException
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from envelope.middleware.shared.envelopes import (
    CheckpointPush,
    HandshakeRequest,
    HandshakeResponse,
    StatusUpdate,
    Strategy,
    SyncEvent,
)
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
                if value is not None:
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

    @app.post("/handshake", response_model=HandshakeResponse)
    async def handshake(req: HandshakeRequest) -> HandshakeResponse:
        """Handshake endpoint with manual tracing spans (OBSV-05).

        Spans:
        - master.api.handshake.lookup_experiment
        - master.api.handshake.determine_strategy
        """
        tracer = get_tracer()

        # Span 1: lookup_experiment
        with tracer.start_as_current_span("master.api.handshake.lookup_experiment") as span:
            span.set_attribute("recipe_id", req.recipe_id)
            span.set_attribute("config_hash", req.config_hash)
            # TODO: db.find_experiment_by_hashes(req)
            existing_exp = None

        # Span 2: determine_strategy
        with tracer.start_as_current_span("master.api.handshake.determine_strategy") as span:
            if existing_exp:
                strategy = Strategy.RESUME
            elif req.base_exp_id:
                if req.checkpoint_id_to_resume:
                    strategy = Strategy.RETRY
                else:
                    strategy = Strategy.BRANCH
            else:
                strategy = Strategy.NEW

            span.set_attribute("strategy", strategy.value)

        exp_id = existing_exp.exp_id if existing_exp else str(uuid.uuid4())

        return HandshakeResponse(
            exp_id=exp_id,
            strategy=strategy,
            base_checkpoint_uri=None,
        )

    @app.post("/checkpoint_push")
    async def checkpoint_push(req: CheckpointPush) -> dict[str, Any]:
        """Checkpoint push endpoint with manual spans (OBSV-05)."""
        tracer = get_tracer()

        # Span 1: validate
        with tracer.start_as_current_span("master.api.checkpoint_push.validate") as span:
            span.set_attribute("exp_id", req.exp_id)
            span.set_attribute("ckp_id", req.ckp_id)
            if req.uri:
                span.set_attribute("has_uri", True)

        # Span 2: persist_to_neo4j
        with tracer.start_as_current_span("master.api.checkpoint_push.persist_to_neo4j") as span:
            span.set_attribute("exp_id", req.exp_id)
            span.set_attribute("ckp_id", req.ckp_id)
            # TODO: repo.upsert_checkpoint(...)

        # Span 3: handle_artifacts (conditional)
        if req.uri:
            with tracer.start_as_current_span("master.api.checkpoint_push.handle_artifacts") as span:
                span.set_attribute("uri", req.uri)
                # TODO: storage.file_exists(req.uri)

        return {"status": "ok", "checkpoint_id": req.ckp_id}

    @app.post("/status_update")
    async def status_update(req: StatusUpdate) -> dict[str, Any]:
        """Status update endpoint with manual spans (OBSV-05)."""
        tracer = get_tracer()

        with tracer.start_as_current_span("master.api.status_update.validate") as span:
            span.set_attribute("exp_id", req.exp_id)
            span.set_attribute("status", req.status)

        with tracer.start_as_current_span("master.api.status_update.upsert_checkpoint") as span:
            if req.checkpoint_id:
                span.set_attribute("ckp_id", req.checkpoint_id)
            # TODO: repo.update_experiment_status(...)

        return {"status": "ok"}

    @app.post("/merge")
    async def merge(req: dict[str, Any]) -> dict[str, Any]:
        """Merge endpoint with manual spans (OBSV-05)."""
        tracer = get_tracer()

        with tracer.start_as_current_span("master.api.merge.validate") as span:
            span.set_attribute("exp_id", req.get("exp_id"))

        with tracer.start_as_current_span("master.api.merge.retrieve_source") as span:
            pass
            # TODO: repo.find_experiment_by_id(...)

        with tracer.start_as_current_span("master.api.merge.merge_lineage") as span:
            pass
            # TODO: lineage validation + merge logic

        with tracer.start_as_current_span("master.api.merge.persist") as span:
            pass
            # TODO: repo.create_merged_checkpoint(...)

        return {"status": "ok"}

    @app.post("/sync_event")
    async def sync_event(req: SyncEvent) -> dict[str, Any]:
        """Sync event endpoint with manual spans (OBSV-05)."""
        tracer = get_tracer()

        with tracer.start_as_current_span("master.api.sync_event.validate") as span:
            span.set_attribute("event_id", req.event_id)
            span.set_attribute("event_type", req.event_type)
            span.set_attribute("exp_id", req.exp_id)

        with tracer.start_as_current_span("master.api.sync_event.process_event") as span:
            pass
            # TODO: deduplication check by event_id

        with tracer.start_as_current_span("master.api.sync_event.upsert_data") as span:
            pass
            # TODO: repo.process_sync_event(...)

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
