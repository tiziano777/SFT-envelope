"""Shared models for Worker state persistence and audit logging."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class WorkerState(BaseModel):
    """Persisted worker state after successful handshake."""

    exp_id: str = Field(..., description="Experiment ID from Master")
    recipe_id: str = Field(..., description="Recipe ID for this training")
    master_uri: str = Field(..., description="Master server URI")
    strategy: str = Field(..., description="Handshake strategy (NEW, RESUME, BRANCH, RETRY)")
    started_at: datetime = Field(default_factory=datetime.now)
    last_heartbeat: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "exp_id": "exp-123",
                "recipe_id": "recipe-abc",
                "master_uri": "http://localhost:8000",
                "strategy": "NEW",
                "started_at": "2026-04-13T10:00:00",
            }
        }


class TransferLogEntry(BaseModel):
    """Audit log entry for every push attempt."""

    event_id: str = Field(..., description="Unique event identifier")
    timestamp: datetime = Field(default_factory=datetime.now)
    event_type: str = Field(..., description="Event type: checkpoint, metric, config, etc.")
    uri: Optional[str] = Field(None, description="Remote storage URI if applicable")
    status: str = Field(..., description="Status: pending, sent, acked, failed")
    error: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(0, description="Number of retry attempts")

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "ckp-1234-567",
                "event_type": "checkpoint",
                "uri": "file:///checkpoint.json",
                "status": "sent",
                "retry_count": 0,
            }
        }
