"""Strategy enum and transport envelopes for Worker-Master communication."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# --- Strategy ---


class Strategy(str, Enum):
    """Handshake strategy -- determines how the Master processes an experiment."""

    NEW = "NEW"
    RESUME = "RESUME"
    BRANCH = "BRANCH"
    RETRY = "RETRY"


# --- Transport Envelopes ---


class HandshakeRequest(BaseModel):
    """Worker to Master handshake request."""

    config_hash: str
    req_hash: str
    code_hash: str
    checkpoint_id_to_resume: str | None = None
    scaffold_path: str
    base_exp_id: str | None = None
    recipe_id: str
    model_id: str
    config_text: str
    train_text: str
    requirements_text: str
    rewards_texts: list[str] = Field(default_factory=list)
    rewards_filenames: list[str] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)


class HandshakeResponse(BaseModel):
    """Master to Worker handshake response."""

    exp_id: str
    strategy: Strategy
    base_checkpoint_uri: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)


class CheckpointPush(BaseModel):
    """Worker to Master checkpoint data push."""

    exp_id: str
    ckp_id: str
    epoch: int
    run: int
    metrics_snapshot: dict[str, Any] = Field(default_factory=dict)
    uri: str | None = None
    is_usable: bool = True
    transfer_policy: str = "ALL"
    headers: dict[str, str] = Field(default_factory=dict)


class SyncEvent(BaseModel):
    """Worker to Master async event."""

    event_id: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp_worker: datetime
    exp_id: str
    headers: dict[str, str] = Field(default_factory=dict)
