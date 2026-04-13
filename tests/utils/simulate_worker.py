"""Worker simulator for E2E testing — sends requests to Master API."""

from __future__ import annotations

import json
from typing import Any

import httpx

from envelope.middleware.shared.envelopes import (
    CheckpointPush,
    HandshakeRequest,
    HandshakeResponse,
    StatusUpdate,
    Strategy,
)


class WorkerSimulator:
    """Simulates a Worker sending handshakes, checkpoints, and status updates to Master API."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = "test-api-key-12345"):
        """Initialize simulator with Master API endpoint and auth key.

        Args:
            base_url: Master API base URL
            api_key: X-API-Key header value
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.exp_id: str | None = None

    def handshake(self, config: dict[str, Any], strategy_override: str | None = None) -> HandshakeResponse:
        """Send handshake request to Master API.

        Args:
            config: Configuration dict with config_hash, req_hash, code_hash, etc.
            strategy_override: Force a specific strategy (for testing only)

        Returns:
            HandshakeResponse with exp_id and strategy

        Raises:
            httpx.HTTPError: If request fails
        """
        # Build HandshakeRequest from config
        hs_req = HandshakeRequest(
            config_hash=config.get("config_hash", "hash_test_config"),
            req_hash=config.get("req_hash", "hash_test_req"),
            code_hash=config.get("code_hash", "hash_test_code"),
            scaffold_path=config.get("scaffold_path", "/tmp/setup_test"),
            recipe_id=config.get("recipe_id", "recipe_test"),
            model_id=config.get("model_id", "model_test"),
            config_text=config.get("config_text", "test_config"),
            train_text=config.get("train_text", "test_train"),
            requirements_text=config.get("requirements_text", "torch==2.0"),
            rewards_texts=config.get("rewards_texts", []),
            rewards_filenames=config.get("rewards_filenames", []),
        )

        headers = {"X-API-Key": self.api_key}
        with httpx.Client() as client:
            resp = client.post(
                f"{self.base_url}/handshake",
                json=hs_req.model_dump(),
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            hs_resp = HandshakeResponse(**data)
            self.exp_id = hs_resp.exp_id
            return hs_resp

    def checkpoint_push(
        self,
        ckp_num: int,
        artifact_uri: str | None = None,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        """Push checkpoint to Master API.

        Args:
            ckp_num: Checkpoint number
            artifact_uri: Optional artifact URI (e.g., file://...)
            event_id: Optional event ID for idempotency

        Returns:
            Response JSON dict

        Raises:
            ValueError: If exp_id not set
            httpx.HTTPError: If request fails
        """
        if not self.exp_id:
            raise ValueError("exp_id not set. Call handshake() first.")

        ckp_push = CheckpointPush(
            exp_id=self.exp_id,
            ckp_id=event_id or f"ckp_{ckp_num}_{self.exp_id}",
            epoch=ckp_num,
            run=0,
            metrics_snapshot={"loss": 1.0 / (ckp_num + 1)},
            uri=artifact_uri,
            is_usable=True,
        )

        headers = {"X-API-Key": self.api_key}
        with httpx.Client() as client:
            resp = client.post(
                f"{self.base_url}/checkpoint_push",
                json=ckp_push.model_dump(),
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    def sync_event(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send sync event to Master API.

        Args:
            event_type: Type of event (e.g., "checkpoint_synced", "config_changed")
            payload: Optional event payload

        Returns:
            Response JSON dict

        Raises:
            ValueError: If exp_id not set
            httpx.HTTPError: If request fails
        """
        if not self.exp_id:
            raise ValueError("exp_id not set. Call handshake() first.")

        event_data = {
            "exp_id": self.exp_id,
            "event_type": event_type,
            "payload": payload or {},
        }

        headers = {"X-API-Key": self.api_key}
        with httpx.Client() as client:
            resp = client.post(
                f"{self.base_url}/sync_event",
                json=event_data,
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    def status_update(self, status: str, checkpoint_id: str | None = None) -> dict[str, Any]:
        """Send status update to Master API.

        Args:
            status: Status string (e.g., "TRAINING", "TRAINING_DONE")
            checkpoint_id: Optional checkpoint ID

        Returns:
            Response JSON dict

        Raises:
            ValueError: If exp_id not set
            httpx.HTTPError: If request fails
        """
        if not self.exp_id:
            raise ValueError("exp_id not set. Call handshake() first.")

        status_upd = StatusUpdate(
            exp_id=self.exp_id,
            status=status,
            checkpoint_id=checkpoint_id,
        )

        headers = {"X-API-Key": self.api_key}
        with httpx.Client() as client:
            resp = client.post(
                f"{self.base_url}/status_update",
                json=status_upd.model_dump(),
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()

    def training_done(self) -> dict[str, Any]:
        """Signal training completion to Master API.

        Returns:
            Response JSON dict

        Raises:
            ValueError: If exp_id not set
            httpx.HTTPError: If request fails
        """
        return self.status_update("TRAINING_DONE")
