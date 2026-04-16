"""Pydantic models for Experiment entity."""

from __future__ import annotations

from pydantic import  Field
from .base import BaseEntity

class Experiment(BaseEntity):
    """Experiment entity -- core tracking entity for a training run."""

    exp_id: str = Field(..., min_length=1, description="Unique experiment ID")
    model_id: str = Field("", description="Associated Model ID")
    description: str = Field("", description="Experiment description")

    status: str = Field("RUNNING", description="RUNNING | COMPLETED | FAILED | PAUSED")
    exit_status: str | None = None
    exit_msg: str | None = None
    strategy: str = Field("", description="NEW | RESUME | BRANCH | RETRY")
    
    config_hash: str = Field("", description="SHA256 of config.yaml")
    code_hash: str = Field("", description="SHA256 of train.py + rewards/*")
    req_hash: str = Field("", description="SHA256 of requirements.txt")
    
    config: str = Field("", description="Textual content of config.yaml (snapshot)")
    train: str = Field("", description="Textual content of train.py (snapshot)")
    rewards: list[str] = Field(default_factory=list, description="List of reward file contents")
    rewards_filenames: list[str] = Field(default_factory=list, description="Reward filenames")
    requirements: str = Field("", description="Textual content of requirements.txt")
    
    scaffold_local_uri: str = Field("", description="Path scaffold on worker")
    scaffold_remote_uri: str = Field("", description="Path scaffold on master/storage")
    
    usable: bool = Field(True, description="Is experiment usable")
    manual_save: bool = Field(False, description="Manually saved")
    
    metrics_uri: str = Field("", description="Pointer to training metrics")
    hw_metrics_uri: str = Field("", description="Pointer to hardware metrics")
    