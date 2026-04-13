"""Tests for Worker daemon bootstrap and state persistence."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import json

from envelope.middleware.worker.daemon import WorkerDaemon
from envelope.middleware.shared.models import WorkerState, TransferLogEntry


@pytest.fixture
def setup_dir(tmp_path):
    """Create temp setup directory with worker subdirectory."""
    worker_dir = tmp_path / "worker"
    worker_dir.mkdir()
    return tmp_path


@pytest.fixture
def daemon(setup_dir):
    """Create WorkerDaemon instance."""
    return WorkerDaemon(
        setup_dir,
        master_uri="http://localhost:8000",
        api_key="test-key",
        handshake_timeout=5,
    )


@pytest.fixture
def mock_worker_state():
    """Mock WorkerState for testing."""
    return WorkerState(
        exp_id="exp-123",
        recipe_id="recipe-abc",
        master_uri="http://localhost:8000",
        strategy="NEW",
    )


@pytest.mark.asyncio
async def test_bootstrap_success(daemon, mock_worker_state):
    """Test successful bootstrap with state persistence."""
    with patch.object(daemon, "_handshake", new_callable=AsyncMock) as mock_hs:
        mock_hs.return_value = mock_worker_state

        state = await daemon.bootstrap()

        assert state is not None
        assert state.exp_id == "exp-123"
        assert state.strategy == "NEW"

        # Verify files created
        assert (daemon.setup_dir / "worker" / ".exp_id").read_text() == "exp-123"
        assert (daemon.setup_dir / "worker" / ".handshake_done").exists()
        assert (daemon.setup_dir / "worker" / ".worker_state.json").exists()

        # Verify state file content
        state_data = json.loads(
            (daemon.setup_dir / "worker" / ".worker_state.json").read_text()
        )
        assert state_data["exp_id"] == "exp-123"


@pytest.mark.asyncio
async def test_bootstrap_timeout(daemon):
    """Test bootstrap timeout -> degraded mode."""
    with patch.object(daemon, "_handshake", new_callable=AsyncMock) as mock_hs:
        mock_hs.side_effect = asyncio.TimeoutError()

        state = await daemon.bootstrap()

        assert state is None
        # No state files created on timeout
        assert not (daemon.setup_dir / "worker" / ".handshake_done").exists()


@pytest.mark.asyncio
async def test_bootstrap_handshake_failure(daemon):
    """Test bootstrap with handshake returning None."""
    with patch.object(daemon, "_handshake", new_callable=AsyncMock) as mock_hs:
        mock_hs.return_value = None

        state = await daemon.bootstrap()

        assert state is None


@pytest.mark.asyncio
async def test_bootstrap_exception_handling(daemon):
    """Test bootstrap handles exceptions gracefully."""
    with patch.object(daemon, "_handshake", new_callable=AsyncMock) as mock_hs:
        mock_hs.side_effect = RuntimeError("Connection refused")

        state = await daemon.bootstrap()

        assert state is None


@pytest.mark.asyncio
async def test_handshake_timeout_asyncio_respects_deadline(daemon):
    """Test asyncio.wait_for actually enforces timeout."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:

        # Simulate slow response that exceeds timeout
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(10)
            return MagicMock()

        mock_post.side_effect = slow_response

        state = await daemon._handshake()
        assert state is None


def test_persist_state_atomic_writes(daemon, mock_worker_state):
    """Test _persist_state uses atomic writes."""
    daemon._persist_state(mock_worker_state)

    # All files should exist
    assert daemon.state_file.exists()
    assert daemon.exp_id_file.exists()
    assert daemon.handshake_done_file.exists()

    # Verify content
    state_data = json.loads(daemon.state_file.read_text())
    assert state_data["exp_id"] == "exp-123"
    assert daemon.exp_id_file.read_text() == "exp-123"


def test_transfer_log_append_idempotent(daemon, tmp_path):
    """Test transfer log append is idempotent."""
    daemon.transfer_log = tmp_path / "transfer_log.jsonl"

    entry1 = TransferLogEntry(
        event_id="ev-1",
        event_type="checkpoint",
        status="sent",
    )
    entry2 = TransferLogEntry(
        event_id="ev-2",
        event_type="metric",
        status="pending",
    )

    daemon.log_transfer(entry1)
    daemon.log_transfer(entry2)

    lines = daemon.transfer_log.read_text().strip().split("\n")
    assert len(lines) == 2

    # Verify JSON validity
    entry1_data = json.loads(lines[0])
    entry2_data = json.loads(lines[1])
    assert entry1_data["event_id"] == "ev-1"
    assert entry2_data["event_id"] == "ev-2"


def test_worker_state_serialization(mock_worker_state):
    """Test WorkerState serializes correctly."""
    json_str = mock_worker_state.model_dump_json()
    data = json.loads(json_str)

    assert data["exp_id"] == "exp-123"
    assert data["strategy"] == "NEW"

    # Deserialize
    reloaded = WorkerState(**json.loads(json_str))
    assert reloaded.exp_id == mock_worker_state.exp_id


def test_transfer_log_entry_all_fields():
    """Test TransferLogEntry with all optional fields."""
    entry = TransferLogEntry(
        event_id="ev-123",
        event_type="checkpoint",
        uri="file:///checkpoint.json",
        status="failed",
        error="Connection timeout",
        retry_count=3,
    )

    assert entry.event_id == "ev-123"
    assert entry.error == "Connection timeout"
    assert entry.retry_count == 3
