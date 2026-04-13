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
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from envelope.middleware.shared.envelopes import (
    CheckpointPush,
    HandshakeRequest,
    HandshakeResponse,
    StatusUpdate,
    Strategy,
    SyncEvent,
)
from master.controllers import LineageController
from master.errors import (
    CircularDependencyError,
    ConflictError,
    ExperimentNotFoundError,
    InternalServerError,
    MasterAPIError,
    ValidationError,
)
from master.neo4j.client import Neo4jClient
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

    # --- Error Handlers ---

    @app.exception_handler(MasterAPIError)
    async def handle_master_api_error(request, exc: MasterAPIError):
        """Handle MasterAPIError with appropriate HTTP status code."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    @app.exception_handler(Exception)
    async def handle_generic_error(request, exc: Exception):
        """Handle unexpected errors."""
        logger.exception("Unexpected error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

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
        neo4j_client = Neo4jClient.get_instance()
        repo = neo4j_client.repository

        # Span 1: lookup_experiment
        with tracer.start_as_current_span("master.api.handshake.lookup_experiment") as span:
            span.set_attribute("recipe_id", req.recipe_id)
            span.set_attribute("config_hash", req.config_hash)
            try:
                existing_exp = await repo.find_experiment_by_hashes(
                    config_hash=req.config_hash,
                    code_hash=req.code_hash,
                    req_hash=req.req_hash,
                )
            except Exception as e:
                logger.error(f"Error looking up experiment: {e}")
                existing_exp = None

        # Span 2: determine_strategy
        with tracer.start_as_current_span("master.api.handshake.determine_strategy") as span:
            strategy = LineageController.determine_strategy(existing_exp, req)
            span.set_attribute("strategy", strategy.value)

        # Span 3: exp_id generation
        with tracer.start_as_current_span("master.api.handshake.exp_id_generation") as span:
            exp_id = LineageController.exp_id_from_strategy(strategy, existing_exp, req)
            span.set_attribute("exp_id", exp_id)

        # Span 4: fetch baseline checkpoint for RESUME
        base_checkpoint_uri = None
        if strategy == Strategy.RESUME and existing_exp:
            with tracer.start_as_current_span("master.api.handshake.retrieve_baseline") as span:
                try:
                    latest_ckp = await repo.get_latest_checkpoint(existing_exp.exp_id)
                    if latest_ckp:
                        base_checkpoint_uri = latest_ckp.uri
                        span.set_attribute("baseline_uri", base_checkpoint_uri)
                except Exception as e:
                    logger.warning(f"Could not retrieve baseline checkpoint: {e}")

        return HandshakeResponse(
            exp_id=exp_id,
            strategy=strategy,
            base_checkpoint_uri=base_checkpoint_uri,
        )

    @app.post("/checkpoint_push")
    async def checkpoint_push(req: CheckpointPush) -> dict[str, Any]:
        """Checkpoint push endpoint with manual spans (OBSV-05)."""
        tracer = get_tracer()
        neo4j_client = Neo4jClient.get_instance()
        repo = neo4j_client.repository

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
            try:
                await repo.upsert_checkpoint(
                    exp_id=req.exp_id,
                    ckp_id=req.ckp_id,
                    epoch=req.epoch or 0,
                    run=req.run or 0,
                    metrics_snapshot=req.metrics_snapshot or {},
                    uri=req.uri,
                )
            except Exception as e:
                logger.error(f"Error upserting checkpoint: {e}")
                raise InternalServerError(str(e))

        # Span 3: handle_artifacts (conditional)
        if req.uri:
            with tracer.start_as_current_span("master.api.checkpoint_push.handle_artifacts") as span:
                span.set_attribute("uri", req.uri)

        return {"status": "ok", "checkpoint_id": req.ckp_id}

    @app.post("/status_update")
    async def status_update(req: StatusUpdate) -> dict[str, Any]:
        """Status update endpoint with manual spans (OBSV-05)."""
        tracer = get_tracer()
        neo4j_client = Neo4jClient.get_instance()
        repo = neo4j_client.repository

        with tracer.start_as_current_span("master.api.status_update.validate") as span:
            span.set_attribute("exp_id", req.exp_id)
            span.set_attribute("status", req.status)

        with tracer.start_as_current_span("master.api.status_update.upsert_checkpoint") as span:
            if req.checkpoint_id:
                span.set_attribute("ckp_id", req.checkpoint_id)
            try:
                # Map error_message to exit_message, status to exit_code
                exit_code = 1 if req.status == "failed" else (0 if req.status == "done" else None)
                await repo.update_experiment_status(
                    exp_id=req.exp_id,
                    status=req.status,
                    exit_code=exit_code,
                    exit_message=req.error_message,
                )
            except Exception as e:
                logger.error(f"Error updating status: {e}")
                raise InternalServerError(str(e))

        return {"status": "ok"}

    @app.post("/merge")
    async def merge(req: dict[str, Any]) -> dict[str, Any]:
        """Merge endpoint with manual spans (OBSV-05)."""
        tracer = get_tracer()
        neo4j_client = Neo4jClient.get_instance()
        repo = neo4j_client.repository

        with tracer.start_as_current_span("master.api.merge.validate") as span:
            span.set_attribute("exp_id", req.get("exp_id"))

        with tracer.start_as_current_span("master.api.merge.retrieve_source") as span:
            try:
                exp = await repo.get_experiment(req.get("exp_id"))
                if not exp:
                    raise ExperimentNotFoundError(req.get("exp_id"))
            except Exception as e:
                logger.error(f"Error retrieving experiment: {e}")
                raise

        with tracer.start_as_current_span("master.api.merge.merge_lineage") as span:
            pass

        with tracer.start_as_current_span("master.api.merge.persist") as span:
            pass

        return {"status": "ok"}

    @app.post("/sync_event")
    async def sync_event(req: SyncEvent) -> dict[str, Any]:
        """Sync event endpoint with manual spans (OBSV-05)."""
        tracer = get_tracer()
        neo4j_client = Neo4jClient.get_instance()
        repo = neo4j_client.repository

        with tracer.start_as_current_span("master.api.sync_event.validate") as span:
            span.set_attribute("event_id", req.event_id)
            span.set_attribute("event_type", req.event_type)
            span.set_attribute("exp_id", req.exp_id)

        with tracer.start_as_current_span("master.api.sync_event.process_event") as span:
            try:
                # Verify experiment exists
                exp = await repo.get_experiment(req.exp_id)
                if not exp:
                    raise ExperimentNotFoundError(req.exp_id)
            except Exception as e:
                logger.error(f"Error verifying experiment: {e}")
                raise InternalServerError(str(e))

        with tracer.start_as_current_span("master.api.sync_event.upsert_data") as span:
            # Sync event processing deferred to Phase 4 GREEN phase 2
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
