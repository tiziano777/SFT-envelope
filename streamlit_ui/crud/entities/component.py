"""Pydantic models for Component entity."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Component(BaseModel):
    """Component entity -- (technique, framework) pair from capability matrix.

    A Component represents a validated combination of technique + framework.
    If a (technique, framework) combo is not supported, the Component doesn't exist.
    This enforces compatibility at the data model level.

    Example: (grpo, unsloth) exists, (unknown, unsloth) doesn't exist → query returns None
    """

    id: str = Field(..., min_length=1, description="UUID primary key")
    description: str = Field("", description="Component description")
    
    technique_code: str = Field(..., min_length=1, description="Technique code (e.g., grpo, sft)")
    framework_code: str = Field(..., min_length=1, description="Framework code (e.g., unsloth, trl)")
    opt_code: str = Field("", description="Optimization code")
    
    docs_url: str = Field("", description="Documentation URL")
    
    created_at: str | None = None
    updated_at: str | None = None
