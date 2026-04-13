"""Unit tests for POST /sync_event endpoint."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from envelope.middleware.shared.envelopes import SyncEvent
from master.api import create_app


@pytest.fixture
def app():
    """Create test FastAPI app."""
    return create_app()


@pytest.fixture
def client(app):
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def valid_sync_event():
    """Valid SyncEvent for testing."""
    return SyncEvent(
        event_id="evt_abc123",
        event_type="checkpoint_ready",
        payload={"ckp_id": "ckp_001", "metrics": {"loss": 0.1}},
        timestamp_worker=datetime.now(timezone.utc),
        exp_id="exp_001",
    )


class TestSyncEventBasic:
    """Test basic sync event processing."""

    @pytest.mark.asyncio
    async def test_sync_event_process(self, client, valid_sync_event):
        """Process async event from worker daemon."""
        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:

                # Mock repository
                mock_repo = AsyncMock()
                mock_repo.process_sync_event.return_value = None
                mock_neo4j.return_value.repository = mock_repo

                response = client.post(
                    "/sync_event",
                    json=valid_sync_event.model_dump(mode="json"),
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ok"


class TestSyncEventDeduplication:
    """Test idempotent event deduplication by event_id."""

    @pytest.mark.asyncio
    async def test_sync_event_deduplication(
        self, client, valid_sync_event
    ):
        """Sending same event twice should be idempotent (succeeds both times)."""
        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:

                # Mock repository - idempotent: accepts duplicate events
                mock_repo = AsyncMock()
                # Simply return None for all calls (idempotent behavior)
                mock_repo.process_sync_event.return_value = None
                mock_neo4j.return_value.repository = mock_repo

                # First event
                response1 = client.post(
                    "/sync_event",
                    json=valid_sync_event.model_dump(mode="json"),
                )
                assert response1.status_code == 200

                # Second event (duplicate) - should succeed (idempotent)
                response2 = client.post(
                    "/sync_event",
                    json=valid_sync_event.model_dump(mode="json"),
                )
                # Should succeed (idempotent deduplication at endpoint level)
                assert response2.status_code == 200


class TestSyncEventTypes:
    """Test different event types."""

    @pytest.mark.asyncio
    async def test_sync_event_checkpoint_ready(self, client):
        """Process 'checkpoint_ready' event type."""
        event = SyncEvent(
            event_id="evt_001",
            event_type="checkpoint_ready",
            payload={"ckp_id": "ckp_001"},
            timestamp_worker=datetime.now(timezone.utc),
            exp_id="exp_001",
        )

        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:
                mock_repo = AsyncMock()
                mock_repo.process_sync_event.return_value = None
                mock_neo4j.return_value.repository = mock_repo

                response = client.post(
                    "/sync_event",
                    json=event.model_dump(mode="json"),
                )

                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_sync_event_training_completed(self, client):
        """Process 'training_completed' event type."""
        event = SyncEvent(
            event_id="evt_002",
            event_type="training_completed",
            payload={"final_epoch": 20, "final_loss": 0.05},
            timestamp_worker=datetime.now(timezone.utc),
            exp_id="exp_001",
        )

        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:
                mock_repo = AsyncMock()
                mock_repo.process_sync_event.return_value = None
                mock_neo4j.return_value.repository = mock_repo

                response = client.post(
                    "/sync_event",
                    json=event.model_dump(mode="json"),
                )

                assert response.status_code == 200


class TestSyncEventErrors:
    """Test error scenarios."""

    def test_sync_event_invalid_request(self, client):
        """400 Bad Request: missing required fields."""
        response = client.post(
            "/sync_event",
            json={
                "event_id": "evt_001",
                # Missing event_type, timestamp_worker, exp_id
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_sync_event_malformed_timestamp(self, client):
        """400 Bad Request: invalid timestamp."""
        response = client.post(
            "/sync_event",
            json={
                "event_id": "evt_001",
                "event_type": "checkpoint_ready",
                "payload": {},
                "timestamp_worker": "not-a-timestamp",  # Invalid
                "exp_id": "exp_001",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_sync_event_experiment_not_found(self, client, valid_sync_event):
        """400/404: experiment reference doesn't exist."""
        event = valid_sync_event.model_copy()
        event.exp_id = "exp_nonexistent"

        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:

                mock_repo = AsyncMock()
                mock_repo.process_sync_event.side_effect = Exception("Experiment not found")
                mock_neo4j.return_value.repository = mock_repo

                response = client.post(
                    "/sync_event",
                    json=event.model_dump(mode="json"),
                )

                assert response.status_code == 500


class TestSyncEventManualSpans:
    """Test manual span instrumentation."""

    def test_sync_event_spans_created(self, client, valid_sync_event):
        """Verify manual spans are created."""
        with patch("master.api.get_tracer") as mock_tracer:
            mock_span = MagicMock()
            mock_tracer.return_value.start_as_current_span.return_value.__enter__ = MagicMock(
                return_value=mock_span
            )
            mock_tracer.return_value.start_as_current_span.return_value.__exit__ = MagicMock(
                return_value=None
            )

            with patch("master.neo4j.client.Neo4jClient.get_instance"):
                response = client.post(
                    "/sync_event",
                    json=valid_sync_event.model_dump(mode="json"),
                )

            # Verify span context manager was called
            assert mock_tracer.return_value.start_as_current_span.called
