"""Master API subprocess launcher for E2E testing."""

from __future__ import annotations

import socket
import subprocess
import time
from pathlib import Path

import httpx


def find_free_port(start_port: int = 8000, max_attempts: int = 100) -> int:
    """Find an available port for the Master API.

    Args:
        start_port: Starting port to check
        max_attempts: Maximum attempts before giving up

    Returns:
        Available port number

    Raises:
        RuntimeError: If no free port found
    """
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", port))
                s.listen(1)
                return port
        except OSError:
            continue
    msg = f"No free port found in range {start_port}-{start_port + max_attempts}"
    raise RuntimeError(msg)


def start_master(port: int | None = None, timeout: int = 10) -> tuple[subprocess.Popen, int]:
    """Start Master API subprocess with health check.

    Args:
        port: Port to run on (auto-detect if None)
        timeout: Seconds to wait for health check

    Returns:
        Tuple of (subprocess.Popen, port)

    Raises:
        RuntimeError: If subprocess fails to start or health check times out
    """
    if port is None:
        port = find_free_port()

    # Build command to start Master API
    project_root = Path(__file__).parent.parent.parent
    cmd = [
        "python",
        "-m",
        "master.api",
        "--port", str(port),
    ]

    # Set environment variables
    import os
    env = os.environ.copy()
    env["NEO4J_URI"] = env.get("NEO4J_URI", "bolt://localhost:7687")
    env["NEO4J_USER"] = env.get("NEO4J_USER", "neo4j")
    env["NEO4J_PASSWORD"] = env.get("NEO4J_PASSWORD", "password")
    env["PYTHONUNBUFFERED"] = "1"

    # Start subprocess
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as e:
        msg = f"Failed to start Master API subprocess: {e}"
        raise RuntimeError(msg) from e

    # Wait for health check
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(f"http://localhost:{port}/health")
                if resp.status_code == 200:
                    return proc, port
        except httpx.RequestError:
            # Health check not ready yet
            pass
        time.sleep(0.5)

    # Timeout reached
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
    msg = f"Master API failed to start on port {port} within {timeout}s"
    raise RuntimeError(msg)


def stop_master(proc: subprocess.Popen, timeout: int = 5) -> int:
    """Stop Master API subprocess gracefully.

    Args:
        proc: Subprocess process object
        timeout: Seconds to wait before force-killing

    Returns:
        Exit code
    """
    try:
        proc.terminate()
        exit_code = proc.wait(timeout=timeout)
        return exit_code
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        return 1
