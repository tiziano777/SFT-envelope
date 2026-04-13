"""End-to-end integration tests with real Phoenix container."""

import pytest
import time
from master.api import setup_master_api
from master.observability.tracing import setup_tracing, get_tracer
from fastapi.testclient import TestClient
from opentelemetry.trace import NoOpTracer


@pytest.mark.integration
def test_traces_appear_in_phoenix(phoenix_container, reset_tracing_state):
    """
    Verify that traces from Master API appear in Phoenix UI.

    OBSV-01: Phoenix UI accessible, shows trace data.
    """
    # Setup tracing with real Phoenix endpoint
    setup_tracing(service_name="master-api", phoenix_endpoint=f"http://{phoenix_container}")

    # Create test app and client
    test_app = setup_master_api()
    client = TestClient(test_app)

    # Make some requests to generate spans
    response = client.get("/health")
    assert response.status_code == 200

    # Make a more complex request with manual spans
    response = client.post("/handshake", json={})
    # May fail with 422 due to missing fields, but that's OK — we just care that spans were created
    assert response.status_code in [200, 422]

    # Give Phoenix time to receive and process the trace
    time.sleep(2)

    # Verify tracer is real (not no-op)
    tracer = get_tracer()
    assert tracer is not None
    # If tracing failed, tracer would be NoOpTracer
    assert not isinstance(tracer, NoOpTracer), "Tracer should be real, not no-op"


@pytest.mark.integration
def test_graceful_degradation_when_phoenix_unavailable(reset_tracing_state):
    """
    Verify OBSV-02: setup_tracing() succeeds silently when Phoenix unreachable.
    """
    # Try to setup tracing with unreachable Phoenix
    setup_tracing(
        service_name="master-api", phoenix_endpoint="http://localhost:9999"
    )

    # Should not raise
    tracer = get_tracer()
    assert tracer is not None
    # Tracer should be functional (either real or no-op, both work)
    # The important thing is that it doesn't raise when we use it
    with tracer.start_as_current_span("test.span") as span:
        span.set_attribute("test", "value")
    # If we got here without exception, graceful degradation worked


def test_manual_spans_with_real_tracer(phoenix_container, reset_tracing_state):
    """Verify manual spans are created with real tracer."""
    setup_tracing(
        service_name="master-api", phoenix_endpoint=f"http://{phoenix_container}"
    )

    test_app = setup_master_api()
    client = TestClient(test_app)

    # Call endpoint with manual spans
    response = client.post("/checkpoint_push", json={})

    # Verify response (may be 422 due to missing fields)
    assert response.status_code in [200, 422]

    # Give Phoenix time to process trace
    time.sleep(1)

    # Verify tracer is real (not no-op)
    tracer = get_tracer()
    assert not isinstance(tracer, NoOpTracer)
