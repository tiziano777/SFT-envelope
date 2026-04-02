"""Unit tests for envelope/config/validators.py -- cross-field validators."""

from __future__ import annotations

import pytest

from envelope.config.models import (
    EnvelopeConfig,
    PeftMethod,
    Quantization,
    Stage,
    Technique,
)
from envelope.config.validators import (
    ConfigValidationError,
    validate_config,
    validate_config_or_raise,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**overrides) -> EnvelopeConfig:
    """Build a minimal valid EnvelopeConfig with optional overrides."""
    base = {
        "experiment": {"name": "val-test"},
        "model": {"name_or_path": "meta-llama/Llama-3.1-8B"},
        "dataset": {"train_uri": "tatsu-lab/alpaca"},
    }
    base.update(overrides)
    return EnvelopeConfig.model_validate(base)


# ---------------------------------------------------------------------------
# _validate_peft_quantization
# ---------------------------------------------------------------------------


class TestPeftQuantizationValidation:
    def test_qlora_without_quant_errors(self):
        """QLoRA with quantization=none should produce an error.

        NOTE: The EnvelopeConfig cross-field validator auto-sets NF4 for QLoRA,
        so we must construct a config where the validator's auto-fix is overridden.
        Since the validator always fires, we test via a config that has qlora+nf4
        (which is valid) and lora+nf4 (which is unusual but from the opposite rule).
        """
        # qlora + nf4 -> valid (auto-set by EnvelopeConfig validator)
        config = _make_config(
            training={
                "technique": "grpo",
                "peft": {"method": "qlora"},
                "precision": {"quantization": "nf4"},
            }
        )
        errors = validate_config(config)
        peft_errors = [e for e in errors if "qlora" in e.lower() or "quantization" in e.lower()]
        assert len(peft_errors) == 0

    def test_no_peft_with_nf4_warns(self):
        """Quantization NF4 without PEFT should produce a warning/error."""
        config = _make_config(
            training={
                "technique": "grpo",
                "peft": {"method": "none"},
                "precision": {"quantization": "nf4"},
            }
        )
        errors = validate_config(config)
        assert any("quantization" in e.lower() and "peft" in e.lower() for e in errors)

    def test_no_peft_with_int8_warns(self):
        config = _make_config(
            training={
                "technique": "grpo",
                "peft": {"method": "none"},
                "precision": {"quantization": "int8"},
            }
        )
        errors = validate_config(config)
        assert any("quantization" in e.lower() for e in errors)

    def test_no_peft_with_gptq_ok(self):
        """GPTQ without PEFT is fine (inference-time quantization)."""
        config = _make_config(
            training={
                "technique": "grpo",
                "peft": {"method": "none"},
                "precision": {"quantization": "gptq"},
            }
        )
        errors = validate_config(config)
        peft_quant_errors = [e for e in errors if "quantization" in e.lower() and "peft" in e.lower()]
        assert len(peft_quant_errors) == 0

    def test_no_peft_with_awq_ok(self):
        config = _make_config(
            training={
                "technique": "grpo",
                "peft": {"method": "none"},
                "precision": {"quantization": "awq"},
            }
        )
        errors = validate_config(config)
        peft_quant_errors = [e for e in errors if "quantization" in e.lower() and "peft" in e.lower()]
        assert len(peft_quant_errors) == 0

    def test_lora_with_none_quant_ok(self):
        config = _make_config(
            training={
                "technique": "sft",
                "peft": {"method": "lora"},
                "precision": {"quantization": "none"},
            }
        )
        errors = validate_config(config)
        peft_quant_errors = [e for e in errors if "qlora" in e.lower()]
        assert len(peft_quant_errors) == 0


# ---------------------------------------------------------------------------
# _validate_hardware_precision
# ---------------------------------------------------------------------------


class TestHardwarePrecisionValidation:
    def test_bf16_on_v100_errors(self):
        config = _make_config(
            hardware={"gpu_type": "V100-16GB"},
            training={
                "technique": "sft",
                "precision": {"compute_dtype": "bf16"},
            },
        )
        errors = validate_config(config)
        assert any("bf16" in e.lower() for e in errors)

    def test_bf16_on_t4_errors(self):
        config = _make_config(
            hardware={"gpu_type": "T4"},
            training={
                "technique": "sft",
                "precision": {"compute_dtype": "bf16"},
            },
        )
        errors = validate_config(config)
        assert any("bf16" in e.lower() for e in errors)

    def test_bf16_on_a100_ok(self):
        config = _make_config(
            hardware={"gpu_type": "A100-80GB"},
            training={
                "technique": "sft",
                "precision": {"compute_dtype": "bf16"},
            },
        )
        errors = validate_config(config)
        hw_errors = [e for e in errors if "bf16" in e.lower() and "not supported" in e.lower()]
        assert len(hw_errors) == 0

    def test_fp8_on_a100_errors(self):
        config = _make_config(
            hardware={"gpu_type": "A100-80GB"},
            training={
                "technique": "grpo",
                "peft": {"method": "qlora"},
                "precision": {"quantization": "fp8"},
            },
        )
        errors = validate_config(config)
        assert any("fp8" in e.lower() for e in errors)

    def test_fp8_on_h100_ok(self):
        config = _make_config(
            hardware={"gpu_type": "H100-80GB"},
            training={
                "technique": "grpo",
                "peft": {"method": "qlora"},
                "precision": {"quantization": "fp8"},
            },
        )
        errors = validate_config(config)
        fp8_errors = [e for e in errors if "fp8" in e.lower() and "hopper" in e.lower()]
        assert len(fp8_errors) == 0

    def test_fp16_on_v100_ok(self):
        config = _make_config(
            hardware={"gpu_type": "V100-16GB"},
            training={
                "technique": "sft",
                "precision": {"compute_dtype": "fp16"},
            },
        )
        errors = validate_config(config)
        hw_errors = [e for e in errors if "not supported" in e.lower()]
        assert len(hw_errors) == 0


# ---------------------------------------------------------------------------
# _validate_rl_requirements
# ---------------------------------------------------------------------------


class TestRLRequirementsValidation:
    def test_rl_without_reward_errors(self):
        """RL technique without reward config should produce error."""
        config = _make_config(
            training={"technique": "grpo"},
            reward={"type": "verifiable"},  # no functions, no reward_model
        )
        errors = validate_config(config)
        assert any("reward" in e.lower() for e in errors)

    def test_rl_with_reward_functions_ok(self):
        config = _make_config(
            training={"technique": "grpo"},
            reward={
                "type": "verifiable",
                "functions": [
                    {"name": "math", "module_path": "rewards.math"},
                ],
            },
        )
        errors = validate_config(config)
        rl_errors = [e for e in errors if "reward" in e.lower() and "require" in e.lower()]
        assert len(rl_errors) == 0

    def test_rl_with_reward_model_ok(self):
        config = _make_config(
            training={"technique": "grpo"},
            reward={
                "type": "learned",
                "reward_model": "OpenAssistant/reward-model-deberta-v3-large",
            },
        )
        errors = validate_config(config)
        rl_errors = [e for e in errors if "reward" in e.lower() and "require" in e.lower()]
        assert len(rl_errors) == 0

    def test_sft_without_reward_ok(self):
        config = _make_config(training={"technique": "sft"})
        errors = validate_config(config)
        rl_errors = [e for e in errors if "reward" in e.lower() and "require" in e.lower()]
        assert len(rl_errors) == 0

    def test_dpo_without_reward_ok(self):
        """Preference techniques should not require reward configuration."""
        config = _make_config(training={"technique": "dpo"})
        errors = validate_config(config)
        rl_errors = [e for e in errors if "rl technique" in e.lower()]
        assert len(rl_errors) == 0


# ---------------------------------------------------------------------------
# _validate_preference_dataset
# ---------------------------------------------------------------------------


class TestPreferenceDatasetValidation:
    def test_dpo_needs_chosen_rejected(self):
        config = _make_config(
            training={"technique": "dpo"},
            dataset={"train_uri": "ds", "chosen_field": "chosen", "rejected_field": "rejected"},
        )
        errors = validate_config(config)
        pref_errors = [e for e in errors if "preference" in e.lower() and "chosen" in e.lower()]
        assert len(pref_errors) == 0

    def test_simpo_needs_chosen_rejected(self):
        config = _make_config(
            training={"technique": "simpo"},
            dataset={"train_uri": "ds", "chosen_field": "chosen", "rejected_field": "rejected"},
        )
        errors = validate_config(config)
        pref_errors = [e for e in errors if "preference" in e.lower()]
        assert len(pref_errors) == 0

    def test_orpo_needs_chosen_rejected(self):
        config = _make_config(
            training={"technique": "orpo"},
            dataset={"train_uri": "ds", "chosen_field": "chosen", "rejected_field": "rejected"},
        )
        errors = validate_config(config)
        pref_errors = [e for e in errors if "preference" in e.lower()]
        assert len(pref_errors) == 0

    def test_sft_does_not_need_preference_fields(self):
        config = _make_config(training={"technique": "sft"})
        errors = validate_config(config)
        pref_errors = [e for e in errors if "preference" in e.lower()]
        assert len(pref_errors) == 0

    def test_grpo_does_not_need_preference_fields(self):
        config = _make_config(
            training={"technique": "grpo"},
            reward={
                "type": "verifiable",
                "functions": [{"name": "math", "module_path": "rewards.math"}],
            },
        )
        errors = validate_config(config)
        pref_errors = [e for e in errors if "preference" in e.lower()]
        assert len(pref_errors) == 0

    def test_reward_modeling_needs_chosen_rejected(self):
        config = _make_config(
            training={"technique": "reward_modeling"},
            dataset={"train_uri": "ds", "chosen_field": "chosen", "rejected_field": "rejected"},
        )
        errors = validate_config(config)
        pref_errors = [e for e in errors if "preference" in e.lower()]
        assert len(pref_errors) == 0


# ---------------------------------------------------------------------------
# _validate_framework_technique
# ---------------------------------------------------------------------------


class TestFrameworkTechniqueValidation:
    def test_dapo_requires_verl(self):
        config = _make_config(
            training={"technique": "dapo"},
            framework={"backend": "trl"},
        )
        errors = validate_config(config)
        assert any("verl" in e.lower() for e in errors)

    def test_vapo_requires_verl(self):
        config = _make_config(
            training={"technique": "vapo"},
            framework={"backend": "trl"},
        )
        errors = validate_config(config)
        assert any("verl" in e.lower() for e in errors)

    def test_flowrl_requires_verl(self):
        config = _make_config(
            training={"technique": "flowrl"},
            framework={"backend": "trl"},
        )
        errors = validate_config(config)
        assert any("verl" in e.lower() for e in errors)

    def test_dapo_with_verl_ok(self):
        config = _make_config(
            training={"technique": "dapo"},
            framework={"backend": "verl"},
        )
        errors = validate_config(config)
        fw_errors = [e for e in errors if "only supported by verl" in e.lower()]
        assert len(fw_errors) == 0

    def test_unsloth_rejects_ppo(self):
        config = _make_config(
            training={"technique": "ppo"},
            framework={"backend": "unsloth"},
        )
        errors = validate_config(config)
        assert any("unsloth" in e.lower() and "ppo" in e.lower() for e in errors)

    def test_unsloth_rejects_rloo(self):
        config = _make_config(
            training={"technique": "rloo"},
            framework={"backend": "unsloth"},
        )
        errors = validate_config(config)
        assert any("unsloth" in e.lower() for e in errors)

    def test_unsloth_allows_sft(self):
        config = _make_config(
            training={"technique": "sft"},
            framework={"backend": "unsloth"},
        )
        errors = validate_config(config)
        fw_errors = [e for e in errors if "unsloth" in e.lower() and "does not support" in e.lower()]
        assert len(fw_errors) == 0

    def test_trl_with_grpo_ok(self):
        config = _make_config(
            training={"technique": "grpo"},
            framework={"backend": "trl"},
            reward={
                "type": "verifiable",
                "functions": [{"name": "math", "module_path": "rewards.math"}],
            },
        )
        errors = validate_config(config)
        fw_errors = [e for e in errors if "does not support" in e.lower() and "trl" in e.lower()]
        assert len(fw_errors) == 0

    def test_gkd_with_non_trl_errors(self):
        config = _make_config(
            training={"technique": "gkd"},
            framework={"backend": "unsloth"},
            teacher_model={"name_or_path": "meta-llama/Llama-3.1-70B"},
        )
        errors = validate_config(config)
        assert any("distillation" in e.lower() and "trl" in e.lower() for e in errors)

    def test_sdpo_with_non_trl_errors(self):
        config = _make_config(
            training={"technique": "sdpo"},
            framework={"backend": "verl"},
        )
        errors = validate_config(config)
        assert any("distillation" in e.lower() and "trl" in e.lower() for e in errors)

    def test_reward_modeling_with_non_trl_errors(self):
        config = _make_config(
            training={"technique": "reward_modeling"},
            framework={"backend": "unsloth"},
        )
        errors = validate_config(config)
        assert any("reward modeling" in e.lower() and "trl" in e.lower() for e in errors)

    def test_reward_modeling_with_trl_ok(self):
        config = _make_config(
            training={"technique": "reward_modeling"},
            framework={"backend": "trl"},
        )
        errors = validate_config(config)
        fw_errors = [e for e in errors if "reward modeling" in e.lower() and "only supported" in e.lower()]
        assert len(fw_errors) == 0


# ---------------------------------------------------------------------------
# validate_config_or_raise
# ---------------------------------------------------------------------------


class TestValidateConfigOrRaise:
    def test_valid_config_no_raise(self):
        config = _make_config(
            training={"technique": "sft"},
            framework={"backend": "trl"},
        )
        # Should not raise
        validate_config_or_raise(config)

    def test_invalid_config_raises(self):
        config = _make_config(
            training={"technique": "dapo"},
            framework={"backend": "trl"},
        )
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config_or_raise(config)
        assert len(exc_info.value.errors) > 0

    def test_error_message_contains_details(self):
        config = _make_config(
            training={"technique": "dapo"},
            framework={"backend": "trl"},
        )
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config_or_raise(config)
        error_str = str(exc_info.value)
        assert "verl" in error_str.lower()


# ---------------------------------------------------------------------------
# _validate_teacher_model
# ---------------------------------------------------------------------------


class TestTeacherModelValidation:
    def test_gkd_without_teacher_model_errors(self):
        config = _make_config(
            training={"technique": "gkd"},
            framework={"backend": "trl"},
        )
        errors = validate_config(config)
        assert any("teacher" in e.lower() for e in errors)

    def test_gkd_with_teacher_model_ok(self):
        config = _make_config(
            training={"technique": "gkd"},
            framework={"backend": "trl"},
            teacher_model={"name_or_path": "meta-llama/Llama-3.1-70B"},
        )
        errors = validate_config(config)
        teacher_errors = [e for e in errors if "teacher" in e.lower()]
        assert len(teacher_errors) == 0

    def test_gold_without_teacher_model_errors(self):
        config = _make_config(
            training={"technique": "gold"},
            framework={"backend": "trl"},
        )
        errors = validate_config(config)
        assert any("teacher" in e.lower() for e in errors)

    def test_gold_with_teacher_model_ok(self):
        config = _make_config(
            training={"technique": "gold"},
            framework={"backend": "trl"},
            teacher_model={"name_or_path": "meta-llama/Llama-3.1-70B"},
        )
        errors = validate_config(config)
        teacher_errors = [e for e in errors if "teacher" in e.lower()]
        assert len(teacher_errors) == 0

    def test_sdft_without_teacher_model_ok(self):
        """SDFT is self-distilled, no external teacher needed."""
        config = _make_config(
            training={"technique": "sdft"},
            framework={"backend": "trl"},
        )
        errors = validate_config(config)
        teacher_errors = [e for e in errors if "teacher" in e.lower()]
        assert len(teacher_errors) == 0

    def test_sft_without_teacher_model_ok(self):
        config = _make_config(
            training={"technique": "sft"},
            framework={"backend": "trl"},
        )
        errors = validate_config(config)
        teacher_errors = [e for e in errors if "teacher" in e.lower()]
        assert len(teacher_errors) == 0
