"""Unit tests for envelope/config/models.py -- Pydantic v2 config models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from envelope.config.models import (
    AttnImplementation,
    ComputeDtype,
    DatasetConfig,
    DatasetFormat,
    ExperimentConfig,
    FlashAttentionVersion,
    FrameworkBackend,
    FrameworkConfig,
    GradientCheckpointingMode,
    HardwareConfig,
    EnvelopeConfig,
    ModelConfig,
    OptimizationConfig,
    OutputConfig,
    PeftConfig,
    PeftMethod,
    PrecisionConfig,
    Quantization,
    REFERENCE_FREE_TECHNIQUES,
    ReferenceModelConfig,
    RewardConfig,
    RewardFunctionConfig,
    RewardType,
    SaveStrategy,
    Stage,
    TECHNIQUE_STAGE_MAP,
    TeacherModelConfig,
    Technique,
    TrainingConfig,
    VllmMode,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_config_dict(**overrides) -> dict:
    """Return the smallest dict that can produce a valid EnvelopeConfig.

    Callers may override any top-level key.
    """
    base = {
        "experiment": {"name": "test-exp"},
        "model": {"name_or_path": "meta-llama/Llama-3.1-8B"},
        "dataset": {"train_uri": "tatsu-lab/alpaca"},
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Enum Tests
# ---------------------------------------------------------------------------


class TestEnums:
    """Validate enum members and their string/int values."""

    def test_stage_values(self):
        assert Stage.SFT == 1
        assert Stage.PREFERENCE == 2
        assert Stage.RL == 3

    @pytest.mark.parametrize(
        "member,value",
        [
            (Technique.SFT, "sft"),
            (Technique.DPO, "dpo"),
            (Technique.SIMPO, "simpo"),
            (Technique.KTO, "kto"),
            (Technique.ORPO, "orpo"),
            (Technique.PPO, "ppo"),
            (Technique.GRPO, "grpo"),
            (Technique.DAPO, "dapo"),
            (Technique.VAPO, "vapo"),
            (Technique.RLOO, "rloo"),
            (Technique.REINFORCE_PP, "reinforce_pp"),
            (Technique.DR_GRPO, "dr_grpo"),
            (Technique.FLOWRL, "flowrl"),
            (Technique.PRIME, "prime"),
            (Technique.GKD, "gkd"),
            (Technique.SDFT, "sdft"),
            (Technique.SDPO, "sdpo"),
            (Technique.GOLD, "gold"),
            (Technique.REWARD_MODELING, "reward_modeling"),
        ],
    )
    def test_technique_values(self, member, value):
        assert member.value == value

    def test_technique_count(self):
        assert len(Technique) == 19

    @pytest.mark.parametrize(
        "member,value",
        [
            (PeftMethod.NONE, "none"),
            (PeftMethod.LORA, "lora"),
            (PeftMethod.QLORA, "qlora"),
            (PeftMethod.DORA, "dora"),
            (PeftMethod.RSLORA, "rslora"),
        ],
    )
    def test_peft_method_values(self, member, value):
        assert member.value == value

    @pytest.mark.parametrize(
        "member,value",
        [
            (ComputeDtype.FP16, "fp16"),
            (ComputeDtype.BF16, "bf16"),
            (ComputeDtype.FP32, "fp32"),
        ],
    )
    def test_compute_dtype_values(self, member, value):
        assert member.value == value

    @pytest.mark.parametrize(
        "member,value",
        [
            (Quantization.NONE, "none"),
            (Quantization.NF4, "nf4"),
            (Quantization.INT8, "int8"),
            (Quantization.GPTQ, "gptq"),
            (Quantization.AWQ, "awq"),
            (Quantization.FP8, "fp8"),
        ],
    )
    def test_quantization_values(self, member, value):
        assert member.value == value

    @pytest.mark.parametrize(
        "enum_cls,bad_value",
        [
            (Technique, "unknown_technique"),
            (PeftMethod, "adapters"),
            (ComputeDtype, "fp64"),
            (Quantization, "int4"),
            (FrameworkBackend, "megatron"),
        ],
    )
    def test_invalid_enum_value_raises(self, enum_cls, bad_value):
        with pytest.raises(ValueError):
            enum_cls(bad_value)

    def test_framework_backend_values(self):
        expected = {"trl", "unsloth", "axolotl", "torchtune", "verl", "openrlhf", "llamafactory", "nemo", "from_scratch"}
        actual = {m.value for m in FrameworkBackend}
        assert actual == expected

    def test_dataset_format_values(self):
        expected = {"chat", "instruction", "preference", "rl"}
        actual = {m.value for m in DatasetFormat}
        assert actual == expected

    def test_reward_type_values(self):
        expected = {"verifiable", "learned", "custom", "combined"}
        actual = {m.value for m in RewardType}
        assert actual == expected

    def test_save_strategy_values(self):
        expected = {"steps", "epoch", "no"}
        actual = {m.value for m in SaveStrategy}
        assert actual == expected

    def test_flash_attention_version_values(self):
        assert FlashAttentionVersion.V2.value == "v2"
        assert FlashAttentionVersion.V3.value == "v3"

    def test_attn_implementation_values(self):
        expected = {"eager", "sdpa", "flash_attention_2"}
        actual = {m.value for m in AttnImplementation}
        assert actual == expected

    def test_gradient_checkpointing_mode_values(self):
        expected = {"full", "unsloth", "selective"}
        actual = {m.value for m in GradientCheckpointingMode}
        assert actual == expected

    def test_vllm_mode_values(self):
        expected = {"colocate", "spmd"}
        actual = {m.value for m in VllmMode}
        assert actual == expected


# ---------------------------------------------------------------------------
# TECHNIQUE_STAGE_MAP
# ---------------------------------------------------------------------------


class TestTechniqueStageMap:
    """Verify the technique-to-stage mapping covers all techniques."""

    def test_all_techniques_mapped(self):
        for technique in Technique:
            assert technique in TECHNIQUE_STAGE_MAP, f"{technique} missing from TECHNIQUE_STAGE_MAP"

    @pytest.mark.parametrize(
        "technique,expected_stage",
        [
            (Technique.SFT, Stage.SFT),
            (Technique.DPO, Stage.PREFERENCE),
            (Technique.SIMPO, Stage.PREFERENCE),
            (Technique.KTO, Stage.PREFERENCE),
            (Technique.ORPO, Stage.PREFERENCE),
            (Technique.PPO, Stage.RL),
            (Technique.GRPO, Stage.RL),
            (Technique.DAPO, Stage.RL),
            (Technique.VAPO, Stage.RL),
            (Technique.RLOO, Stage.RL),
            (Technique.REINFORCE_PP, Stage.RL),
            (Technique.DR_GRPO, Stage.RL),
            (Technique.FLOWRL, Stage.RL),
            (Technique.PRIME, Stage.RL),
            (Technique.GKD, Stage.SFT),
            (Technique.SDFT, Stage.SFT),
            (Technique.SDPO, Stage.RL),
            (Technique.GOLD, Stage.SFT),
            (Technique.REWARD_MODELING, Stage.PREFERENCE),
        ],
    )
    def test_individual_mapping(self, technique, expected_stage):
        assert TECHNIQUE_STAGE_MAP[technique] == expected_stage


# ---------------------------------------------------------------------------
# Sub-model defaults and validation
# ---------------------------------------------------------------------------


class TestExperimentConfig:
    def test_minimal(self):
        cfg = ExperimentConfig(name="exp1")
        assert cfg.name == "exp1"
        assert cfg.description == ""
        assert cfg.tags == []
        assert cfg.seed == 42
        assert cfg.run_id is None

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ExperimentConfig(name="")


class TestModelConfig:
    def test_defaults(self):
        cfg = ModelConfig(name_or_path="my-model")
        assert cfg.revision == "main"
        assert cfg.tokenizer_name_or_path is None
        assert cfg.trust_remote_code is False
        assert cfg.attn_implementation == AttnImplementation.FLASH_ATTENTION_2
        assert cfg.max_seq_length == 2048

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ModelConfig(name_or_path="")

    def test_max_seq_length_must_be_positive(self):
        with pytest.raises(ValidationError):
            ModelConfig(name_or_path="m", max_seq_length=0)


class TestPeftConfig:
    def test_defaults(self):
        cfg = PeftConfig()
        assert cfg.method == PeftMethod.NONE
        assert cfg.r == 16
        assert cfg.lora_alpha == 32
        assert cfg.use_dora is False
        assert cfg.use_rslora is False

    def test_dora_auto_flag(self):
        cfg = PeftConfig(method="dora")
        assert cfg.use_dora is True

    def test_rslora_auto_flag(self):
        cfg = PeftConfig(method="rslora")
        assert cfg.use_rslora is True

    def test_lora_dropout_range(self):
        with pytest.raises(ValidationError):
            PeftConfig(lora_dropout=1.5)
        with pytest.raises(ValidationError):
            PeftConfig(lora_dropout=-0.1)

    def test_rank_must_be_positive(self):
        with pytest.raises(ValidationError):
            PeftConfig(r=0)


class TestPrecisionConfig:
    def test_defaults(self):
        cfg = PrecisionConfig()
        assert cfg.compute_dtype == ComputeDtype.BF16
        assert cfg.quantization == Quantization.NONE
        # Validator sets double_quantization to False when quantization is NONE
        assert cfg.double_quantization is False

    def test_quantization_none_disables_double_quant(self):
        cfg = PrecisionConfig(quantization="none", double_quantization=True)
        assert cfg.double_quantization is False

    def test_nf4_keeps_double_quant(self):
        cfg = PrecisionConfig(quantization="nf4", double_quantization=True)
        assert cfg.double_quantization is True


class TestTrainingConfig:
    def test_defaults(self):
        cfg = TrainingConfig()
        # Default technique is GRPO, so stage is auto-set to RL
        assert cfg.technique == Technique.GRPO
        assert cfg.stage == Stage.RL

    def test_stage_auto_set_from_technique(self):
        cfg = TrainingConfig(technique="sft")
        assert cfg.stage == Stage.SFT

        cfg = TrainingConfig(technique="dpo")
        assert cfg.stage == Stage.PREFERENCE

        cfg = TrainingConfig(technique="grpo")
        assert cfg.stage == Stage.RL

    def test_stage_override_ignored(self):
        """Even if the user passes stage=1, the validator overrides it to match the technique."""
        cfg = TrainingConfig(technique="grpo", stage=1)
        assert cfg.stage == Stage.RL


class TestDatasetConfig:
    def test_minimal(self):
        cfg = DatasetConfig(train_uri="my-dataset")
        assert cfg.split_train == "train"
        assert cfg.format == DatasetFormat.CHAT
        assert cfg.prompt_field == "prompt"

    def test_empty_train_uri_rejected(self):
        with pytest.raises(ValidationError):
            DatasetConfig(train_uri="")

    def test_max_samples_positive(self):
        with pytest.raises(ValidationError):
            DatasetConfig(train_uri="ds", max_samples=0)


class TestRewardConfig:
    def test_defaults(self):
        cfg = RewardConfig()
        assert cfg.type == RewardType.VERIFIABLE
        assert cfg.functions == []
        assert cfg.reward_model is None

    def test_with_function(self):
        cfg = RewardConfig(
            functions=[
                RewardFunctionConfig(name="math", module_path="rewards.math"),
            ]
        )
        assert len(cfg.functions) == 1
        assert cfg.functions[0].weight == 1.0


class TestHardwareConfig:
    def test_defaults(self):
        cfg = HardwareConfig()
        assert cfg.gpu_type == "A100-80GB"
        assert cfg.gpu_count == 1
        assert cfg.num_nodes == 1

    def test_gpu_count_positive(self):
        with pytest.raises(ValidationError):
            HardwareConfig(gpu_count=0)


class TestTeacherModelConfig:
    def test_defaults(self):
        cfg = TeacherModelConfig()
        assert cfg.name_or_path is None
        assert cfg.tokenizer_name_or_path is None
        assert cfg.init_kwargs == {}

    def test_custom_values(self):
        cfg = TeacherModelConfig(
            name_or_path="meta-llama/Llama-3.1-70B",
            tokenizer_name_or_path="meta-llama/Llama-3.1-70B",
            init_kwargs={"torch_dtype": "bfloat16"},
        )
        assert cfg.name_or_path == "meta-llama/Llama-3.1-70B"
        assert cfg.tokenizer_name_or_path == "meta-llama/Llama-3.1-70B"
        assert cfg.init_kwargs == {"torch_dtype": "bfloat16"}


class TestOptimizationConfig:
    def test_defaults(self):
        cfg = OptimizationConfig()
        assert cfg.flash_attention == FlashAttentionVersion.V2
        assert cfg.gradient_checkpointing is True
        assert cfg.vllm_rollout is False
        assert cfg.deepspeed_stage is None

    def test_deepspeed_stage_range(self):
        # Valid
        OptimizationConfig(deepspeed_stage=2)
        OptimizationConfig(deepspeed_stage=3)
        # Invalid
        with pytest.raises(ValidationError):
            OptimizationConfig(deepspeed_stage=1)
        with pytest.raises(ValidationError):
            OptimizationConfig(deepspeed_stage=4)

    def test_vllm_gpu_memory_utilization_range(self):
        with pytest.raises(ValidationError):
            OptimizationConfig(vllm_gpu_memory_utilization=0.0)
        with pytest.raises(ValidationError):
            OptimizationConfig(vllm_gpu_memory_utilization=1.5)


class TestOutputConfig:
    def test_defaults(self):
        cfg = OutputConfig()
        assert cfg.dir == "./output"
        assert cfg.save_strategy == SaveStrategy.STEPS
        assert cfg.report_to == ["tensorboard"]
        assert cfg.push_to_hub is False


class TestFrameworkConfig:
    def test_defaults(self):
        cfg = FrameworkConfig()
        assert cfg.backend == FrameworkBackend.TRL
        assert cfg.version is None
        assert cfg.custom_args == {}


# ---------------------------------------------------------------------------
# EnvelopeConfig (root)
# ---------------------------------------------------------------------------


class TestEnvelopeConfig:
    def test_minimal_config(self):
        """A config with only the required fields should produce a valid model."""
        cfg = EnvelopeConfig.model_validate(_minimal_config_dict())
        assert cfg.experiment.name == "test-exp"
        assert cfg.model.name_or_path == "meta-llama/Llama-3.1-8B"
        assert cfg.dataset.train_uri == "tatsu-lab/alpaca"
        # Defaults
        assert cfg.training.technique == Technique.GRPO
        assert cfg.training.stage == Stage.RL
        assert cfg.framework.backend == FrameworkBackend.TRL

    def test_reference_model_disabled_for_sft(self):
        cfg = EnvelopeConfig.model_validate(
            _minimal_config_dict(training={"technique": "sft"})
        )
        assert cfg.reference_model.enabled is False

    def test_reference_model_disabled_for_simpo(self):
        cfg = EnvelopeConfig.model_validate(
            _minimal_config_dict(training={"technique": "simpo"})
        )
        assert cfg.reference_model.enabled is False

    def test_reference_model_disabled_for_orpo(self):
        cfg = EnvelopeConfig.model_validate(
            _minimal_config_dict(training={"technique": "orpo"})
        )
        assert cfg.reference_model.enabled is False

    def test_reference_model_enabled_for_dpo(self):
        cfg = EnvelopeConfig.model_validate(
            _minimal_config_dict(training={"technique": "dpo"})
        )
        # DPO is NOT in REFERENCE_FREE_TECHNIQUES, so enabled stays True
        assert cfg.reference_model.enabled is True

    def test_teacher_model_defaults(self):
        cfg = EnvelopeConfig.model_validate(_minimal_config_dict())
        assert cfg.teacher_model.name_or_path is None
        assert cfg.teacher_model.tokenizer_name_or_path is None
        assert cfg.teacher_model.init_kwargs == {}

    def test_teacher_model_with_gkd(self):
        cfg = EnvelopeConfig.model_validate(
            _minimal_config_dict(
                training={"technique": "gkd"},
                teacher_model={"name_or_path": "meta-llama/Llama-3.1-70B"},
            )
        )
        assert cfg.teacher_model.name_or_path == "meta-llama/Llama-3.1-70B"

    def test_qlora_auto_sets_nf4(self):
        """QLoRA without explicit quantization should default to NF4."""
        cfg = EnvelopeConfig.model_validate(
            _minimal_config_dict(
                training={
                    "technique": "grpo",
                    "peft": {"method": "qlora"},
                    "precision": {"quantization": "none"},
                }
            )
        )
        assert cfg.training.precision.quantization == Quantization.NF4

    def test_qlora_explicit_quantization_preserved(self):
        cfg = EnvelopeConfig.model_validate(
            _minimal_config_dict(
                training={
                    "technique": "grpo",
                    "peft": {"method": "qlora"},
                    "precision": {"quantization": "int8"},
                }
            )
        )
        assert cfg.training.precision.quantization == Quantization.INT8

    def test_missing_experiment_raises(self):
        with pytest.raises(ValidationError):
            EnvelopeConfig.model_validate(
                {"model": {"name_or_path": "x"}, "dataset": {"train_uri": "ds"}}
            )

    def test_missing_model_raises(self):
        with pytest.raises(ValidationError):
            EnvelopeConfig.model_validate(
                {"experiment": {"name": "e"}, "dataset": {"train_uri": "ds"}}
            )

    def test_missing_dataset_raises(self):
        with pytest.raises(ValidationError):
            EnvelopeConfig.model_validate(
                {"experiment": {"name": "e"}, "model": {"name_or_path": "m"}}
            )

    def test_invalid_technique_raises(self):
        with pytest.raises(ValidationError):
            EnvelopeConfig.model_validate(
                _minimal_config_dict(training={"technique": "imaginary"})
            )

    def test_grpo_config_from_dict(self):
        """Full GRPO config round-trip."""
        data = {
            "experiment": {
                "name": "grpo-test",
                "description": "GRPO unit test",
                "tags": ["test"],
                "seed": 123,
            },
            "model": {
                "name_or_path": "Qwen/Qwen2.5-7B-Instruct",
                "trust_remote_code": True,
                "max_seq_length": 2048,
            },
            "training": {
                "technique": "grpo",
                "peft": {
                    "method": "qlora",
                    "r": 32,
                    "lora_alpha": 64,
                },
                "precision": {
                    "compute_dtype": "bf16",
                    "quantization": "nf4",
                },
                "technique_args": {
                    "num_generations": 16,
                    "beta": 0.04,
                },
            },
            "dataset": {
                "train_uri": "argilla/magpie-ultra-v1.0",
                "format": "rl",
            },
            "reward": {
                "type": "verifiable",
                "functions": [
                    {"name": "math", "module_path": "rewards.math", "weight": 1.0},
                ],
            },
            "framework": {"backend": "trl"},
        }
        cfg = EnvelopeConfig.model_validate(data)
        assert cfg.training.stage == Stage.RL
        assert cfg.training.technique == Technique.GRPO
        assert cfg.training.peft.method == PeftMethod.QLORA
        assert cfg.training.precision.quantization == Quantization.NF4
        assert cfg.experiment.seed == 123
        assert cfg.reward.functions[0].name == "math"


# ---------------------------------------------------------------------------
# REFERENCE_FREE_TECHNIQUES
# ---------------------------------------------------------------------------


class TestReferenceFree:
    def test_sft_is_reference_free(self):
        assert Technique.SFT in REFERENCE_FREE_TECHNIQUES

    def test_simpo_is_reference_free(self):
        assert Technique.SIMPO in REFERENCE_FREE_TECHNIQUES

    def test_orpo_is_reference_free(self):
        assert Technique.ORPO in REFERENCE_FREE_TECHNIQUES

    def test_kto_is_reference_free(self):
        assert Technique.KTO in REFERENCE_FREE_TECHNIQUES

    def test_dpo_needs_reference(self):
        assert Technique.DPO not in REFERENCE_FREE_TECHNIQUES

    def test_grpo_needs_reference(self):
        assert Technique.GRPO not in REFERENCE_FREE_TECHNIQUES

    def test_gkd_is_reference_free(self):
        assert Technique.GKD in REFERENCE_FREE_TECHNIQUES

    def test_sdft_is_reference_free(self):
        assert Technique.SDFT in REFERENCE_FREE_TECHNIQUES

    def test_gold_is_reference_free(self):
        assert Technique.GOLD in REFERENCE_FREE_TECHNIQUES

    def test_sdpo_is_reference_free(self):
        assert Technique.SDPO in REFERENCE_FREE_TECHNIQUES

    def test_reward_modeling_is_reference_free(self):
        assert Technique.REWARD_MODELING in REFERENCE_FREE_TECHNIQUES
