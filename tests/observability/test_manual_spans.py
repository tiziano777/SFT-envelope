"""Unit tests for manual span attributes and nesting."""

import pytest
from unittest.mock import MagicMock, patch
from master.observability.tracing import get_tracer
from master.observability.constants import SPAN_NAMES


def test_span_context_from_api():
    """Test that span_context helper works correctly."""
    from master.api import span_context

    with patch("master.api.get_tracer") as mock_get_tracer:
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer

        with span_context("test.span", {"exp_id": "123", "recipe_id": "abc"}):
            pass

        # Verify span was created
        mock_tracer.start_as_current_span.assert_called_once_with("test.span")
        # Verify attributes were set
        assert mock_span.set_attribute.call_count == 2


def test_span_names_follow_convention():
    """Test that all span names follow service.operation.step convention."""
    for endpoint, spans in SPAN_NAMES.items():
        if isinstance(spans, dict):
            for step, name in spans.items():
                # Should start with "master.api."
                assert name.startswith(
                    "master.api."
                ), f"Span {name} does not follow convention"
                # Should have at least 3 parts (service.operation.step)
                parts = name.split(".")
                assert len(parts) >= 3, f"Span {name} does not have enough parts"


def test_span_names_defined_for_all_endpoints():
    """Test that SPAN_NAMES has entries for all critical endpoints."""
    expected_endpoints = {
        "handshake",
        "checkpoint_push",
        "status_update",
        "merge",
        "sync_event",
    }

    actual_endpoints = {
        k for k in SPAN_NAMES.keys() if isinstance(SPAN_NAMES[k], dict)
    }

    assert expected_endpoints.issubset(
        actual_endpoints
    ), f"Missing endpoints in SPAN_NAMES: {expected_endpoints - actual_endpoints}"


def test_handshake_has_expected_spans():
    """Test that handshake endpoint has lookup_experiment and determine_strategy spans."""
    handshake_spans = SPAN_NAMES.get("handshake")
    assert handshake_spans is not None
    assert "lookup_experiment" in handshake_spans
    assert "determine_strategy" in handshake_spans
    assert (
        handshake_spans["lookup_experiment"]
        == "master.api.handshake.lookup_experiment"
    )
    assert (
        handshake_spans["determine_strategy"]
        == "master.api.handshake.determine_strategy"
    )


def test_checkpoint_push_has_conditional_artifacts_span():
    """Test that checkpoint_push has validate, persist, and handle_artifacts spans."""
    checkpoint_spans = SPAN_NAMES.get("checkpoint_push")
    assert checkpoint_spans is not None
    assert "validate" in checkpoint_spans
    assert "persist_to_neo4j" in checkpoint_spans
    assert "handle_artifacts" in checkpoint_spans
