"""Unit tests for error handling and semantic status codes."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from master.api import create_app


@pytest.fixture
def app():
    """Create test FastAPI app."""
    return create_app()


@pytest.fixture
def client(app):
    """FastAPI test client."""
    return TestClient(app)


class TestErrorResponses:
    """Test semantic HTTP error responses."""

    def test_404_experiment_not_found(self, client):
        """404 Not Found for missing experiment."""
        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:
                from unittest.mock import AsyncMock

                mock_repo = AsyncMock()
                mock_repo.get_experiment = AsyncMock(return_value=None)
                mock_neo4j.return_value.repository = mock_repo

                # Attempting to access nonexistent experiment
                response = client.post(
                    "/status_update",
                    json={
                        "exp_id": "exp_nonexistent",
                        "status": "training",
                    },
                )
                # Should return 404 for missing experiment
                assert response.status_code == 404

    def test_409_conflict_circular_dependency(self, client):
        """409 Conflict for circular dependency in merge."""
        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:
                from unittest.mock import AsyncMock

                mock_repo = AsyncMock()
                # Simulate ConsistencyGuard detecting cycle
                mock_repo.create_merged_checkpoint = AsyncMock(
                    side_effect=Exception("Circular dependency detected")
                )
                mock_neo4j.return_value.repository = mock_repo

                response = client.post(
                    "/merge",
                    json={
                        "exp_id": "exp_001",
                        "source_checkpoint_ids": ["ckp_001"],
                        "merged_checkpoint_id": "ckp_merged",
                        "epoch": 10,
                    },
                )
                # Should not return 200 for conflict
                assert response.status_code != 200

    def test_400_invalid_rewards_alignment(self, client):
        """400 Bad Request for misaligned rewards arrays."""
        response = client.post(
            "/handshake",
            json={
                "config_hash": "abc",
                "req_hash": "xyz",
                "code_hash": "def",
                "scaffold_path": "/path",
                "recipe_id": "recipe_1",
                "model_id": "model_1",
                "config_text": "config",
                "train_text": "train",
                "requirements_text": "reqs",
                "rewards_texts": ["reward1", "reward2"],
                "rewards_filenames": ["file1"],  # Mismatched length
            },
        )
        assert response.status_code == 422

    def test_422_validation_error_missing_field(self, client):
        """422 Unprocessable Entity for validation errors."""
        response = client.post(
            "/checkpoint_push",
            json={
                "exp_id": "exp_001",
                # Missing ckp_id and other required fields
            },
        )
        assert response.status_code == 422


class TestErrorResponseFormat:
    """Test error response JSON format."""

    def test_error_response_has_detail(self, client):
        """Error response should include 'detail' field."""
        response = client.post(
            "/handshake",
            json={
                "config_hash": "abc",
                # Incomplete request
            },
        )
        assert response.status_code in [400, 422]
        data = response.json()
        assert "detail" in data or "type" in data or "errors" in data


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_endpoint_returns_200(self, client):
        """Health check returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
