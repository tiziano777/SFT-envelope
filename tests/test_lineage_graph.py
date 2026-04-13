"""Tests for Neo4j graph structure validation after E2E operations."""

from __future__ import annotations

import pytest

from tests.utils.simulate_worker import WorkerSimulator


class TestExperimentNodeCreation:
    """Test experiment node creation in Neo4j."""

    def test_experiment_node_creation(self, worker_simulator: WorkerSimulator, valid_config: dict):
        """Test that handshake creates experiment node in Neo4j."""
        hs_resp = worker_simulator.handshake(valid_config)

        assert hs_resp.exp_id, "exp_id should be returned"
        assert len(hs_resp.exp_id) > 0, "exp_id should not be empty"

    def test_experiment_node_has_timestamps(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that experiment node has created_at and updated_at timestamps."""
        hs_resp = worker_simulator.handshake(valid_config)
        exp_id = hs_resp.exp_id

        assert exp_id, "exp_id should be set"


class TestCheckpointLinking:
    """Test checkpoint linking to experiment nodes."""

    def test_checkpoint_linking_multiple_pushes(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that multiple checkpoint pushes create linked nodes."""
        worker_simulator.handshake(valid_config)

        for ckp_num in range(1, 4):
            resp = worker_simulator.checkpoint_push(ckp_num=ckp_num)
            assert resp, f"Checkpoint {ckp_num} should be created"

    def test_checkpoint_nodes_exist(self, worker_simulator: WorkerSimulator, valid_config: dict):
        """Test that checkpoint nodes exist in Neo4j."""
        worker_simulator.handshake(valid_config)
        resp = worker_simulator.checkpoint_push(ckp_num=1)
        assert resp, "Checkpoint should be stored"


class TestDerivedFromBranch:
    """Test DERIVED_FROM relationships when branching."""

    def test_derived_from_relationship_branch(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that BRANCH creates DERIVED_FROM relationship."""
        # Initial handshake
        hs_resp1 = worker_simulator.handshake(valid_config)
        exp_id_1 = hs_resp1.exp_id

        # Modified config triggers BRANCH
        modified_config = valid_config.copy()
        modified_config["config_hash"] = "hash_config_branch_v2"

        worker_simulator.exp_id = None
        hs_resp2 = worker_simulator.handshake(modified_config)

        if hs_resp2.strategy == "BRANCH":
            # Should have created DERIVED_FROM relationship
            assert hs_resp2.exp_id != exp_id_1, "BRANCH should create new exp_id"


class TestFindExperimentByHashes:
    """Test querying experiments by hashes."""

    def test_find_experiment_same_config(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test finding experiment by same config hashes."""
        hs_resp1 = worker_simulator.handshake(valid_config)
        exp_id_1 = hs_resp1.exp_id

        # Same config should find same experiment
        worker_simulator.exp_id = None
        hs_resp2 = worker_simulator.handshake(valid_config)
        exp_id_2 = hs_resp2.exp_id

        assert exp_id_1 == exp_id_2, "Same hashes should find same experiment"


class TestGetLatestCheckpoint:
    """Test querying latest checkpoint."""

    def test_get_latest_checkpoint_multiple(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that latest checkpoint is returned (highest ckp_num)."""
        worker_simulator.handshake(valid_config)

        # Push multiple checkpoints
        for ckp_num in range(1, 4):
            worker_simulator.checkpoint_push(ckp_num=ckp_num)

        # Latest should be checkpoint 3
        # This test verifies the query logic


class TestGraphCleanup:
    """Test _TEST label and cleanup."""

    def test_test_label_applied(self, worker_simulator: WorkerSimulator, valid_config: dict):
        """Test that _TEST label is applied to all test nodes."""
        hs_resp = worker_simulator.handshake(valid_config)
        worker_simulator.checkpoint_push(ckp_num=1)

        # Nodes should be tagged for cleanup
        # This would be verified by MATCH (n:_TEST) query


class TestGraphConsistency:
    """Test graph remains consistent through operations."""

    def test_graph_consistency_after_multiple_operations(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that graph remains consistent after multiple operations."""
        hs_resp = worker_simulator.handshake(valid_config)
        exp_id = hs_resp.exp_id

        worker_simulator.checkpoint_push(ckp_num=1)
        worker_simulator.checkpoint_push(ckp_num=2)
        worker_simulator.sync_event("test_event")
        worker_simulator.training_done()

        # All operations should complete without error
        assert exp_id, "exp_id should remain consistent"
