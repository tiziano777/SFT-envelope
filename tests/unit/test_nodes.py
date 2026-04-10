"""Unit tests for envelope/middleware/shared/nodes.py -- Neo4j node types."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from envelope.middleware.shared.nodes import (
    BaseNode,
    CheckpointNode,
    ComponentNode,
    ExperimentNode,
    ModelNode,
    RecipeNode,
)


# ---------------------------------------------------------------------------
# BaseNode
# ---------------------------------------------------------------------------


class TestBaseNode:
    """Validate BaseNode instantiation and field constraints."""

    def test_instantiation(self) -> None:
        node = BaseNode(id="abc")
        assert node.id == "abc"
        assert node.created_at is None
        assert node.updated_at is None

    def test_with_timestamps(self) -> None:
        now = datetime.now(tz=timezone.utc)
        node = BaseNode(id="abc", created_at=now, updated_at=now)
        assert node.created_at == now
        assert node.updated_at == now

    def test_id_min_length_validation(self) -> None:
        with pytest.raises(ValidationError):
            BaseNode(id="")


# ---------------------------------------------------------------------------
# RecipeNode
# ---------------------------------------------------------------------------


class TestRecipeNode:
    """Validate RecipeNode fields and BaseNode inheritance."""

    def test_instantiation(self) -> None:
        now = datetime.now(tz=timezone.utc)
        node = RecipeNode(
            id="r1",
            recipe_id="r1",
            name="test",
            description="",
            scope="",
            tasks=[],
            tags=[],
            issued=now,
            modified=now,
        )
        assert node.recipe_id == "r1"
        assert node.name == "test"
        assert node.derived_from is None
        assert node.config_yaml == ""

    def test_inherits_from_base_node(self) -> None:
        now = datetime.now(tz=timezone.utc)
        node = RecipeNode(
            id="r1",
            recipe_id="r1",
            name="test",
            description="",
            scope="",
            tasks=[],
            tags=[],
            issued=now,
            modified=now,
        )
        assert isinstance(node, BaseNode)
        assert node.created_at is None
        assert node.updated_at is None

    def test_roundtrip_serialization(self) -> None:
        now = datetime.now(tz=timezone.utc)
        node = RecipeNode(
            id="r1",
            recipe_id="r1",
            name="test",
            description="desc",
            scope="scope",
            tasks=["t1"],
            tags=["tag1"],
            issued=now,
            modified=now,
            derived_from="parent-r",
            config_yaml="lr: 1e-4",
        )
        json_str = node.model_dump_json()
        restored = RecipeNode.model_validate_json(json_str)
        assert node == restored


# ---------------------------------------------------------------------------
# ModelNode
# ---------------------------------------------------------------------------


class TestModelNode:
    """Validate ModelNode fields."""

    def test_instantiation(self) -> None:
        node = ModelNode(
            id="m1",
            model_name="llama-3",
            version="1.0",
            uri="",
            url="",
            doc_url="",
            architecture_info_ref="",
            description="",
        )
        assert node.model_name == "llama-3"
        assert isinstance(node, BaseNode)

    def test_model_name_required(self) -> None:
        with pytest.raises(ValidationError):
            ModelNode(id="m1", model_name="")


# ---------------------------------------------------------------------------
# ExperimentNode
# ---------------------------------------------------------------------------


class TestExperimentNode:
    """Validate ExperimentNode defaults and required fields."""

    def test_instantiation_minimal(self) -> None:
        node = ExperimentNode(
            id="e1",
            exp_id="e1",
            hash_committed_code="abc123",
        )
        assert node.status == "RUNNING"
        assert node.usable is True
        assert node.manual_save is False
        assert node.rewards == []
        assert node.rewards_filenames == []
        assert node.model_id == ""
        assert node.config == ""
        assert node.train == ""
        assert node.requirements == ""
        assert node.hyperparams_json == ""
        assert node.scaffold_local_uri == ""
        assert node.scaffold_remote_uri == ""
        assert node.metrics_uri == ""
        assert node.hw_metrics_uri == ""
        assert node.description == ""
        assert node.exit_status is None
        assert node.exit_msg is None
        assert isinstance(node, BaseNode)

    def test_exp_id_required(self) -> None:
        with pytest.raises(ValidationError):
            ExperimentNode(id="e1", exp_id="", hash_committed_code="abc")


# ---------------------------------------------------------------------------
# CheckpointNode
# ---------------------------------------------------------------------------


class TestCheckpointNode:
    """Validate CheckpointNode constraints and defaults."""

    def test_instantiation(self) -> None:
        node = CheckpointNode(id="c1", ckp_id="c1", epoch=0, run=0)
        assert node.metrics_snapshot == {}
        assert node.uri is None
        assert node.is_usable is True
        assert node.is_merging is False
        assert node.description == ""
        assert isinstance(node, BaseNode)

    def test_epoch_ge_zero(self) -> None:
        with pytest.raises(ValidationError):
            CheckpointNode(id="c1", ckp_id="c1", epoch=-1, run=0)

    def test_run_ge_zero(self) -> None:
        with pytest.raises(ValidationError):
            CheckpointNode(id="c1", ckp_id="c1", epoch=0, run=-1)


# ---------------------------------------------------------------------------
# ComponentNode
# ---------------------------------------------------------------------------


class TestComponentNode:
    """Validate ComponentNode fields."""

    def test_instantiation(self) -> None:
        node = ComponentNode(
            id="comp1",
            technique_code="grpo",
            framework_code="trl",
        )
        assert node.technique_code == "grpo"
        assert node.framework_code == "trl"
        assert node.docs_url == ""
        assert node.description == ""
        assert isinstance(node, BaseNode)

    def test_technique_code_min_length(self) -> None:
        with pytest.raises(ValidationError):
            ComponentNode(id="comp1", technique_code="", framework_code="trl")

    def test_framework_code_min_length(self) -> None:
        with pytest.raises(ValidationError):
            ComponentNode(id="comp1", technique_code="grpo", framework_code="")


# ---------------------------------------------------------------------------
# Serialization Roundtrip (all node types)
# ---------------------------------------------------------------------------


class TestNodeSerialization:
    """Verify model_dump_json / model_validate_json roundtrip for all node types."""

    @pytest.mark.parametrize(
        "node",
        [
            pytest.param(
                RecipeNode(
                    id="r1",
                    recipe_id="r1",
                    name="test",
                    description="",
                    scope="",
                    tasks=[],
                    tags=[],
                    issued=datetime(2025, 1, 1, tzinfo=timezone.utc),
                    modified=datetime(2025, 1, 1, tzinfo=timezone.utc),
                ),
                id="RecipeNode",
            ),
            pytest.param(
                ModelNode(
                    id="m1",
                    model_name="llama-3",
                    version="1.0",
                    uri="",
                    url="",
                    doc_url="",
                    architecture_info_ref="",
                    description="",
                ),
                id="ModelNode",
            ),
            pytest.param(
                ExperimentNode(
                    id="e1",
                    exp_id="e1",
                    hash_committed_code="abc123",
                ),
                id="ExperimentNode",
            ),
            pytest.param(
                CheckpointNode(id="c1", ckp_id="c1", epoch=0, run=0),
                id="CheckpointNode",
            ),
            pytest.param(
                ComponentNode(
                    id="comp1", technique_code="grpo", framework_code="trl"
                ),
                id="ComponentNode",
            ),
        ],
    )
    def test_roundtrip(self, node: BaseNode) -> None:
        json_str = node.model_dump_json()
        cls = type(node)
        restored = cls.model_validate_json(json_str)
        assert node == restored

    @pytest.mark.parametrize(
        "node",
        [
            pytest.param(
                RecipeNode(
                    id="r1",
                    recipe_id="r1",
                    name="test",
                    description="",
                    scope="",
                    tasks=[],
                    tags=[],
                    issued=datetime(2025, 1, 1, tzinfo=timezone.utc),
                    modified=datetime(2025, 1, 1, tzinfo=timezone.utc),
                ),
                id="RecipeNode",
            ),
            pytest.param(
                ModelNode(
                    id="m1",
                    model_name="llama-3",
                ),
                id="ModelNode",
            ),
            pytest.param(
                ExperimentNode(id="e1", exp_id="e1", hash_committed_code="x"),
                id="ExperimentNode",
            ),
            pytest.param(
                CheckpointNode(id="c1", ckp_id="c1", epoch=0, run=0),
                id="CheckpointNode",
            ),
            pytest.param(
                ComponentNode(
                    id="comp1", technique_code="grpo", framework_code="trl"
                ),
                id="ComponentNode",
            ),
        ],
    )
    def test_isinstance_base_node(self, node: BaseNode) -> None:
        assert isinstance(node, BaseNode)
