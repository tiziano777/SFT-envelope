"""Unit tests for framework adapters and the capability matrix."""

from __future__ import annotations

import pytest

from envelope.config.models import (
    FrameworkBackend,
    EnvelopeConfig,
    PeftMethod,
)
from envelope.frameworks.base import BaseFrameworkAdapter
from envelope.frameworks.capability_matrix import (
    check_or_raise,
    get_compatible_frameworks,
    get_compatible_techniques,
    is_compatible,
)
from envelope.registry import discover_plugins, framework_registry

# Ensure all plugins are registered
discover_plugins()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_adapter(name: str) -> BaseFrameworkAdapter:
    cls = framework_registry.get(name)
    return cls()


def _make_config(**overrides) -> EnvelopeConfig:
    """Build a minimal EnvelopeConfig with optional overrides."""
    base = {
        "experiment": {"name": "fw-test"},
        "model": {"name_or_path": "meta-llama/Llama-3.1-8B"},
        "dataset": {"train_uri": "tatsu-lab/alpaca"},
    }
    base.update(overrides)
    return EnvelopeConfig.model_validate(base)


# ---------------------------------------------------------------------------
# Framework metadata
# ---------------------------------------------------------------------------

ALL_FRAMEWORKS = [
    ("trl", "HuggingFace TRL"),
    ("unsloth", "Unsloth"),
    ("axolotl", "Axolotl"),
    ("torchtune", "Torchtune (PyTorch)"),
    ("verl", "veRL (ByteDance)"),
    ("openrlhf", "OpenRLHF"),
    ("llamafactory", "LlamaFactory"),
]

ALL_FRAMEWORK_NAMES = [fw[0] for fw in ALL_FRAMEWORKS]


class TestFrameworkMetadata:
    @pytest.mark.parametrize("name,display_name", ALL_FRAMEWORKS)
    def test_name(self, name, display_name):
        adapter = _get_adapter(name)
        assert adapter.name == name

    @pytest.mark.parametrize("name,display_name", ALL_FRAMEWORKS)
    def test_display_name(self, name, display_name):
        adapter = _get_adapter(name)
        assert adapter.display_name == display_name


# ---------------------------------------------------------------------------
# template_name
# ---------------------------------------------------------------------------


class TestTemplateName:
    def test_trl_grpo_template(self):
        adapter = _get_adapter("trl")
        assert adapter.template_name("grpo") == "train_grpo_trl.py.j2"

    def test_trl_sft_template(self):
        adapter = _get_adapter("trl")
        assert adapter.template_name("sft") == "train_sft_trl.py.j2"

    def test_unsloth_template(self):
        adapter = _get_adapter("unsloth")
        assert adapter.template_name("sft") == "train_sft_unsloth.py.j2"

    def test_axolotl_template(self):
        adapter = _get_adapter("axolotl")
        assert adapter.template_name("sft") == "train_sft_axolotl.yaml.j2"

    def test_torchtune_template(self):
        adapter = _get_adapter("torchtune")
        assert adapter.template_name("sft") == "train_sft_torchtune.yaml.j2"

    def test_verl_template(self):
        adapter = _get_adapter("verl")
        assert adapter.template_name("grpo") == "train_grpo_verl.sh.j2"

    def test_openrlhf_template(self):
        adapter = _get_adapter("openrlhf")
        assert adapter.template_name("grpo") == "train_grpo_openrlhf.sh.j2"

    def test_llamafactory_template(self):
        adapter = _get_adapter("llamafactory")
        assert adapter.template_name("sft") == "train_sft_llamafactory.yaml.j2"

    @pytest.mark.parametrize("name", ALL_FRAMEWORK_NAMES)
    def test_template_contains_technique(self, name):
        adapter = _get_adapter(name)
        template = adapter.template_name("sft")
        assert "sft" in template
        assert name in template or name.replace("_", "") in template.replace("_", "")


# ---------------------------------------------------------------------------
# requirements
# ---------------------------------------------------------------------------


class TestRequirements:
    @pytest.mark.parametrize("name", ALL_FRAMEWORK_NAMES)
    def test_returns_non_empty_list(self, name):
        adapter = _get_adapter(name)
        config = _make_config()
        reqs = adapter.requirements(config)
        assert isinstance(reqs, list)
        assert len(reqs) >= 1

    @pytest.mark.parametrize("name", ALL_FRAMEWORK_NAMES)
    def test_all_require_torch(self, name):
        adapter = _get_adapter(name)
        config = _make_config()
        reqs = adapter.requirements(config)
        assert any("torch" in r for r in reqs)

    def test_trl_with_peft_includes_peft(self):
        adapter = _get_adapter("trl")
        config = _make_config(
            training={"technique": "sft", "peft": {"method": "lora"}}
        )
        reqs = adapter.requirements(config)
        assert any("peft" in r for r in reqs)

    def test_trl_without_peft_no_peft(self):
        adapter = _get_adapter("trl")
        config = _make_config(
            training={"technique": "sft", "peft": {"method": "none"}}
        )
        reqs = adapter.requirements(config)
        assert not any(r.startswith("peft") for r in reqs)

    def test_trl_with_nf4_includes_bitsandbytes(self):
        adapter = _get_adapter("trl")
        config = _make_config(
            training={
                "technique": "grpo",
                "peft": {"method": "qlora"},
                "precision": {"quantization": "nf4"},
            }
        )
        reqs = adapter.requirements(config)
        assert any("bitsandbytes" in r for r in reqs)

    def test_trl_with_wandb_includes_wandb(self):
        adapter = _get_adapter("trl")
        config = _make_config(output={"report_to": ["wandb"]})
        reqs = adapter.requirements(config)
        assert any("wandb" in r for r in reqs)

    def test_trl_with_vllm_includes_vllm(self):
        adapter = _get_adapter("trl")
        config = _make_config(optimization={"vllm_rollout": True})
        reqs = adapter.requirements(config)
        assert any("vllm" in r for r in reqs)


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------


class TestValidateConfig:
    def test_trl_supports_sft(self):
        adapter = _get_adapter("trl")
        config = _make_config(training={"technique": "sft"})
        assert adapter.validate_config(config) == []

    def test_trl_supports_grpo(self):
        adapter = _get_adapter("trl")
        config = _make_config(training={"technique": "grpo"})
        assert adapter.validate_config(config) == []

    def test_trl_rejects_dapo(self):
        adapter = _get_adapter("trl")
        config = _make_config(training={"technique": "dapo"})
        errors = adapter.validate_config(config)
        assert len(errors) == 1
        assert "dapo" in errors[0].lower()

    def test_unsloth_rejects_ppo(self):
        adapter = _get_adapter("unsloth")
        config = _make_config(training={"technique": "ppo"})
        errors = adapter.validate_config(config)
        assert any("ppo" in e.lower() for e in errors)

    def test_unsloth_rejects_multi_gpu(self):
        adapter = _get_adapter("unsloth")
        config = _make_config(
            training={"technique": "sft"},
            hardware={"gpu_count": 4},
        )
        errors = adapter.validate_config(config)
        assert any("single-gpu" in e.lower() or "single" in e.lower() for e in errors)

    def test_axolotl_supports_sft(self):
        adapter = _get_adapter("axolotl")
        config = _make_config(training={"technique": "sft"})
        assert adapter.validate_config(config) == []

    def test_axolotl_rejects_grpo(self):
        adapter = _get_adapter("axolotl")
        config = _make_config(training={"technique": "grpo"})
        errors = adapter.validate_config(config)
        assert len(errors) == 1

    def test_torchtune_rejects_grpo(self):
        adapter = _get_adapter("torchtune")
        config = _make_config(training={"technique": "grpo"})
        errors = adapter.validate_config(config)
        assert len(errors) == 1

    def test_verl_supports_grpo(self):
        adapter = _get_adapter("verl")
        config = _make_config(training={"technique": "grpo"})
        assert adapter.validate_config(config) == []

    def test_verl_rejects_sft(self):
        adapter = _get_adapter("verl")
        config = _make_config(training={"technique": "sft"})
        errors = adapter.validate_config(config)
        assert len(errors) == 1

    def test_openrlhf_supports_grpo(self):
        adapter = _get_adapter("openrlhf")
        config = _make_config(training={"technique": "grpo"})
        assert adapter.validate_config(config) == []

    def test_openrlhf_rejects_dapo(self):
        adapter = _get_adapter("openrlhf")
        config = _make_config(training={"technique": "dapo"})
        errors = adapter.validate_config(config)
        assert len(errors) == 1

    def test_llamafactory_supports_sft(self):
        adapter = _get_adapter("llamafactory")
        config = _make_config(training={"technique": "sft"})
        assert adapter.validate_config(config) == []

    def test_trl_supports_gkd(self):
        adapter = _get_adapter("trl")
        config = _make_config(
            training={"technique": "gkd"},
            teacher_model={"name_or_path": "meta-llama/Llama-3.1-70B"},
        )
        assert adapter.validate_config(config) == []

    def test_trl_supports_reward_modeling(self):
        adapter = _get_adapter("trl")
        config = _make_config(training={"technique": "reward_modeling"})
        assert adapter.validate_config(config) == []

    def test_llamafactory_rejects_grpo(self):
        adapter = _get_adapter("llamafactory")
        config = _make_config(training={"technique": "grpo"})
        errors = adapter.validate_config(config)
        assert len(errors) == 1


# ---------------------------------------------------------------------------
# launch_command
# ---------------------------------------------------------------------------


class TestLaunchCommand:
    def test_trl_single_gpu(self):
        adapter = _get_adapter("trl")
        config = _make_config(hardware={"gpu_count": 1})
        cmd = adapter.launch_command(config)
        assert cmd == "python train.py"

    def test_trl_multi_gpu(self):
        adapter = _get_adapter("trl")
        config = _make_config(hardware={"gpu_count": 4})
        cmd = adapter.launch_command(config)
        assert "accelerate launch" in cmd
        assert "--num_processes=4" in cmd

    def test_unsloth_always_python(self):
        adapter = _get_adapter("unsloth")
        config = _make_config()
        cmd = adapter.launch_command(config)
        assert cmd == "python train.py"

    def test_axolotl_single_gpu(self):
        adapter = _get_adapter("axolotl")
        config = _make_config(hardware={"gpu_count": 1})
        cmd = adapter.launch_command(config)
        assert "axolotl" in cmd
        assert "config.yaml" in cmd

    def test_axolotl_multi_gpu(self):
        adapter = _get_adapter("axolotl")
        config = _make_config(hardware={"gpu_count": 4})
        cmd = adapter.launch_command(config)
        assert "accelerate launch" in cmd

    def test_torchtune_single_gpu_lora(self):
        adapter = _get_adapter("torchtune")
        config = _make_config(
            hardware={"gpu_count": 1},
            training={"technique": "sft", "peft": {"method": "lora"}},
        )
        cmd = adapter.launch_command(config)
        assert "tune run" in cmd
        assert "lora" in cmd
        assert "single_device" in cmd

    def test_torchtune_multi_gpu(self):
        adapter = _get_adapter("torchtune")
        config = _make_config(
            hardware={"gpu_count": 4},
            training={"technique": "sft", "peft": {"method": "lora"}},
        )
        cmd = adapter.launch_command(config)
        assert "distributed" in cmd
        assert "--nproc_per_node 4" in cmd

    def test_torchtune_full_finetune(self):
        adapter = _get_adapter("torchtune")
        config = _make_config(
            training={"technique": "sft", "peft": {"method": "none"}},
        )
        cmd = adapter.launch_command(config)
        assert "full_finetune" in cmd

    def test_verl_bash(self):
        adapter = _get_adapter("verl")
        config = _make_config(training={"technique": "grpo"})
        cmd = adapter.launch_command(config)
        assert cmd == "bash train.sh"

    def test_openrlhf_bash(self):
        adapter = _get_adapter("openrlhf")
        config = _make_config(training={"technique": "grpo"})
        cmd = adapter.launch_command(config)
        assert cmd == "bash train.sh"

    def test_llamafactory_cmd(self):
        adapter = _get_adapter("llamafactory")
        config = _make_config(training={"technique": "sft"})
        cmd = adapter.launch_command(config)
        assert "llamafactory-cli" in cmd
        assert "config.yaml" in cmd


# ---------------------------------------------------------------------------
# Capability Matrix
# ---------------------------------------------------------------------------


class TestCapabilityMatrix:
    def test_sft_trl_compatible(self):
        assert is_compatible("sft", "trl") is True

    def test_grpo_trl_compatible(self):
        assert is_compatible("grpo", "trl") is True

    def test_grpo_verl_compatible(self):
        assert is_compatible("grpo", "verl") is True

    def test_dapo_verl_only(self):
        assert is_compatible("dapo", "verl") is True
        assert is_compatible("dapo", "trl") is False
        assert is_compatible("dapo", "unsloth") is False

    def test_vapo_verl_only(self):
        assert is_compatible("vapo", "verl") is True
        assert is_compatible("vapo", "trl") is False

    def test_unknown_combo_returns_false(self):
        assert is_compatible("imaginary", "trl") is False

    def test_sft_verl_not_compatible(self):
        assert is_compatible("sft", "verl") is False

    @pytest.mark.parametrize(
        "technique,expected_frameworks",
        [
            ("sft", ["axolotl", "from_scratch", "llamafactory", "nemo", "openrlhf", "torchtune", "trl", "unsloth"]),
            ("dapo", ["from_scratch", "verl"]),
            ("vapo", ["from_scratch", "verl"]),
        ],
    )
    def test_get_compatible_frameworks(self, technique, expected_frameworks):
        result = get_compatible_frameworks(technique)
        assert result == expected_frameworks

    def test_get_compatible_techniques_trl(self):
        result = get_compatible_techniques("trl")
        assert "sft" in result
        assert "dpo" in result
        assert "grpo" in result
        assert "gkd" in result
        assert "sdft" in result
        assert "sdpo" in result
        assert "gold" in result
        assert "reward_modeling" in result
        assert "dapo" not in result

    def test_get_compatible_techniques_verl(self):
        result = get_compatible_techniques("verl")
        assert "grpo" in result
        assert "dapo" in result
        assert "vapo" in result
        assert "sft" not in result

    def test_check_or_raise_valid(self):
        # Should not raise
        check_or_raise("grpo", "trl")

    def test_check_or_raise_invalid(self):
        with pytest.raises(ValueError, match="does not support"):
            check_or_raise("dapo", "trl")

    def test_check_or_raise_error_includes_compatible(self):
        with pytest.raises(ValueError, match="verl"):
            check_or_raise("dapo", "trl")

    def test_gkd_trl_compatible(self):
        assert is_compatible("gkd", "trl") is True

    def test_sdft_trl_compatible(self):
        assert is_compatible("sdft", "trl") is True

    def test_sdpo_trl_compatible(self):
        assert is_compatible("sdpo", "trl") is True

    def test_gold_trl_compatible(self):
        assert is_compatible("gold", "trl") is True

    def test_reward_modeling_trl_compatible(self):
        assert is_compatible("reward_modeling", "trl") is True

    def test_gkd_not_compatible_with_verl(self):
        assert is_compatible("gkd", "verl") is False

    def test_reward_modeling_not_compatible_with_verl(self):
        assert is_compatible("reward_modeling", "verl") is False
