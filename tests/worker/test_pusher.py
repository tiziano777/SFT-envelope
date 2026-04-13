"""Tests for async pusher."""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import json

from envelope.middleware.worker.pusher import AsyncPusher
from envelope.middleware.shared.models import TransferLogEntry


@pytest.fixture
def tmp_transfer_log(tmp_path):
    return tmp_path / "transfer_log.jsonl"


@pytest.fixture
def mock_connection():
    conn = MagicMock()
    conn.send_metadata = AsyncMock()
    return conn


@pytest.mark.asyncio
async def test_pusher_deduplication(mock_connection, tmp_transfer_log):
    """AsyncPusher deduplicates events by event_id."""
    pusher = AsyncPusher(mock_connection, tmp_transfer_log)

    await pusher.push_event("ev-1", "checkpoint", {"data": "test"})
    await pusher.push_event("ev-1", "checkpoint", {"data": "test"})

    assert pusher.queue.qsize() == 1


@pytest.mark.asyncio
async def test_pusher_retry_success_on_third_attempt(mock_connection, tmp_transfer_log):
    """AsyncPusher retries and succeeds."""
    mock_connection.send_metadata.side_effect = [False, False, True]

    pusher = AsyncPusher(mock_connection, tmp_transfer_log, max_retries=3, initial_backoff=0.01)

    item = {
        "event_id": "ev-1",
        "event_type": "checkpoint",
        "data": {"test": "data"},
        "retry_count": 0
    }

    await pusher._push_with_retry(item)

    assert mock_connection.send_metadata.call_count == 3


@pytest.mark.asyncio
async def test_pusher_exhausted_retries_logged(mock_connection, tmp_transfer_log):
    """AsyncPusher logs exhausted retries."""
    mock_connection.send_metadata.side_effect = Exception("Connection error")

    pusher = AsyncPusher(mock_connection, tmp_transfer_log, max_retries=2, initial_backoff=0.01)

    item = {
        "event_id": "ev-1",
        "event_type": "checkpoint",
        "data": {"test": "data"},
        "retry_count": 0
    }

    await pusher._push_with_retry(item)

    log_lines = tmp_transfer_log.read_text().strip().split('\n')
    assert len(log_lines) == 1
    assert '"status":"failed"' in log_lines[0]


@pytest.mark.asyncio
async def test_pusher_start_stop(mock_connection, tmp_transfer_log):
    """AsyncPusher processes queue."""
    mock_connection.send_metadata.return_value = True

    pusher = AsyncPusher(mock_connection, tmp_transfer_log)

    await pusher.push_event("ev-1", "checkpoint", {"data": "test"})

    # Start with short timeout
    await pusher.start(timeout=0.5)

    assert mock_connection.send_metadata.called
