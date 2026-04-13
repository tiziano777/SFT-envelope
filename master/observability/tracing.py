"""Phoenix tracing with OpenTelemetry integration.

Singleton tracer setup with graceful degradation (OBSV-02, OBSV-03).
"""

from __future__ import annotations

import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import NoOpTracer, Tracer

logger = logging.getLogger(__name__)

_tracer_provider: Optional[TracerProvider] = None
_tracer: Optional[Tracer] = None


def setup_tracing(
    service_name: str = "master-api",
    phoenix_endpoint: str = "http://localhost:4317",
) -> None:
    """Initialize global tracer with graceful degradation.

    Call once at application startup, before any request handling.
    Fails silently if Phoenix is unreachable (OBSV-02).

    Args:
        service_name: Service identifier for spans
        phoenix_endpoint: OTEL collector endpoint (Phoenix on localhost:4317)
    """
    global _tracer_provider, _tracer

    try:
        # Create OTEL exporter pointing to Phoenix
        exporter = OTLPSpanExporter(
            endpoint=phoenix_endpoint,
            timeout=10,
        )

        # Create tracer provider with span processor
        _tracer_provider = TracerProvider()
        _tracer_provider.add_span_processor(BatchSpanProcessor(exporter))

        # Set global tracer provider
        trace.set_tracer_provider(_tracer_provider)

        # Get tracer from provider
        _tracer = _tracer_provider.get_tracer(
            instrumenting_module_name=service_name,
            instrumenting_library_version="1.0.0",
        )

        logger.info(f"Tracing initialized: {service_name} → {phoenix_endpoint}")

    except Exception as e:
        # Graceful degradation: log warning, use no-op tracer
        logger.warning(f"Tracing setup failed: {e}. Using no-op tracer.")
        _tracer_provider = TracerProvider()
        _tracer = _tracer_provider.get_tracer(instrumenting_module_name=service_name)


def get_tracer() -> Tracer:
    """Get global tracer instance (OBSV-03)."""
    global _tracer

    if _tracer is None:
        logger.debug("Tracer not initialized; returning no-op tracer")
        return NoOpTracer()

    return _tracer
