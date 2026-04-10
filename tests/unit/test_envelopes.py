"""Unit tests for envelope/middleware/shared/envelopes.py."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from envelope.middleware.shared.envelopes import (
    CheckpointPush,
    HandshakeRequest,
    HandshakeResponse,
    Strategy,
    SyncEvent,
)


# ---------------------------------------------------------------------------
# Strategy Enum
# ---------------------------------------------------------------------------


class TestStrategy:
    """Validate Strategy enum members."""

    def test_member_count(self) -> None:
        assert len(Strategy) == 4

    @pytest.mark.parametrize(
        "member,value",
        [
            (Strategy.NEW, "NEW"),
            (Strategy.RESUME, "RESUME"),
            (Strategy.BRANCH, "BRANCH"),
            (Strategy.RETRY, "RETRY"),
        ],
    )
    def test_member_values(self, member: Strategy, value: str) -> None:
        assert member.value == value

    def test_all_values_upper_case(self) -> None:
        for member in Strategy:
            assert member.value == member.value.upper()


# ---------------------------------------------------------------------------
# HandshakeRequest
# ---------------------------------------------------------------------------


class TestHandshakeRequest:
    """Validate HandshakeRequest fields and defaults."""

    def test_instantiation(self) -> None:
        req = HandshakeRequest(
            config_hash="h1",
            req_hash="h2",
            code_hash="h3",
            scaffold_path="/tmp",
            recipe_id="r1",
            model_id="m1",
            config_text="lr: 1e-4",
            train_text="import torch",
            requirements_text="torch>=2.0",
        )
        assert req.config_hash == "h1"
        assert req.headers == {}
        assert req.checkpoint_id_to_resume is None
        assert req.base_exp_id is None
        assert req.rewards_texts == []
        assert req.rewards_filenames == []

    def test_headers_default_empty_dict(self) -> None:
        req = HandshakeRequest(
            config_hash="h1",
            req_hash="h2",
            code_hash="h3",
            scaffold_path="/tmp",
            recipe_id="r1",
            model_id="m1",
            config_text="",
            train_text="",
            requirements_text="",
        )
        assert req.headers == {}
        assert isinstance(req.headers, dict)

    def test_roundtrip_serialization(self) -> None:
        req = HandshakeRequest(
            config_hash="abc123",
            req_hash="def456",
            code_hash="ghi789",
            scaffold_path="/tmp/setup_test",
            recipe_id="r-001",
            model_id="m-001",
            config_text="lr: 1e-4",
            train_text="import torch",
            requirements_text="torch>=2.0",
            rewards_texts=["def reward(): return 1.0"],
            rewards_filenames=["math_reward.py"],
            headers={"X-Version": "1.0"},
        )
        json_str = req.model_dump_json()
        restored = HandshakeRequest.model_validate_json(json_str)
        assert req == restored


# ---------------------------------------------------------------------------
# HandshakeResponse
# ---------------------------------------------------------------------------


class TestHandshakeResponse:
    """Validate HandshakeResponse fields."""

    def test_instantiation(self) -> None:
        resp = HandshakeResponse(exp_id="e1", strategy=Strategy.NEW)
        assert resp.exp_id == "e1"
        assert resp.strategy == Strategy.NEW
        assert resp.base_checkpoint_uri is None
        assert resp.headers == {}

    def test_strategy_accepts_enum(self) -> None:
        resp = HandshakeResponse(exp_id="e1", strategy=Strategy.BRANCH)
        assert resp.strategy == Strategy.BRANCH

    def test_strategy_accepts_string(self) -> None:
        resp = HandshakeResponse(exp_id="e1", strategy="RESUME")
        assert resp.strategy == Strategy.RESUME

    def test_roundtrip_serialization(self) -> None:
        resp = HandshakeResponse(
            exp_id="e1",
            strategy=Strategy.BRANCH,
            base_checkpoint_uri="worker:///ckp/001",
            headers={"X-Trace": "abc"},
        )
        json_str = resp.model_dump_json()
        restored = HandshakeResponse.model_validate_json(json_str)
        assert resp == restored


# ---------------------------------------------------------------------------
# CheckpointPush
# ---------------------------------------------------------------------------


class TestCheckpointPush:
    """Validate CheckpointPush fields and defaults."""

    def test_instantiation(self) -> None:
        ckp = CheckpointPush(exp_id="e1", ckp_id="c1", epoch=0, run=0)
        assert ckp.metrics_snapshot == {}
        assert ckp.uri is None
        assert ckp.is_usable is True
        assert ckp.transfer_policy == "ALL"
        assert ckp.headers == {}

    def test_roundtrip_serialization(self) -> None:
        ckp = CheckpointPush(
            exp_id="e1",
            ckp_id="c1",
            epoch=3,
            run=1,
            metrics_snapshot={"loss": 0.5, "accuracy": 0.9},
            uri="s3://bucket/ckp",
            is_usable=True,
            transfer_policy="BEST_ONLY",
            headers={"X-Policy": "best"},
        )
        json_str = ckp.model_dump_json()
        restored = CheckpointPush.model_validate_json(json_str)
        assert ckp == restored


# ---------------------------------------------------------------------------
# SyncEvent
# ---------------------------------------------------------------------------


class TestSyncEvent:
    """Validate SyncEvent fields."""

    def test_instantiation(self) -> None:
        now = datetime.now(tz=timezone.utc)
        event = SyncEvent(
            event_id="ev1",
            event_type="STATUS",
            payload={},
            timestamp_worker=now,
            exp_id="e1",
        )
        assert event.event_id == "ev1"
        assert event.event_type == "STATUS"
        assert event.headers == {}

    def test_roundtrip_serialization(self) -> None:
        now = datetime.now(tz=timezone.utc)
        event = SyncEvent(
            event_id="ev1",
            event_type="METRIC",
            payload={"loss": 0.3},
            timestamp_worker=now,
            exp_id="e1",
            headers={"X-Retry": "0"},
        )
        json_str = event.model_dump_json()
        restored = SyncEvent.model_validate_json(json_str)
        assert event == restored


# ---------------------------------------------------------------------------
# Envelope Headers (all 4 envelopes)
# ---------------------------------------------------------------------------


class TestEnvelopeHeaders:
    """Verify all 4 envelopes have headers defaulting to empty dict (D-04)."""

    @pytest.mark.parametrize(
        "envelope",
        [
            pytest.param(
                HandshakeRequest(
                    config_hash="h",
                    req_hash="h",
                    code_hash="h",
                    scaffold_path="/tmp",
                    recipe_id="r1",
                    model_id="m1",
                    config_text="",
                    train_text="",
                    requirements_text="",
                ),
                id="HandshakeRequest",
            ),
            pytest.param(
                HandshakeResponse(exp_id="e1", strategy=Strategy.NEW),
                id="HandshakeResponse",
            ),
            pytest.param(
                CheckpointPush(exp_id="e1", ckp_id="c1", epoch=0, run=0),
                id="CheckpointPush",
            ),
            pytest.param(
                SyncEvent(
                    event_id="ev1",
                    event_type="STATUS",
                    payload={},
                    timestamp_worker=datetime.now(tz=timezone.utc),
                    exp_id="e1",
                ),
                id="SyncEvent",
            ),
        ],
    )
    def test_headers_default_empty(self, envelope: object) -> None:
        assert envelope.headers == {}  # type: ignore[attr-defined]

    @pytest.mark.parametrize(
        "envelope_cls,kwargs",
        [
            pytest.param(
                HandshakeRequest,
                {
                    "config_hash": "h",
                    "req_hash": "h",
                    "code_hash": "h",
                    "scaffold_path": "/tmp",
                    "recipe_id": "r1",
                    "model_id": "m1",
                    "config_text": "",
                    "train_text": "",
                    "requirements_text": "",
                },
                id="HandshakeRequest",
            ),
            pytest.param(
                HandshakeResponse,
                {"exp_id": "e1", "strategy": Strategy.NEW},
                id="HandshakeResponse",
            ),
            pytest.param(
                CheckpointPush,
                {"exp_id": "e1", "ckp_id": "c1", "epoch": 0, "run": 0},
                id="CheckpointPush",
            ),
            pytest.param(
                SyncEvent,
                {
                    "event_id": "ev1",
                    "event_type": "STATUS",
                    "payload": {},
                    "timestamp_worker": datetime.now(tz=timezone.utc),
                    "exp_id": "e1",
                },
                id="SyncEvent",
            ),
        ],
    )
    def test_headers_can_be_set(self, envelope_cls: type, kwargs: dict) -> None:
        kwargs["headers"] = {"X-Custom": "value"}
        envelope = envelope_cls(**kwargs)
        assert envelope.headers == {"X-Custom": "value"}

    @pytest.mark.parametrize(
        "envelope",
        [
            pytest.param(
                HandshakeRequest(
                    config_hash="h",
                    req_hash="h",
                    code_hash="h",
                    scaffold_path="/tmp",
                    recipe_id="r1",
                    model_id="m1",
                    config_text="",
                    train_text="",
                    requirements_text="",
                ),
                id="HandshakeRequest",
            ),
            pytest.param(
                HandshakeResponse(exp_id="e1", strategy=Strategy.NEW),
                id="HandshakeResponse",
            ),
            pytest.param(
                CheckpointPush(exp_id="e1", ckp_id="c1", epoch=0, run=0),
                id="CheckpointPush",
            ),
            pytest.param(
                SyncEvent(
                    event_id="ev1",
                    event_type="STATUS",
                    payload={},
                    timestamp_worker=datetime.now(tz=timezone.utc),
                    exp_id="e1",
                ),
                id="SyncEvent",
            ),
        ],
    )
    def test_headers_type_is_dict(self, envelope: object) -> None:
        assert isinstance(envelope.headers, dict)  # type: ignore[attr-defined]
