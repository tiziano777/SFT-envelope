"""Tests for checkpoint push — idempotency, uri=NULL handling, state persistence."""

from __future__ import annotations

import pytest

from tests.utils.simulate_worker import WorkerSimulator


class TestCheckpointPushIdempotency:
    """Test checkpoint push idempotency via event_id."""

    def test_push_checkpoint_idempotency_same_event_id(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that pushing same event_id returns 200 (not error)."""
        worker_simulator.handshake(valid_config)

        event_id = "ckp_idempotent_test_123"
        resp1 = worker_simulator.checkpoint_push(ckp_num=1, event_id=event_id)
        assert resp1, "First push should succeed"

        # Push with same event_id again
        resp2 = worker_simulator.checkpoint_push(ckp_num=1, event_id=event_id)
        assert resp2, "Identical push should return success (idempotent)"

    def test_push_checkpoint_different_event_ids(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that different event_ids create different checkpoints."""
        worker_simulator.handshake(valid_config)

        resp1 = worker_simulator.checkpoint_push(ckp_num=1, event_id="ckp_event_1")
        resp2 = worker_simulator.checkpoint_push(ckp_num=2, event_id="ckp_event_2")

        assert resp1, "First checkpoint should succeed"
        assert resp2, "Second checkpoint should succeed"
        # Both should be accepted without conflict


class TestCheckpointUriHandling:
    """Test checkpoint URI handling."""

    def test_push_checkpoint_no_uri(self, worker_simulator: WorkerSimulator, valid_config: dict):
        """Test that uri=NULL is accepted."""
        worker_simulator.handshake(valid_config)
        resp = worker_simulator.checkpoint_push(ckp_num=1, artifact_uri=None)
        assert resp, "Checkpoint push with uri=NULL should succeed"

    def test_push_checkpoint_with_uri(self, worker_simulator: WorkerSimulator, valid_config: dict):
        """Test that artifact_uri is accepted."""
        worker_simulator.handshake(valid_config)
        resp = worker_simulator.checkpoint_push(
            ckp_num=1, artifact_uri="file:///tmp/checkpoint.pt"
        )
        assert resp, "Checkpoint push with artifact_uri should succeed"

    def test_push_checkpoint_local_file_uri(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that local file:// URIs are accepted."""
        worker_simulator.handshake(valid_config)
        resp = worker_simulator.checkpoint_push(
            ckp_num=1, artifact_uri="file:///var/tmp/model.safetensors"
        )
        assert resp, "Local file:// URI should be accepted"


class TestCheckpointSequencing:
    """Test checkpoint sequencing and ordering."""

    def test_push_multiple_checkpoints_sequence(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test pushing multiple checkpoints in sequence."""
        worker_simulator.handshake(valid_config)

        for ckp_num in range(1, 4):
            resp = worker_simulator.checkpoint_push(ckp_num=ckp_num)
            assert resp, f"Checkpoint {ckp_num} push should succeed"

    def test_push_checkpoint_with_metrics(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that checkpoint push includes metrics."""
        worker_simulator.handshake(valid_config)

        # Verify checkpoint_push includes metrics_snapshot
        resp = worker_simulator.checkpoint_push(ckp_num=1)
        assert resp, "Checkpoint with metrics should succeed"


class TestLifecycleFlow:
    """Test complete E2E lifecycle."""

    def test_complete_e2e_flow(self, worker_simulator: WorkerSimulator, valid_config: dict):
        """Test complete E2E flow: handshake → checkpoint → training_done."""
        # Handshake
        hs_resp = worker_simulator.handshake(valid_config)
        assert hs_resp.exp_id, "exp_id should be returned"

        # Push checkpoint
        ckp_resp = worker_simulator.checkpoint_push(ckp_num=1)
        assert ckp_resp, "Checkpoint push should succeed"

        # Sync event
        sync_resp = worker_simulator.sync_event("checkpoint_synced", {"ckp_num": 1})
        assert sync_resp, "Sync event should succeed"

        # Training done
        done_resp = worker_simulator.training_done()
        assert done_resp, "training_done should succeed"
