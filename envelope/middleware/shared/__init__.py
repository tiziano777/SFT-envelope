"""Shared data contracts for the lineage tracking system."""

from __future__ import annotations

from envelope.middleware.shared.config_hasher import ConfigHasher, ConfigSnapshot
from envelope.middleware.shared.diff_engine import DiffEngine, DiffEntry
from envelope.middleware.shared.envelopes import (
    CheckpointPush,
    HandshakeRequest,
    HandshakeResponse,
    Strategy,
    SyncEvent,
)
from envelope.middleware.shared.nodes import (
    BaseNode,
    CheckpointNode,
    ComponentNode,
    ExperimentNode,
    ModelNode,
    RecipeNode,
)
from envelope.middleware.shared.relations import DerivedFromRel, RelationType

__all__ = [
    # nodes
    "BaseNode",
    "RecipeNode",
    "ModelNode",
    "ExperimentNode",
    "CheckpointNode",
    "ComponentNode",
    # relations
    "RelationType",
    "DerivedFromRel",
    # envelopes
    "Strategy",
    "HandshakeRequest",
    "HandshakeResponse",
    "CheckpointPush",
    "SyncEvent",
    # utilities
    "ConfigHasher",
    "ConfigSnapshot",
    "DiffEngine",
    "DiffEntry",
]
