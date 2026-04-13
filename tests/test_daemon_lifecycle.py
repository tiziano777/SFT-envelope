"""Tests for daemon lifecycle — startup, shutdown, crash recovery."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from tests.utils.simulate_worker import WorkerSimulator


class TestDaemonBootstrap:
    """Test daemon startup and initialization."""

    def test_daemon_bootstrap_creates_exp_id(self, worker_simulator: WorkerSimulator, valid_config: dict):
        """Test that handshake creates .exp_id file (simulated)."""
        hs_resp = worker_simulator.handshake(valid_config)
        assert hs_resp.exp_id, "exp_id should be returned"
        assert len(hs_resp.exp_id) > 0, "exp_id should not be empty"

    def test_daemon_bootstrap_returns_strategy(self, worker_simulator: WorkerSimulator, valid_config: dict):
        """Test that handshake returns a valid strategy."""
        hs_resp = worker_simulator.handshake(valid_config)
        assert hs_resp.strategy in ["NEW", "RESUME", "BRANCH", "RETRY"], f"Invalid strategy: {hs_resp.strategy}"


class TestDaemonSignalHandling:
    """Test daemon signal handling and graceful shutdown."""

    def test_daemon_accepts_checkpoint_push(self, worker_simulator: WorkerSimulator, valid_config: dict):
        """Test that daemon receives checkpoint push without errors."""
        hs_resp = worker_simulator.handshake(valid_config)
        ckp_resp = worker_simulator.checkpoint_push(ckp_num=1)
        assert ckp_resp, "Checkpoint push should return response"

    def test_daemon_sync_event_succeeds(self, worker_simulator: WorkerSimulator, valid_config: dict):
        """Test that daemon receives sync events."""
        worker_simulator.handshake(valid_config)
        sync_resp = worker_simulator.sync_event("test_event", payload={"data": "test"})
        assert sync_resp, "Sync event should return response"

    def test_daemon_training_done_succeeds(self, worker_simulator: WorkerSimulator, valid_config: dict):
        """Test that daemon receives training_done signal."""
        worker_simulator.handshake(valid_config)
        worker_simulator.checkpoint_push(ckp_num=1)
        training_done_resp = worker_simulator.training_done()
        assert training_done_resp, "training_done should return response"


class TestStatePersistence:
    """Test state persistence and crash recovery."""

    def test_handshake_idempotency_same_config(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that same config returns same exp_id (idempotent)."""
        hs_resp1 = worker_simulator.handshake(valid_config)
        exp_id_1 = hs_resp1.exp_id

        # Reset worker simulator to simulate new process
        worker_simulator.exp_id = None

        hs_resp2 = worker_simulator.handshake(valid_config)
        exp_id_2 = hs_resp2.exp_id

        # Should return same exp_id for same config (RESUME or RETRY strategy)
        assert exp_id_1 == exp_id_2, "Same config should return same exp_id"

    def test_handshake_different_config_new_exp_id(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that different config returns different exp_id."""
        hs_resp1 = worker_simulator.handshake(valid_config)
        exp_id_1 = hs_resp1.exp_id

        # Modify config
        modified_config = valid_config.copy()
        modified_config["config_hash"] = "hash_config_different_xyz"

        hs_resp2 = worker_simulator.handshake(modified_config)
        exp_id_2 = hs_resp2.exp_id

        # Different config should return different exp_id (NEW strategy)
        assert exp_id_1 != exp_id_2, "Different config should return different exp_id"
        assert hs_resp2.strategy == "NEW", "Different config should trigger NEW strategy"
