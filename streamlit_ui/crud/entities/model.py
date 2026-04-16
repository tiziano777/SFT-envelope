"""Pydantic models for Model entity."""

from __future__ import annotations

from pydantic import Field
from .base import BaseEntity

class Model(BaseEntity):
    """Model entity -- base model for fine-tuning."""

    model_name: str = Field(..., min_length=1, description="Unique model name")
    version: str = Field("", description="Model version")
    uri: str = Field("", description="Path or URI to model")
    url: str = Field("", description="Model URL (HuggingFace, etc)")
    doc_url: str = Field("", description="Documentation URL")
    description: str = Field("", description="Model description")
    kind: str = Field("", description="Model kind: BASE | ADAPTER | MERGED")
    architecture_info_ref: str = Field("", description="Reference to architecture document")
  
