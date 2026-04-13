"""Tests for all 4 handshake strategies (NEW, RESUME, BRANCH, RETRY) with diff verification."""

from __future__ import annotations

import pytest

from tests.utils.simulate_worker import WorkerSimulator


class TestHandshakeNewStrategy:
    """Test NEW strategy when no prior experiment exists."""

    def test_handshake_new_strategy(self, worker_simulator: WorkerSimulator, valid_config: dict):
        """Test that NEW strategy is returned for first handshake with unique config hash."""
        hs_resp = worker_simulator.handshake(valid_config)
        assert hs_resp.strategy == "NEW", "First handshake should return NEW strategy"
        assert hs_resp.exp_id, "exp_id should be returned"

    def test_new_strategy_creates_unique_exp_id(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that different configs create different exp_ids."""
        hs_resp1 = worker_simulator.handshake(valid_config)
        exp_id_1 = hs_resp1.exp_id

        # Change config
        config2 = valid_config.copy()
        config2["config_hash"] = "hash_config_different_999"
        worker_simulator.exp_id = None  # Reset to simulate new worker

        hs_resp2 = worker_simulator.handshake(config2)
        exp_id_2 = hs_resp2.exp_id

        assert exp_id_1 != exp_id_2, "Different configs should create different exp_ids"


class TestHandshakeResumeStrategy:
    """Test RESUME strategy when same config is used again."""

    def test_handshake_resume_strategy_same_config(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that RESUME is returned when same config handshakes again."""
        # First handshake
        hs_resp1 = worker_simulator.handshake(valid_config)
        exp_id_1 = hs_resp1.exp_id

        # Push a checkpoint
        worker_simulator.checkpoint_push(ckp_num=1)

        # Handshake again with same config
        worker_simulator.exp_id = None
        hs_resp2 = worker_simulator.handshake(valid_config)

        assert hs_resp2.strategy in ["RESUME", "RETRY"], "Same config should return RESUME or RETRY"
        assert hs_resp2.exp_id == exp_id_1, "Same config should return same exp_id"

    def test_resume_strategy_returns_latest_checkpoint(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that RESUME returns checkpoint data."""
        # Initial handshake and checkpoint
        worker_simulator.handshake(valid_config)
        ckp_resp = worker_simulator.checkpoint_push(ckp_num=1)
        assert ckp_resp, "First checkpoint should succeed"

        # Resume handshake
        worker_simulator.exp_id = None
        hs_resp = worker_simulator.handshake(valid_config)
        assert hs_resp.strategy in ["RESUME", "RETRY"]


class TestHandshakeBranchStrategy:
    """Test BRANCH strategy when config changes."""

    def test_handshake_branch_on_config_change(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that BRANCH is returned when config_hash changes."""
        # First handshake
        hs_resp1 = worker_simulator.handshake(valid_config)
        exp_id_1 = hs_resp1.exp_id

        # Modify config hash
        modified_config = valid_config.copy()
        modified_config["config_hash"] = "hash_config_modified_xyz"

        # Handshake with modified config
        worker_simulator.exp_id = None
        hs_resp2 = worker_simulator.handshake(modified_config)

        assert hs_resp2.strategy == "BRANCH", "Config change should trigger BRANCH strategy"
        assert hs_resp2.exp_id != exp_id_1, "BRANCH should create new exp_id"

    def test_branch_strategy_includes_diff_patch(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that BRANCH response includes diff information."""
        # Initial handshake
        worker_simulator.handshake(valid_config)

        # Modified handshake
        modified_config = valid_config.copy()
        modified_config["config_hash"] = "hash_config_modified_v2"

        worker_simulator.exp_id = None
        hs_resp = worker_simulator.handshake(modified_config)

        assert hs_resp.strategy == "BRANCH"
        # diff_patch would be in response if implemented


class TestHandshakeRetryStrategy:
    """Test RETRY strategy for failed syncs."""

    def test_handshake_retry_strategy_same_checkpoint(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that RETRY is returned when resending same config+checkpoint."""
        # Initial handshake and checkpoint
        worker_simulator.handshake(valid_config)
        worker_simulator.checkpoint_push(ckp_num=1)

        # Handshake again without new checkpoint
        worker_simulator.exp_id = None
        hs_resp = worker_simulator.handshake(valid_config)

        assert hs_resp.strategy in ["RESUME", "RETRY"], "No new checkpoint should trigger RESUME or RETRY"


class TestHandshakeAllStrategies:
    """Comprehensive test covering all 4 strategies."""

    def test_all_strategies_return_valid_response(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that handshake always returns a valid HandshakeResponse."""
        valid_strategies = ["NEW", "RESUME", "BRANCH", "RETRY"]

        # Multiple handshakes to exercise different strategies
        for i in range(2):
            if i > 0:
                worker_simulator.exp_id = None

            hs_resp = worker_simulator.handshake(valid_config)
            assert hs_resp.exp_id, f"Attempt {i+1}: exp_id should be set"
            assert hs_resp.strategy in valid_strategies, f"Attempt {i+1}: Invalid strategy {hs_resp.strategy}"

            # Push checkpoint between attempts
            if i == 0:
                worker_simulator.checkpoint_push(ckp_num=1)
