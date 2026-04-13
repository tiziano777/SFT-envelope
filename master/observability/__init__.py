"""Master observability layer: Phoenix tracing with OTEL integration.

Exports:
- setup_tracing: Initialize global tracer (call once at startup)
- get_tracer: Get global tracer instance
"""

from __future__ import annotations

from master.observability.tracing import get_tracer, setup_tracing

__all__ = ["setup_tracing", "get_tracer"]
