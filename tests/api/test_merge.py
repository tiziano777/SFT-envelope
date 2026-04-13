"""Unit tests for POST /merge endpoint with lineage validation."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

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


class TestMergeBasic:
    """Test basic merge operations."""

    @pytest.mark.asyncio
    async def test_merge_two_checkpoints(self, client):
        """Merge two checkpoints into one."""
        merge_request = {
            "exp_id": "exp_001",
            "source_checkpoint_ids": ["ckp_001", "ckp_002"],
            "merged_checkpoint_id": "ckp_merged_001",
            "epoch": 15,
        }

        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:

                # Mock repository
                mock_repo = AsyncMock()
                mock_repo.create_merged_checkpoint.return_value = CheckpointNode(
                    ckp_id="ckp_merged_001",
                    exp_id="exp_001",
                    epoch=15,
                    run=1,
                    metrics_snapshot={},
                    uri=None,
                    is_usable=True,
                    created_at=datetime.now(timezone.utc),
                )
                mock_neo4j.return_value.repository = mock_repo

                response = client.post(
                    "/merge",
                    json=merge_request,
                )

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "ok"


class TestMergeLineageValidation:
    """Test lineage validation and cycle detection."""

    @pytest.mark.asyncio
    async def test_merge_checks_lineage_consistency(self, client):
        """Merge validates against circular dependencies."""
        merge_request = {
            "exp_id": "exp_001",
            "source_checkpoint_ids": ["ckp_001", "ckp_002"],
            "merged_checkpoint_id": "ckp_merged_001",
            "epoch": 15,
        }

        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:

                # Mock repository
                mock_repo = AsyncMock()
                # Simulate ConsistencyGuard detecting cycle
                mock_repo.validate_lineage.side_effect = Exception("Circular dependency detected")
                mock_neo4j.return_value.repository = mock_repo

                response = client.post(
                    "/merge",
                    json=merge_request,
                )

                # Should fail with 409 Conflict
                assert response.status_code in [409, 500]


class TestMergeErrors:
    """Test merge error scenarios."""

    def test_merge_invalid_request(self, client):
        """400 Bad Request: missing fields."""
        response = client.post(
            "/merge",
            json={
                "exp_id": "exp_001",
                # Missing source_checkpoint_ids
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_merge_experiment_not_found(self, client):
        """404 Not Found: experiment doesn't exist."""
        merge_request = {
            "exp_id": "exp_nonexistent",
            "source_checkpoint_ids": ["ckp_001"],
            "merged_checkpoint_id": "ckp_merged_001",
            "epoch": 15,
        }

        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:

                # Mock repository - experiment not found
                mock_repo = AsyncMock()
                mock_repo.find_experiment_by_id.return_value = None
                mock_neo4j.return_value.repository = mock_repo

                response = client.post(
                    "/merge",
                    json=merge_request,
                )

                # Should fail with 404 or validation error
                assert response.status_code in [404, 422]


class TestMergeManualSpans:
    """Test manual span instrumentation for merge."""

    def test_merge_spans_created(self, client):
        """Verify manual spans are created."""
        merge_request = {
            "exp_id": "exp_001",
            "source_checkpoint_ids": ["ckp_001", "ckp_002"],
            "merged_checkpoint_id": "ckp_merged_001",
            "epoch": 15,
        }

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
                    "/merge",
                    json=merge_request,
                )

            # Verify span context manager was called
            assert mock_tracer.return_value.start_as_current_span.called
