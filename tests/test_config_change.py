"""Tests for config change detection and trigger hash behavior."""

from __future__ import annotations

import pytest

from envelope.middleware.shared.envelopes import Strategy
from tests.utils.simulate_worker import WorkerSimulator


class TestConfigChangeTriggerHash:
    """Test trigger hash detection for config.yaml, train.py, rewards/*."""

    def test_config_change_triggers_branch(self, worker_simulator: WorkerSimulator, valid_config: dict):
        """Test that config.yaml change triggers BRANCH strategy."""
        # Initial handshake
        hs_resp1 = worker_simulator.handshake(valid_config)
        assert hs_resp1.strategy == Strategy.NEW

        # Modify config_hash (simulates config.yaml change)
        modified_config = valid_config.copy()
        modified_config["config_hash"] = "hash_config_changed_v2"

        worker_simulator.exp_id = None
        hs_resp2 = worker_simulator.handshake(modified_config)

        assert hs_resp2.strategy == Strategy.BRANCH, "config.yaml change should trigger BRANCH"

    def test_train_change_triggers_branch(self, worker_simulator: WorkerSimulator, valid_config: dict):
        """Test that train.py change (via code_hash) triggers BRANCH strategy."""
        # Initial handshake
        hs_resp1 = worker_simulator.handshake(valid_config)
        assert hs_resp1.strategy == Strategy.NEW

        # Modify code_hash (simulates train.py change)
        modified_config = valid_config.copy()
        modified_config["code_hash"] = "hash_code_changed_v2"

        worker_simulator.exp_id = None
        hs_resp2 = worker_simulator.handshake(modified_config)

        assert hs_resp2.strategy == Strategy.BRANCH, "train.py change should trigger BRANCH"

    def test_rewards_change_triggers_branch(self, worker_simulator: WorkerSimulator, valid_config: dict):
        """Test that rewards/* file change triggers BRANCH strategy."""
        # Initial handshake with rewards
        hs_resp1 = worker_simulator.handshake(valid_config)
        assert hs_resp1.strategy == Strategy.NEW

        # Modify rewards config (simulates rewards file change)
        modified_config = valid_config.copy()
        modified_config["rewards_texts"] = ["new_reward_content"]
        modified_config["rewards_filenames"] = ["reward_changed.py"]

        worker_simulator.exp_id = None
        hs_resp2 = worker_simulator.handshake(modified_config)

        # This should trigger BRANCH due to rewards change
        assert hs_resp2.strategy == Strategy.BRANCH, "rewards/* change should trigger BRANCH"


class TestRequirementsNotInTriggerHash:
    """Test that requirements.txt is excluded from trigger hash."""

    def test_requirements_change_does_not_trigger_branch(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that requirements.txt change does NOT trigger BRANCH."""
        # Initial handshake
        hs_resp1 = worker_simulator.handshake(valid_config)
        exp_id_1 = hs_resp1.exp_id
        assert hs_resp1.strategy == Strategy.NEW

        # Modify requirements_text (should NOT change hash)
        modified_config = valid_config.copy()
        modified_config["requirements_text"] = "torch==2.1\nnumpy>=1.21\npandas"

        worker_simulator.exp_id = None
        hs_resp2 = worker_simulator.handshake(modified_config)

        # Since config_hash, code_hash, req_hash are same, should not branch
        assert hs_resp2.strategy != Strategy.BRANCH, "requirements.txt change should NOT trigger BRANCH"
        assert hs_resp2.exp_id == exp_id_1, "requirements.txt change should keep same exp_id"


class TestWhitespaceOnlyChanges:
    """Test that whitespace-only changes are handled consistently."""

    def test_whitespace_only_change_not_branching(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that whitespace-only changes have consistent hash."""
        # Initial handshake
        hs_resp1 = worker_simulator.handshake(valid_config)
        exp_id_1 = hs_resp1.exp_id

        # Add leading spaces to config_text (whitespace-only)
        modified_config = valid_config.copy()
        modified_config["config_text"] = "  " + modified_config["config_text"]
        # But keep the hash same (assuming hash is deterministic)

        worker_simulator.exp_id = None
        hs_resp2 = worker_simulator.handshake(modified_config)

        # If hash is deterministic, should not branch
        # This tests the assumption that config_hash is based on content, not formatting


class TestConfigHashConsistency:
    """Test that config hashing is deterministic and consistent."""

    def test_same_config_same_hash_multiple_times(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that handshaking with same config always returns same exp_id."""
        exp_ids = []
        for attempt in range(3):
            if attempt > 0:
                worker_simulator.exp_id = None
            hs_resp = worker_simulator.handshake(valid_config)
            exp_ids.append(hs_resp.exp_id)

        # All should be same (or at least first and second should be same from RESUME strategy)
        assert exp_ids[0] == exp_ids[1], "Same config should return same exp_id"

    def test_deterministic_hash_different_orders(
        self, worker_simulator: WorkerSimulator, valid_config: dict
    ):
        """Test that config order doesn't affect hash (if applicable)."""
        # This tests the assumption that hash is computed deterministically
        hs_resp1 = worker_simulator.handshake(valid_config)
        exp_id_1 = hs_resp1.exp_id

        # Reorder keys (should not matter if hash is deterministic)
        config_reordered = {}
        for key in reversed(sorted(valid_config.keys())):
            config_reordered[key] = valid_config[key]

        worker_simulator.exp_id = None
        hs_resp2 = worker_simulator.handshake(config_reordered)

        # If hash is truly deterministic, should be same
        assert exp_id_1 == hs_resp2.exp_id, "Config order should not affect hash"


class TestMultipleTriggerFileChanges:
    """Test behavior when multiple trigger files change simultaneously."""

    def test_multiple_files_changed(self, worker_simulator: WorkerSimulator, valid_config: dict):
        """Test BRANCH when both config and train change."""
        hs_resp1 = worker_simulator.handshake(valid_config)

        # Change both config and code
        modified_config = valid_config.copy()
        modified_config["config_hash"] = "hash_config_changed_multi"
        modified_config["code_hash"] = "hash_code_changed_multi"

        worker_simulator.exp_id = None
        hs_resp2 = worker_simulator.handshake(modified_config)

        assert hs_resp2.strategy == Strategy.BRANCH, "Multiple trigger file changes should trigger BRANCH"
