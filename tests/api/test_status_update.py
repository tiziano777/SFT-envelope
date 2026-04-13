"""Unit tests for POST /status_update endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from envelope.middleware.shared.envelopes import StatusUpdate
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
def valid_status_update():
    """Valid StatusUpdate for testing."""
    return StatusUpdate(
        exp_id="exp_001",
        checkpoint_id="ckp_epoch10_001",
        status="training",
        metrics={"loss": 0.123},
    )


class TestStatusUpdateBasic:
    """Test basic status update operations."""

    @pytest.mark.asyncio
    async def test_status_update_training(self, client, valid_status_update):
        """Update experiment status to training."""
        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:

                # Mock repository
                mock_repo = AsyncMock()
                mock_repo.update_experiment_status.return_value = None
                mock_neo4j.return_value.repository = mock_repo

                response = client.post(
                    "/status_update",
                    json=valid_status_update.model_dump(),
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ok"


    @pytest.mark.asyncio
    async def test_status_update_done(self, client):
        """Update experiment status to done (lifecycle completion)."""
        status_update = StatusUpdate(
            exp_id="exp_001",
            checkpoint_id=None,
            status="done",
            metrics={"final_loss": 0.05},
        )

        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:

                # Mock repository
                mock_repo = AsyncMock()
                mock_repo.update_experiment_status.return_value = None
                mock_neo4j.return_value.repository = mock_repo

                response = client.post(
                    "/status_update",
                    json=status_update.model_dump(),
                )

                assert response.status_code == 200


    @pytest.mark.asyncio
    async def test_status_update_failed_with_error(self, client):
        """Update experiment status to failed with error message."""
        status_update = StatusUpdate(
            exp_id="exp_001",
            checkpoint_id=None,
            status="failed",
            error_message="CUDA out of memory",
        )

        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:

                # Mock repository
                mock_repo = AsyncMock()
                mock_repo.update_experiment_status.return_value = None
                mock_neo4j.return_value.repository = mock_repo

                response = client.post(
                    "/status_update",
                    json=status_update.model_dump(),
                )

                assert response.status_code == 200


class TestStatusUpdateLifecycle:
    """Test experiment lifecycle transitions."""

    @pytest.mark.asyncio
    async def test_status_update_transition_setup_to_training(self, client):
        """Transition from setup → training."""
        updates = [
            StatusUpdate(exp_id="exp_001", status="setup"),
            StatusUpdate(exp_id="exp_001", status="training"),
        ]

        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:

                mock_repo = AsyncMock()
                mock_repo.update_experiment_status.return_value = None
                mock_neo4j.return_value.repository = mock_repo

                for update in updates:
                    response = client.post(
                        "/status_update",
                        json=update.model_dump(),
                    )
                    assert response.status_code == 200


class TestStatusUpdateErrors:
    """Test error scenarios."""

    def test_status_update_invalid_request(self, client):
        """400 Bad Request: missing required fields."""
        response = client.post(
            "/status_update",
            json={
                "exp_id": "exp_001",
                # Missing status
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_status_update_experiment_not_found(self, client):
        """404 Not Found: experiment doesn't exist."""
        status_update = StatusUpdate(
            exp_id="exp_nonexistent",
            status="training",
        )

        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:

                mock_repo = AsyncMock()
                mock_repo.update_experiment_status.side_effect = Exception("Experiment not found")
                mock_neo4j.return_value.repository = mock_repo

                response = client.post(
                    "/status_update",
                    json=status_update.model_dump(),
                )

                assert response.status_code == 500


class TestStatusUpdateManualSpans:
    """Test manual span instrumentation."""

    def test_status_update_spans_created(self, client, valid_status_update):
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
                    "/status_update",
                    json=valid_status_update.model_dump(),
                )

            # Verify span context manager was called
            assert mock_tracer.return_value.start_as_current_span.called
