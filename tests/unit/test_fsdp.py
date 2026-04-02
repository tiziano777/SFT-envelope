"""Unit tests for FSDP integration across config, validators, adapters, and capability matrix."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from envelope.config.models import (
    FSDPAutoWrapPolicy,
    FSDPBackwardPrefetch,
    FSDPConfig,
    FSDPMixedPrecision,
    FSDPShardingStrategy,
    EnvelopeConfig,
    OptimizationConfig,
)
from envelope.config.validators import validate_config
from envelope.frameworks.accelerate_fsdp import build_accelerate_fsdp_config
from envelope.frameworks.base import BaseFrameworkAdapter
from envelope.frameworks.capability_matrix import get_fsdp_frameworks, get_infra_support
from envelope.registry import discover_plugins, framework_registry

# Ensure all plugins are registered
discover_plugins()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**overrides) -> EnvelopeConfig:
    """Build a minimal valid EnvelopeConfig with optional overrides."""
    base = {
        "experiment": {"name": "fsdp-test"},
        "model": {"name_or_path": "meta-llama/Llama-3.1-8B"},
        "dataset": {"train_uri": "tatsu-lab/alpaca"},
    }
    base.update(overrides)
    return EnvelopeConfig.model_validate(base)


def _get_adapter(name: str) -> BaseFrameworkAdapter:
    cls = framework_registry.get(name)
    return cls()


# ===========================================================================
# FSDPConfig model tests
# ===========================================================================


class TestFSDPConfig:
    """Tests for the FSDPConfig Pydantic model."""

    def test_defaults(self):
        cfg = FSDPConfig()
        assert cfg.enabled is False
        assert cfg.sharding_strategy == FSDPShardingStrategy.FULL_SHARD
        assert cfg.auto_wrap_policy == FSDPAutoWrapPolicy.TRANSFORMER_BASED
        assert cfg.min_num_params == 1_000_000
        assert cfg.cpu_offload is False
        assert cfg.mixed_precision == FSDPMixedPrecision.NONE
        assert cfg.forward_prefetch is True
        assert cfg.backward_prefetch == FSDPBackwardPrefetch.BACKWARD_PRE
        assert cfg.sync_module_states is True
        assert cfg.use_orig_params is True
        assert cfg.limit_all_gathers is True
        assert cfg.activation_checkpointing is False

    def test_fsdp_in_optimization_defaults(self):
        cfg = OptimizationConfig()
        assert isinstance(cfg.fsdp, FSDPConfig)
        assert cfg.fsdp.enabled is False

    def test_fsdp_enabled_via_dict(self):
        cfg = OptimizationConfig.model_validate({"fsdp": {"enabled": True, "sharding_strategy": "shard_grad_op"}})
        assert cfg.fsdp.enabled is True
        assert cfg.fsdp.sharding_strategy == FSDPShardingStrategy.SHARD_GRAD_OP

    def test_fsdp_min_num_params_positive(self):
        with pytest.raises(ValidationError):
            FSDPConfig(min_num_params=0)

    def test_fsdp_backward_compat_bool_true(self):
        """fsdp: true in YAML should be coerced to FSDPConfig(enabled=True)."""
        cfg = OptimizationConfig.model_validate({"fsdp": True})
        assert cfg.fsdp.enabled is True

    def test_fsdp_backward_compat_bool_false(self):
        """fsdp: false in YAML should be coerced to FSDPConfig(enabled=False)."""
        cfg = OptimizationConfig.model_validate({"fsdp": False})
        assert cfg.fsdp.enabled is False

    @pytest.mark.parametrize("strategy", ["full_shard", "shard_grad_op", "no_shard", "hybrid_shard"])
    def test_all_sharding_strategies(self, strategy: str):
        cfg = FSDPConfig(sharding_strategy=strategy)
        assert cfg.sharding_strategy.value == strategy

    @pytest.mark.parametrize("policy", ["transformer_based", "size_based"])
    def test_all_auto_wrap_policies(self, policy: str):
        cfg = FSDPConfig(auto_wrap_policy=policy)
        assert cfg.auto_wrap_policy.value == policy

    def test_invalid_sharding_strategy_rejected(self):
        with pytest.raises(ValidationError):
            FSDPConfig(sharding_strategy="invalid")


class TestFSDPAutoSetMixedPrecision:
    """Tests for automatic FSDP mixed precision from compute_dtype."""

    def test_auto_set_bf16(self):
        cfg = _make_config(
            optimization={"fsdp": {"enabled": True}},
            hardware={"gpu_count": 4},
            training={"technique": "sft", "precision": {"compute_dtype": "bf16"}},
            framework={"backend": "trl"},
        )
        assert cfg.optimization.fsdp.mixed_precision == FSDPMixedPrecision.BF16

    def test_auto_set_fp16(self):
        cfg = _make_config(
            optimization={"fsdp": {"enabled": True}},
            hardware={"gpu_count": 4},
            training={"technique": "sft", "precision": {"compute_dtype": "fp16"}},
            framework={"backend": "trl"},
        )
        assert cfg.optimization.fsdp.mixed_precision == FSDPMixedPrecision.FP16

    def test_no_auto_set_when_explicitly_specified(self):
        cfg = _make_config(
            optimization={"fsdp": {"enabled": True, "mixed_precision": "fp16"}},
            hardware={"gpu_count": 4},
            training={"technique": "sft", "precision": {"compute_dtype": "bf16"}},
            framework={"backend": "trl"},
        )
        assert cfg.optimization.fsdp.mixed_precision == FSDPMixedPrecision.FP16

    def test_no_auto_set_when_disabled(self):
        cfg = _make_config(
            optimization={"fsdp": {"enabled": False}},
            training={"technique": "sft", "precision": {"compute_dtype": "bf16"}},
        )
        assert cfg.optimization.fsdp.mixed_precision == FSDPMixedPrecision.NONE


# ===========================================================================
# FSDP Validator tests
# ===========================================================================


class TestFSDPValidation:
    """Tests for FSDP cross-field validators."""

    def test_fsdp_disabled_no_errors(self):
        config = _make_config(
            optimization={"fsdp": {"enabled": False}},
            training={"technique": "sft"},
            framework={"backend": "trl"},
        )
        errors = validate_config(config)
        fsdp_errors = [e for e in errors if "fsdp" in e.lower()]
        assert len(fsdp_errors) == 0

    def test_fsdp_single_gpu_errors(self):
        config = _make_config(
            optimization={"fsdp": {"enabled": True}},
            hardware={"gpu_count": 1},
            training={"technique": "sft"},
            framework={"backend": "trl"},
        )
        errors = validate_config(config)
        assert any("gpu_count" in e.lower() or "gpu" in e.lower() for e in errors)

    def test_fsdp_multi_gpu_no_gpu_error(self):
        config = _make_config(
            optimization={"fsdp": {"enabled": True}},
            hardware={"gpu_count": 4},
            training={"technique": "sft"},
            framework={"backend": "trl"},
        )
        errors = validate_config(config)
        fsdp_gpu_errors = [e for e in errors if "fsdp" in e.lower() and "gpu_count" in e.lower()]
        assert len(fsdp_gpu_errors) == 0

    def test_fsdp_unsloth_incompatible(self):
        config = _make_config(
            optimization={"fsdp": {"enabled": True}},
            hardware={"gpu_count": 4},
            training={"technique": "sft"},
            framework={"backend": "unsloth"},
        )
        errors = validate_config(config)
        assert any("unsloth" in e.lower() for e in errors)

    def test_fsdp_deepspeed_mutual_exclusion(self):
        config = _make_config(
            optimization={"fsdp": {"enabled": True}, "deepspeed_stage": 2},
            hardware={"gpu_count": 4},
            training={"technique": "sft"},
            framework={"backend": "trl"},
        )
        errors = validate_config(config)
        assert any("deepspeed" in e.lower() and "fsdp" in e.lower() for e in errors)

    def test_fsdp_qlora_needs_use_orig_params(self):
        config = _make_config(
            optimization={"fsdp": {"enabled": True, "use_orig_params": False}},
            hardware={"gpu_count": 4},
            training={"technique": "sft", "peft": {"method": "qlora"}, "precision": {"quantization": "nf4"}},
            framework={"backend": "trl"},
        )
        errors = validate_config(config)
        assert any("use_orig_params" in e.lower() for e in errors)

    def test_fsdp_torchtune_internal_errors(self):
        config = _make_config(
            optimization={"fsdp": {"enabled": True}},
            hardware={"gpu_count": 4},
            training={"technique": "sft"},
            framework={"backend": "torchtune"},
        )
        errors = validate_config(config)
        assert any("internally" in e.lower() for e in errors)

    def test_fsdp_verl_internal_errors(self):
        config = _make_config(
            optimization={"fsdp": {"enabled": True}},
            hardware={"gpu_count": 4},
            training={"technique": "grpo"},
            framework={"backend": "verl"},
            reward={"type": "verifiable", "functions": [{"name": "test", "module_path": "test"}]},
        )
        errors = validate_config(config)
        assert any("internally" in e.lower() for e in errors)

    def test_fsdp_cpu_offload_fp16_warns(self):
        config = _make_config(
            optimization={"fsdp": {"enabled": True, "cpu_offload": True, "mixed_precision": "fp16"}},
            hardware={"gpu_count": 4},
            training={"technique": "sft"},
            framework={"backend": "trl"},
        )
        errors = validate_config(config)
        assert any("cpu offload" in e.lower() for e in errors)

    def test_fsdp_cpu_offload_bf16_ok(self):
        config = _make_config(
            optimization={"fsdp": {"enabled": True, "cpu_offload": True, "mixed_precision": "bf16"}},
            hardware={"gpu_count": 4},
            training={"technique": "sft"},
            framework={"backend": "trl"},
        )
        errors = validate_config(config)
        assert not any("cpu offload" in e.lower() for e in errors)


# ===========================================================================
# Accelerate Config Builder tests
# ===========================================================================


class TestBuildAccelerateFSDPConfig:
    """Tests for the shared Accelerate FSDP config builder."""

    def test_basic_structure(self):
        config = _make_config(
            hardware={"gpu_count": 4},
            optimization={"fsdp": {"enabled": True}},
            training={"technique": "sft"},
            framework={"backend": "trl"},
        )
        result = build_accelerate_fsdp_config(config)
        assert result["compute_environment"] == "LOCAL_MACHINE"
        assert result["distributed_type"] == "FSDP"
        assert "fsdp_config" in result
        assert result["num_processes"] == 4

    def test_sharding_strategy_mapping(self):
        for strategy, expected in [
            ("full_shard", "FULL_SHARD"),
            ("shard_grad_op", "SHARD_GRAD_OP"),
            ("no_shard", "NO_SHARD"),
            ("hybrid_shard", "HYBRID_SHARD"),
        ]:
            config = _make_config(
                hardware={"gpu_count": 4},
                optimization={"fsdp": {"enabled": True, "sharding_strategy": strategy}},
                training={"technique": "sft"},
                framework={"backend": "trl"},
            )
            result = build_accelerate_fsdp_config(config)
            assert result["fsdp_config"]["fsdp_sharding_strategy"] == expected

    def test_multinode_num_processes(self):
        config = _make_config(
            hardware={"gpu_count": 4, "num_nodes": 2},
            optimization={"fsdp": {"enabled": True}},
            training={"technique": "sft"},
            framework={"backend": "trl"},
        )
        result = build_accelerate_fsdp_config(config)
        assert result["num_processes"] == 8
        assert result["num_machines"] == 2

    def test_cpu_offload(self):
        config = _make_config(
            hardware={"gpu_count": 4},
            optimization={"fsdp": {"enabled": True, "cpu_offload": True}},
            training={"technique": "sft"},
            framework={"backend": "trl"},
        )
        result = build_accelerate_fsdp_config(config)
        assert result["fsdp_config"]["fsdp_offload_params"] is True

    def test_mixed_precision_bf16(self):
        config = _make_config(
            hardware={"gpu_count": 4},
            optimization={"fsdp": {"enabled": True, "mixed_precision": "bf16"}},
            training={"technique": "sft"},
            framework={"backend": "trl"},
        )
        result = build_accelerate_fsdp_config(config)
        assert result["mixed_precision"] == "bf16"

    def test_mixed_precision_none_becomes_no(self):
        config = _make_config(
            hardware={"gpu_count": 4},
            optimization={"fsdp": {"enabled": True, "mixed_precision": "none"}},
            training={"technique": "sft", "precision": {"compute_dtype": "fp32"}},
            framework={"backend": "trl"},
        )
        result = build_accelerate_fsdp_config(config)
        assert result["mixed_precision"] == "no"

    def test_backward_prefetch_mapping(self):
        for prefetch, expected in [
            ("backward_pre", "BACKWARD_PRE"),
            ("backward_post", "BACKWARD_POST"),
        ]:
            config = _make_config(
                hardware={"gpu_count": 4},
                optimization={"fsdp": {"enabled": True, "backward_prefetch": prefetch}},
                training={"technique": "sft"},
                framework={"backend": "trl"},
            )
            result = build_accelerate_fsdp_config(config)
            assert result["fsdp_config"]["fsdp_backward_prefetch"] == expected

    def test_state_dict_type_sharded(self):
        config = _make_config(
            hardware={"gpu_count": 4},
            optimization={"fsdp": {"enabled": True}},
            training={"technique": "sft"},
            framework={"backend": "trl"},
        )
        result = build_accelerate_fsdp_config(config)
        assert result["fsdp_config"]["fsdp_state_dict_type"] == "SHARDED_STATE_DICT"


# ===========================================================================
# FSDP Launch Command tests
# ===========================================================================


class TestFSDPLaunchCommands:
    """Tests for FSDP-aware launch commands in framework adapters."""

    def test_trl_fsdp_launch(self):
        adapter = _get_adapter("trl")
        config = _make_config(
            hardware={"gpu_count": 4},
            optimization={"fsdp": {"enabled": True}},
            training={"technique": "sft"},
            framework={"backend": "trl"},
        )
        cmd = adapter.launch_command(config)
        assert "accelerate launch" in cmd
        assert "accelerate_config.yaml" in cmd
        assert "--num_processes=4" in cmd

    def test_trl_no_fsdp_launch(self):
        adapter = _get_adapter("trl")
        config = _make_config(
            hardware={"gpu_count": 4},
            training={"technique": "sft"},
            framework={"backend": "trl"},
        )
        cmd = adapter.launch_command(config)
        assert "accelerate launch" in cmd
        assert "accelerate_config.yaml" not in cmd

    def test_axolotl_fsdp_launch(self):
        adapter = _get_adapter("axolotl")
        config = _make_config(
            hardware={"gpu_count": 4},
            optimization={"fsdp": {"enabled": True}},
            training={"technique": "sft"},
            framework={"backend": "axolotl"},
        )
        cmd = adapter.launch_command(config)
        assert "accelerate_config.yaml" in cmd
        assert "axolotl.cli.train" in cmd

    def test_llamafactory_fsdp_launch(self):
        adapter = _get_adapter("llamafactory")
        config = _make_config(
            hardware={"gpu_count": 4},
            optimization={"fsdp": {"enabled": True}},
            training={"technique": "sft"},
            framework={"backend": "llamafactory"},
        )
        cmd = adapter.launch_command(config)
        assert "accelerate launch" in cmd
        assert "accelerate_config.yaml" in cmd
        assert "llamafactory-cli" in cmd

    def test_llamafactory_no_fsdp_launch(self):
        adapter = _get_adapter("llamafactory")
        config = _make_config(
            training={"technique": "sft"},
            framework={"backend": "llamafactory"},
        )
        cmd = adapter.launch_command(config)
        assert cmd == "llamafactory-cli train config.yaml"

    def test_fromscratch_multinode_launch(self):
        adapter = _get_adapter("from_scratch")
        config = _make_config(
            hardware={"gpu_count": 4, "num_nodes": 2},
            optimization={"fsdp": {"enabled": True}},
            training={"technique": "sft"},
            framework={"backend": "from_scratch"},
        )
        cmd = adapter.launch_command(config)
        assert "torchrun" in cmd
        assert "--nproc_per_node=4" in cmd
        assert "--nnodes=2" in cmd
        assert "MASTER_ADDR" in cmd

    def test_fromscratch_single_node_multi_gpu(self):
        adapter = _get_adapter("from_scratch")
        config = _make_config(
            hardware={"gpu_count": 4},
            training={"technique": "sft"},
            framework={"backend": "from_scratch"},
        )
        cmd = adapter.launch_command(config)
        assert "torchrun" in cmd
        assert "--nproc_per_node=4" in cmd
        assert "--nnodes" not in cmd


# ===========================================================================
# Infrastructure Capability Matrix tests
# ===========================================================================


class TestInfraCapabilityMatrix:
    """Tests for the infrastructure capability matrix."""

    def test_fsdp_frameworks(self):
        frameworks = get_fsdp_frameworks()
        assert "trl" in frameworks
        assert "axolotl" in frameworks
        assert "llamafactory" in frameworks
        assert "from_scratch" in frameworks
        assert "unsloth" not in frameworks
        assert "openrlhf" not in frameworks

    @pytest.mark.parametrize(
        "capability,framework,expected",
        [
            ("fsdp", "trl", "full"),
            ("fsdp", "unsloth", "none"),
            ("fsdp", "torchtune", "internal"),
            ("fsdp", "verl", "internal"),
            ("fsdp", "openrlhf", "none"),
            ("triton", "from_scratch", "native"),
            ("triton", "unsloth", "native"),
            ("triton", "trl", "partial"),
            ("skypilot", "trl", "full"),
            ("skypilot", "verl", "partial"),
        ],
    )
    def test_infra_support_levels(self, capability: str, framework: str, expected: str):
        assert get_infra_support(capability, framework) == expected

    def test_unknown_combination_returns_unknown(self):
        assert get_infra_support("fsdp", "nonexistent") == "unknown"

    def test_all_frameworks_have_fsdp_entry(self):
        """Every framework in the registry should have an FSDP entry."""
        for fw in ["trl", "unsloth", "axolotl", "torchtune", "verl", "openrlhf", "llamafactory", "from_scratch"]:
            level = get_infra_support("fsdp", fw)
            assert level != "unknown", f"Missing FSDP entry for framework '{fw}'"

    def test_all_frameworks_have_triton_entry(self):
        for fw in ["trl", "unsloth", "axolotl", "torchtune", "verl", "openrlhf", "llamafactory", "from_scratch"]:
            level = get_infra_support("triton", fw)
            assert level != "unknown", f"Missing Triton entry for framework '{fw}'"

    def test_all_frameworks_have_skypilot_entry(self):
        for fw in ["trl", "unsloth", "axolotl", "torchtune", "verl", "openrlhf", "llamafactory", "from_scratch"]:
            level = get_infra_support("skypilot", fw)
            assert level != "unknown", f"Missing SkyPilot entry for framework '{fw}'"


# ===========================================================================
# Auto-optimizer FSDP suggestion tests
# ===========================================================================


class TestAutoOptimizerFSDP:
    """Tests for FSDP suggestions in auto_optimizer."""

    def test_suggests_fsdp_for_trl_multi_gpu(self):
        from envelope.hardware.auto_optimizer import suggest_optimizations

        config = _make_config(
            hardware={"gpu_count": 4, "gpu_type": "A100-80GB"},
            model={"name_or_path": "meta-llama/Llama-3.1-70B"},
            training={"technique": "sft"},
            framework={"backend": "trl"},
        )
        suggestions = suggest_optimizations(config)
        assert suggestions.get("optimization.fsdp.enabled") is True

    def test_suggests_deepspeed_for_openrlhf(self):
        from envelope.hardware.auto_optimizer import suggest_optimizations

        config = _make_config(
            hardware={"gpu_count": 4, "gpu_type": "A100-80GB"},
            model={"name_or_path": "meta-llama/Llama-3.1-70B"},
            training={"technique": "grpo"},
            framework={"backend": "openrlhf"},
            reward={"type": "verifiable", "functions": [{"name": "test", "module_path": "test"}]},
        )
        suggestions = suggest_optimizations(config)
        assert suggestions.get("optimization.deepspeed_stage") == 2
        assert "optimization.fsdp.enabled" not in suggestions

    def test_no_fsdp_single_gpu(self):
        from envelope.hardware.auto_optimizer import suggest_optimizations

        config = _make_config(
            hardware={"gpu_count": 1, "gpu_type": "A100-80GB"},
            model={"name_or_path": "meta-llama/Llama-3.1-7B"},
            training={"technique": "sft"},
            framework={"backend": "trl"},
        )
        suggestions = suggest_optimizations(config)
        assert "optimization.fsdp.enabled" not in suggestions
