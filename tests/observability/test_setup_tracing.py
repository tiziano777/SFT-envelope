"""Unit tests for tracing setup and graceful degradation (OBSV-02, OBSV-03)."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from master.observability.tracing import get_tracer, setup_tracing


def test_setup_tracing_success(caplog):
    """Test successful tracing initialization."""
    import master.observability.tracing as tracing_module

    # Reset global state
    tracing_module._tracer_provider = None
    tracing_module._tracer = None

    with patch("master.observability.tracing.OTLPSpanExporter"):
        with caplog.at_level(logging.INFO):
            setup_tracing(service_name="test-api", phoenix_endpoint="http://localhost:4317")

        assert "Tracing initialized" in caplog.text
        tracer = get_tracer()
        assert tracer is not None


def test_setup_tracing_graceful_degradation(caplog):
    """Test graceful degradation when Phoenix unreachable (OBSV-02)."""
    import master.observability.tracing as tracing_module

    # Reset global state
    tracing_module._tracer_provider = None
    tracing_module._tracer = None

    with patch("master.observability.tracing.OTLPSpanExporter") as mock_exporter:
        mock_exporter.side_effect = ConnectionRefusedError("Connection refused")

        with caplog.at_level(logging.WARNING):
            setup_tracing()

        # Should log WARNING, not ERROR
        assert "Tracing setup failed" in caplog.text
        assert "no-op tracer" in caplog.text


def test_get_tracer_fallback():
    """Test get_tracer returns no-op when setup_tracing not called (OBSV-03)."""
    import master.observability.tracing as tracing_module

    # Force uninitialized state
    original_tracer = tracing_module._tracer
    tracing_module._tracer = None

    try:
        tracer = get_tracer()
        assert tracer is not None
        # Should be no-op tracer (safe to use)
    finally:
        tracing_module._tracer = original_tracer


def test_manual_span_context():
    """Test manual span creation with attributes."""
    import master.observability.tracing as tracing_module

    # Reset global state
    tracing_module._tracer_provider = None
    tracing_module._tracer = None

    with patch("master.observability.tracing.OTLPSpanExporter"):
        setup_tracing()
        tracer = get_tracer()

        with tracer.start_as_current_span("test.span") as span:
            span.set_attribute("key", "value")
            span.set_attribute("exp_id", "123")

        # If we got here without exceptions, tracing worked
        assert True
