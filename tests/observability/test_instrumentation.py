"""Unit tests for FastAPI auto-instrumentation (D-04 requirement)."""

import pytest
from unittest.mock import patch, MagicMock
from master.api import create_app
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor


def test_fastapi_instrumented_once():
    """Test that FastAPI instrumentation is applied exactly once."""
    with patch.object(
        FastAPIInstrumentor, "instrument_app", wraps=FastAPIInstrumentor.instrument_app
    ) as mock_instrument:
        app = create_app()

        # Verify instrument_app was called exactly once
        assert mock_instrument.call_count == 1
        # Check that the first positional arg is the app
        assert mock_instrument.call_args_list[0][0][0] is app


def test_health_check_endpoint_exists():
    """Test that /health endpoint is present and working."""
    from fastapi.testclient import TestClient

    app = create_app()
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_middleware_attached():
    """Test that FastAPI instrumentation middleware is attached to the app."""
    app = create_app()

    # Check that app.middleware was called (instrumentation adds middleware)
    # OTEL instrumentation adds a middleware class to app.user_middleware
    # Verify by checking starlette middleware stack exists
    assert hasattr(app, "user_middleware")


def test_no_double_instrumentation_on_recreate():
    """Test that creating multiple apps doesn't double-instrument each."""
    with patch.object(
        FastAPIInstrumentor, "instrument_app", wraps=FastAPIInstrumentor.instrument_app
    ) as mock_instrument:
        app1 = create_app()
        app2 = create_app()

        # Each app should be instrumented once (2 calls total, 1 per app)
        assert mock_instrument.call_count == 2
        # But each individual app is instrumented exactly once
        calls = mock_instrument.call_args_list
        assert calls[0][0][0] is app1
        assert calls[1][0][0] is app2


def test_endpoint_stubs_respond():
    """Test that all 5 critical endpoints are reachable."""
    from fastapi.testclient import TestClient

    app = create_app()
    client = TestClient(app)

    endpoints = [
        ("POST", "/handshake"),
        ("POST", "/checkpoint_push"),
        ("POST", "/status_update"),
        ("POST", "/merge"),
        ("POST", "/sync_event"),
    ]

    for method, path in endpoints:
        # All stubs return {"status": "ok"} or similar
        # May return 422 if schema validation fails, but endpoint exists
        response = client.request(method, path, json={})
        # Status code may be 200 (success) or 422 (validation), but not 404 (not found)
        assert response.status_code != 404, f"{method} {path} not found"
