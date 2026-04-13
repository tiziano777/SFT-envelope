"""Unit tests for POST /checkpoint_push endpoint."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from envelope.middleware.shared.envelopes import CheckpointPush
from envelope.middleware.shared.nodes import CheckpointNode, ExperimentNode
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
def valid_checkpoint_push():
    """Valid CheckpointPush for testing."""
    return CheckpointPush(
        exp_id="exp_001",
        ckp_id="ckp_epoch10_001",
        epoch=10,
        run=1,
        metrics_snapshot={"loss": 0.123, "accuracy": 0.95},
        uri="file:///checkpoints/ckp_epoch10_001.pt",
        is_usable=True,
        transfer_policy="ALL",
    )


@pytest.fixture
def checkpoint_node():
    """CheckpointNode for mocking."""
    return CheckpointNode(
        id="node_ckp_epoch10_001",
        ckp_id="ckp_epoch10_001",
        exp_id="exp_001",
        epoch=10,
        run=1,
        metrics_snapshot={"loss": 0.123, "accuracy": 0.95},
        uri="file:///checkpoints/ckp_epoch10_001.pt",
        is_usable=True,
        created_at=datetime.now(timezone.utc),
    )


class TestCheckpointPushBasic:
    """Test basic checkpoint push operations."""

    @pytest.mark.asyncio
    async def test_checkpoint_push_success(self, client, valid_checkpoint_push):
        """Successfully push checkpoint."""
        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j, \
                 patch("master.storage.resolver.URIResolver") as mock_storage:

                # Mock repository
                mock_repo = AsyncMock()
                mock_repo.upsert_checkpoint.return_value = CheckpointNode(
                    id="node_ckp_test_001",
                    ckp_id=valid_checkpoint_push.ckp_id,
                    exp_id=valid_checkpoint_push.exp_id,
                    epoch=valid_checkpoint_push.epoch,
                    run=valid_checkpoint_push.run,
                    metrics_snapshot=valid_checkpoint_push.metrics_snapshot,
                    uri=valid_checkpoint_push.uri,
                    is_usable=valid_checkpoint_push.is_usable,
                    created_at=datetime.now(timezone.utc),
                )
                mock_neo4j.return_value.repository = mock_repo

                # Mock storage
                mock_storage.return_value.file_exists.return_value = True

                response = client.post(
                    "/checkpoint_push",
                    json=valid_checkpoint_push.model_dump(),
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ok"
                assert data["checkpoint_id"] == valid_checkpoint_push.ckp_id


class TestCheckpointPushIdempotency:
    """Test idempotent checkpoint push (same request twice = no duplicate)."""

    @pytest.mark.asyncio
    async def test_checkpoint_push_idempotent(
        self, client, valid_checkpoint_push, checkpoint_node
    ):
        """Pushing same checkpoint twice should not create duplicate."""
        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:

                # Mock repository - returns same node both times
                mock_repo = AsyncMock()
                mock_repo.upsert_checkpoint.return_value = checkpoint_node
                mock_neo4j.return_value.repository = mock_repo

                # First push
                response1 = client.post(
                    "/checkpoint_push",
                    json=valid_checkpoint_push.model_dump(),
                )
                assert response1.status_code == 200

                # Second push (identical)
                response2 = client.post(
                    "/checkpoint_push",
                    json=valid_checkpoint_push.model_dump(),
                )
                assert response2.status_code == 200

                # Verify upsert was called exactly twice (idempotent behavior)
                assert mock_repo.upsert_checkpoint.call_count == 2


class TestCheckpointPushArtifacts:
    """Test artifact handling in checkpoint push."""

    @pytest.mark.asyncio
    async def test_checkpoint_push_with_artifact(
        self, client, valid_checkpoint_push
    ):
        """Checkpoint push with artifact URI."""
        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j, \
                 patch("master.api.URIResolver") as mock_storage_cls:

                # Mock repository
                mock_repo = AsyncMock()
                mock_repo.upsert_checkpoint.return_value = MagicMock(
                    ckp_id=valid_checkpoint_push.ckp_id,
                )
                mock_neo4j.return_value.repository = mock_repo

                # Mock storage instance and file_exists method
                mock_storage_instance = MagicMock()
                mock_storage_instance.file_exists.return_value = True
                mock_storage_cls.return_value = mock_storage_instance

                response = client.post(
                    "/checkpoint_push",
                    json=valid_checkpoint_push.model_dump(),
                )

                assert response.status_code == 200
                # Verify file_exists was called with the URI
                mock_storage_instance.file_exists.assert_called_with(valid_checkpoint_push.uri)


    @pytest.mark.asyncio
    async def test_checkpoint_push_without_artifact(self, client):
        """Checkpoint push without artifact (optional uri)."""
        checkpoint_no_artifact = CheckpointPush(
            exp_id="exp_001",
            ckp_id="ckp_epoch10_001",
            epoch=10,
            run=1,
            metrics_snapshot={"loss": 0.123},
            uri=None,  # No artifact
            is_usable=True,
        )

        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:

                # Mock repository
                mock_repo = AsyncMock()
                mock_repo.upsert_checkpoint.return_value = MagicMock()
                mock_neo4j.return_value.repository = mock_repo

                response = client.post(
                    "/checkpoint_push",
                    json=checkpoint_no_artifact.model_dump(),
                )

                assert response.status_code == 200


class TestCheckpointPushErrors:
    """Test error scenarios."""

    def test_checkpoint_push_invalid_request(self, client):
        """400 Bad Request: missing required fields."""
        response = client.post(
            "/checkpoint_push",
            json={
                "exp_id": "exp_001",
                # Missing ckp_id
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_checkpoint_push_repo_error(
        self, client, valid_checkpoint_push
    ):
        """500 error when repository fails."""
        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:

                # Mock repository to raise error
                mock_repo = AsyncMock()
                mock_repo.upsert_checkpoint.side_effect = Exception("DB connection failed")
                mock_neo4j.return_value.repository = mock_repo

                response = client.post(
                    "/checkpoint_push",
                    json=valid_checkpoint_push.model_dump(),
                )

                assert response.status_code == 500


class TestCheckpointPushManualSpans:
    """Test manual span instrumentation."""

    def test_checkpoint_push_spans_created(self, client, valid_checkpoint_push):
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
                    "/checkpoint_push",
                    json=valid_checkpoint_push.model_dump(),
                )

            # Verify span context manager was called
            assert mock_tracer.return_value.start_as_current_span.called
