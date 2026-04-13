"""Pydantic v2 models for Neo4j node types in the lineage graph."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --- Neo4j Node Types ---


class BaseNode(BaseModel):
    """Base for all Neo4j node types with shared fields."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="UUID primary key")
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RecipeNode(BaseNode):
    """Recipe node -- declarative experiment configuration entry point."""

    recipe_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = ""
    scope: str = ""
    tasks: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    issued: datetime
    modified: datetime
    derived_from: str | None = None
    config_yaml: str = ""


class ModelNode(BaseNode):
    """Model node -- base model for fine-tuning."""

    model_name: str = Field(..., min_length=1)
    version: str = ""
    uri: str = ""
    url: str = ""
    doc_url: str = ""
    architecture_info_ref: str = ""
    description: str = ""


class ExperimentNode(BaseNode):
    """Experiment node -- core tracking entity for a training run."""

    exp_id: str = Field(..., min_length=1)
    model_id: str = ""
    status: str = "RUNNING"
    exit_status: str | None = None
    exit_msg: str | None = None
    hash_committed_code: str = ""
    config: str = ""
    train: str = ""
    rewards: list[str] = Field(default_factory=list)
    rewards_filenames: list[str] = Field(default_factory=list)
    requirements: str = ""
    hyperparams_json: str = ""
    scaffold_local_uri: str = ""
    scaffold_remote_uri: str = ""
    usable: bool = True
    manual_save: bool = False
    metrics_uri: str = ""
    hw_metrics_uri: str = ""
    description: str = ""


class CheckpointNode(BaseNode):
    """Checkpoint node -- atomic weight snapshot from a training run."""

    ckp_id: str = Field(..., min_length=1)
    epoch: int = Field(..., ge=0)
    run: int = Field(..., ge=0)
    metrics_snapshot: dict[str, Any] = Field(default_factory=dict)
    uri: str | None = None
    is_usable: bool = True
    is_merging: bool = False
    description: str = ""


class ComponentNode(BaseNode):
    """Component node -- (technique, framework) pair from capability matrix.

    A Component represents a validated combination of technique + framework.
    If a (technique, framework) combo is not supported, the Component doesn't exist.
    This enforces compatibility at the data model level.

    Example: (lora_grpo, unsloth) exists, (qora, unsloth) doesn't exist → query returns None
    """

    opt_code: str = Field(..., min_length=1, description="Optimization code/identifier")
    technique_code: str = Field(..., min_length=1, description="Technique code (e.g., lora_grpo)")
    framework_code: str = Field(..., min_length=1, description="Framework code (e.g., unsloth)")
    docs_url: str = ""
    description: str = ""
