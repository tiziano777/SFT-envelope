"""Fixtures for observability integration tests."""

import pytest
import socket
import time
from typing import Generator


@pytest.fixture(scope="session")
def phoenix_container() -> Generator[str, None, None]:
    """
    Spin up Phoenix OTEL collector in Docker for E2E tests.

    Uses docker Python library to manage container lifecycle. Assumes docker is running.
    Phoenix listens on localhost:4317 (gRPC), 6006 (UI).
    """
    container_id = None

    try:
        import docker

        client = docker.from_env()

        # Pull Phoenix image if not present
        try:
            client.images.pull("arizetechtechnologies/phoenix:latest")
        except Exception as e:
            print(f"Warning: Could not pull Phoenix image: {e}")

        # Run Phoenix container
        container = client.containers.run(
            "arizetechtechnologies/phoenix:latest",
            ports={"4317/tcp": 4317, "6006/tcp": 6006},
            detach=True,
            remove=False,
            name="test-phoenix",
        )

        container_id = container.id

        # Wait for Phoenix to be ready (max 30 seconds)
        for i in range(30):
            try:
                sock = socket.create_connection(("localhost", 4317), timeout=1)
                sock.close()
                print(f"Phoenix ready after {i + 1} attempts")
                break
            except (socket.timeout, ConnectionRefusedError):
                time.sleep(1)
        else:
            raise RuntimeError(
                "Phoenix gRPC port did not become reachable in 30 seconds"
            )

        yield "localhost:4317"

    finally:
        # Clean up container
        if container_id:
            try:
                import docker

                client = docker.from_env()
                container = client.containers.get(container_id)
                container.stop()
                container.remove()
                print(f"Cleaned up Phoenix container {container_id}")
            except Exception as e:
                print(f"Warning: Could not clean up Phoenix container: {e}")


@pytest.fixture
def reset_tracing_state():
    """Reset global tracer state before/after each test."""
    import master.observability.tracing as tracing_module

    original_provider = tracing_module._tracer_provider
    original_tracer = tracing_module._tracer

    yield

    tracing_module._tracer_provider = original_provider
    tracing_module._tracer = original_tracer
