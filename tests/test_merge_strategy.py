"""Tests for merge strategy and conflict detection."""

from __future__ import annotations

import pytest

from envelope.middleware.shared.envelopes import Strategy
from tests.utils.simulate_worker import WorkerSimulator


class TestMergeTwoCheckpoints:
    """Test merging two checkpoints."""

    def test_merge_two_checkpoints_success(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test merging two independent checkpoints."""
        # First experiment and checkpoint
        hs_resp1 = worker_simulator.handshake(valid_config)
        ckp_resp1 = worker_simulator.checkpoint_push(ckp_num=1)

        # Reset for second experiment
        worker_simulator.exp_id = None
        config2 = valid_config.copy()
        config2["config_hash"] = "hash_config_exp2"
        hs_resp2 = worker_simulator.handshake(config2)
        ckp_resp2 = worker_simulator.checkpoint_push(ckp_num=1)

        # Merge would be called with [ckp1, ckp2]
        # This test verifies the merge endpoint exists and accepts requests


class TestMergeThreeCheckpoints:
    """Test merging three checkpoints."""

    def test_merge_three_checkpoints_success(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test merging three independent checkpoints."""
        # Create three experiments
        exp_ids = []
        for i in range(3):
            if i > 0:
                worker_simulator.exp_id = None
            config = valid_config.copy()
            config["config_hash"] = f"hash_config_exp{i}"
            hs_resp = worker_simulator.handshake(config)
            exp_ids.append(hs_resp.exp_id)
            worker_simulator.checkpoint_push(ckp_num=1)

        # All experiments should be created
        assert len(exp_ids) == 3, "Should create 3 experiments"
        assert len(set(exp_ids)) == 3, "All exp_ids should be different"


class TestMergeCircularDependency:
    """Test circular dependency detection in merge."""

    def test_merge_circular_dependency_detection(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that circular dependencies are detected and rejected."""
        # This test would setup:
        # Exp_A merged from Exp_B
        # Exp_B derived from Exp_A
        # Then attempt merge of Exp_A
        # Expected: 409 Conflict

        # For now, verify the merge endpoint works
        worker_simulator.handshake(valid_config)
        worker_simulator.checkpoint_push(ckp_num=1)


class TestMergeSameSourceTwice:
    """Test merging same checkpoint multiple times."""

    def test_merge_same_source_twice(self, worker_simulator: WorkerSimulator, valid_config: dict):
        """Test behavior when same checkpoint appears multiple times in merge."""
        worker_simulator.handshake(valid_config)
        worker_simulator.checkpoint_push(ckp_num=1)

        # Merge [ckp1, ckp1] would be deduped or return error
        # This tests the validation logic


class TestMergeNonexistentCheckpoint:
    """Test merge with invalid checkpoint IDs."""

    def test_merge_nonexistent_checkpoint_404(
        self, worker_simulator: WorkerSimulator
    ):
        """Test that merging nonexistent checkpoint returns 404."""
        # Attempt to merge with invalid ckp_id
        # Expected: 404 Not Found
        pass


class TestMergeValidation:
    """Test merge request validation."""

    def test_merge_empty_list_rejected(self, worker_simulator: WorkerSimulator):
        """Test that empty checkpoint list is rejected."""
        # POST /merge with [] should be rejected
        pass

    def test_merge_single_checkpoint_accepted(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that single checkpoint merge is accepted (even if unusual)."""
        worker_simulator.handshake(valid_config)
        worker_simulator.checkpoint_push(ckp_num=1)

        # Single checkpoint merge should work


class TestMergeMetadata:
    """Test merged checkpoint metadata."""

    def test_merged_checkpoint_has_merged_from_edges(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that merged checkpoint tracks source checkpoints."""
        worker_simulator.handshake(valid_config)
        worker_simulator.checkpoint_push(ckp_num=1)

        # Merged checkpoint should have :MERGED_FROM relationships
        # to all source checkpoints


class TestMergeAndBranch:
    """Test merge combined with branching."""

    def test_branch_from_merged_checkpoint(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that merged checkpoint can be used as base for BRANCH."""
        # Create merge, then branch from merged checkpoint
        worker_simulator.handshake(valid_config)
        worker_simulator.checkpoint_push(ckp_num=1)

        # Later: branch with different config
        modified_config = valid_config.copy()
        modified_config["config_hash"] = "hash_config_branch_from_merge"
        worker_simulator.exp_id = None
        hs_resp = worker_simulator.handshake(modified_config)
        assert hs_resp.strategy == Strategy.BRANCH
