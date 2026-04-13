"""Unit tests for POST /handshake endpoint with all 4 strategy paths."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from envelope.middleware.shared.config_hasher import ConfigSnapshot
from envelope.middleware.shared.envelopes import HandshakeRequest, Strategy
from envelope.middleware.shared.nodes import ExperimentNode
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
def valid_handshake_request():
    """Valid HandshakeRequest for testing."""
    return HandshakeRequest(
        config_hash="hash_config_abc",
        req_hash="hash_req_xyz",
        code_hash="hash_code_def",
        scaffold_path="/path/to/scaffold",
        recipe_id="recipe_123",
        model_id="llama-7b",
        config_text="config: test",
        train_text="training: test",
        requirements_text="torch==2.0",
        rewards_texts=["reward1"],
        rewards_filenames=["reward.py"],
    )


@pytest.fixture
def config_snapshot():
    """ConfigSnapshot for testing."""
    return ConfigSnapshot(
        snapshot_id="hash_abc123",
        files={
            "config.yaml": "hash_config_abc",
            "train.py": "hash_code_def",
            "requirements.txt": "hash_req_xyz",
        },
        aggregated_hash="hash_abc123",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def experiment_node():
    """ExperimentNode for mocking."""
    return ExperimentNode(
        id="node_exp_existing_001",
        exp_id="exp_existing_001",
        recipe_id="recipe_123",
        model_id="llama-7b",
        status="RUNNING",
        created_at=datetime.now(timezone.utc),
    )


class TestHandshakeStrategyNEW:
    """Test NEW strategy when no existing experiment matches."""

    @pytest.mark.asyncio
    async def test_handshake_new_strategy_no_existing(
        self, client, valid_handshake_request
    ):
        """NEW strategy: no existing experiment with matching hashes."""
        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j, \
                 patch("master.storage.resolver.URIResolver") as mock_storage:

                # Mock repository
                mock_repo = AsyncMock()
                mock_repo.find_experiment_by_hashes.return_value = None
                mock_neo4j.return_value.repository = mock_repo

                response = client.post(
                    "/handshake",
                    json=valid_handshake_request.model_dump(),
                )

                assert response.status_code == 200
                data = response.json()
                assert data["strategy"] == Strategy.NEW.value
                assert data["exp_id"]  # Generated new exp_id


class TestHandshakeStrategyRESUME:
    """Test RESUME strategy when experiment exists with latest checkpoint."""

    @pytest.mark.asyncio
    async def test_handshake_resume_strategy(
        self, client, valid_handshake_request, experiment_node, config_snapshot
    ):
        """RESUME strategy: experiment exists, previous checkpoint available."""
        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:

                # Mock repository
                mock_repo = AsyncMock()
                mock_repo.find_experiment_by_hashes.return_value = experiment_node
                mock_repo.get_latest_checkpoint.return_value = MagicMock(
                    ckp_id="ckp_previous_001",
                    uri="file:///checkpoints/ckp_001.pt",
                )
                mock_neo4j.return_value.repository = mock_repo

                response = client.post(
                    "/handshake",
                    json=valid_handshake_request.model_dump(),
                )

                assert response.status_code == 200
                data = response.json()
                assert data["strategy"] == Strategy.RESUME.value
                assert data["exp_id"] == experiment_node.exp_id
                assert data.get("base_checkpoint_uri") == "file:///checkpoints/ckp_001.pt"


class TestHandshakeStrategyBRANCH:
    """Test BRANCH strategy when config hash changed (divergent experiment)."""

    @pytest.mark.asyncio
    async def test_handshake_branch_strategy_config_changed(
        self, client, valid_handshake_request, experiment_node, config_snapshot
    ):
        """BRANCH strategy: config hash differs from base experiment."""
        # Modify config hash to trigger BRANCH
        branch_request = valid_handshake_request.model_copy()
        branch_request.base_exp_id = experiment_node.exp_id
        branch_request.config_hash = "hash_config_new_diff"  # Different config

        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:

                # Mock repository
                mock_repo = AsyncMock()
                # For find_experiment_by_hashes with new config: no match (returns None from the old config search)
                # But when searching by base_exp_id later, find the experiment
                # Actually: for BRANCH to work, existing_exp must be not None
                # So mock find_experiment_by_hashes to return experiment_node
                # This simulates finding an experiment with the base config
                mock_repo.find_experiment_by_hashes.return_value = experiment_node
                mock_repo.create_derived_from_relation.return_value = None
                mock_neo4j.return_value.repository = mock_repo

                response = client.post(
                    "/handshake",
                    json=branch_request.model_dump(),
                )

                assert response.status_code == 200
                data = response.json()
                assert data["strategy"] == Strategy.BRANCH.value


class TestHandshakeStrategyRETRY:
    """Test RETRY strategy when config unchanged but different seed/hardware."""

    @pytest.mark.asyncio
    async def test_handshake_retry_strategy_config_unchanged(
        self, client, valid_handshake_request, experiment_node, config_snapshot
    ):
        """RETRY strategy: config same, but explicit retry requested."""
        # Set base_exp_id and checkpoint_id_to_resume to trigger RETRY
        retry_request = valid_handshake_request.model_copy()
        retry_request.base_exp_id = experiment_node.exp_id
        retry_request.checkpoint_id_to_resume = "ckp_existing_001"

        with patch("master.api.get_tracer"):
            with patch("master.neo4j.client.Neo4jClient.get_instance") as mock_neo4j:

                # Mock repository
                mock_repo = AsyncMock()
                mock_repo.find_experiment_by_hashes.return_value = experiment_node
                mock_repo.create_retry_from_relation.return_value = None
                mock_neo4j.return_value.repository = mock_repo

                response = client.post(
                    "/handshake",
                    json=retry_request.model_dump(),
                )

                assert response.status_code == 200
                data = response.json()
                assert data["strategy"] == Strategy.RETRY.value


class TestHandshakeErrors:
    """Test error scenarios."""

    def test_handshake_invalid_request_missing_fields(self, client):
        """400 Bad Request: missing required fields."""
        response = client.post(
            "/handshake",
            json={
                "config_hash": "abc",
                # Missing other required fields
            },
        )
        assert response.status_code == 422  # Validation error


    def test_handshake_rewards_mismatch(self, client):
        """400 Bad Request: rewards texts and filenames length mismatch."""
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
                "rewards_filenames": ["file1"],  # Mismatched!
            },
        )
        assert response.status_code == 422


class TestHandshakeManualSpans:
    """Test manual span instrumentation."""

    def test_handshake_spans_created(self, client, valid_handshake_request):
        """Verify manual spans are created for handshake."""
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
                    "/handshake",
                    json=valid_handshake_request.model_dump(),
                )

            # Verify span context manager was called
            assert mock_tracer.return_value.start_as_current_span.called
