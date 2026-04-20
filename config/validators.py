"""Cross-field validators for envelope configuration.

These validators check constraints that span multiple config sections
and cannot be expressed in a single Pydantic model_validator.
"""

from __future__ import annotations

from envelope.config.models import (
    ComputeDtype,
    FrameworkBackend,
    EnvelopeConfig,
    PeftMethod,
    Quantization,
    Stage,
    Technique,
)


class ConfigValidationError(Exception):
    """Raised when cross-field validation fails."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(f"  - {e}" for e in errors))


def validate_config(config: EnvelopeConfig) -> list[str]:
    """Run all cross-field validations. Returns list of error messages (empty = valid)."""
    errors: list[str] = []
    errors.extend(_validate_peft_quantization(config))
    errors.extend(_validate_hardware_precision(config))
    errors.extend(_validate_rl_requirements(config))
    errors.extend(_validate_preference_dataset(config))
    errors.extend(_validate_framework_technique(config))
    errors.extend(_validate_fsdp(config))
    errors.extend(_validate_teacher_model(config))
    return errors


# --- Worker Daemon Naming ---

WORKER_DAEMON_NAME_PATTERN = "worker-{exp_id}-{recipe_id}"


def validate_worker_daemon_name(daemon_name: str, exp_id: str, recipe_id: str) -> list[str]:
    """Validate worker daemon naming follows the standard pattern: worker-{exp_id}-{recipe_id}.

    Args:
        daemon_name: The daemon name to validate
        exp_id: Experiment ID
        recipe_id: Recipe ID

    Returns:
        List of error messages (empty = valid)
    """
    errors: list[str] = []
    expected_pattern = WORKER_DAEMON_NAME_PATTERN.format(exp_id=exp_id, recipe_id=recipe_id)

    if daemon_name != expected_pattern:
        errors.append(
            f"Worker daemon name must follow pattern '{WORKER_DAEMON_NAME_PATTERN}'. "
            f"Got '{daemon_name}', expected '{expected_pattern}'."
        )

    return errors


def validate_config_or_raise(config: EnvelopeConfig) -> None:
    """Validate config and raise ConfigValidationError if issues found."""
    errors = validate_config(config)
    if errors:
        raise ConfigValidationError(errors)


def _validate_peft_quantization(config: EnvelopeConfig) -> list[str]:
    """QLoRA requires quantization; LoRA should not have quantization by default."""
    errors = []
    peft = config.training.peft
    quant = config.training.precision.quantization

    if peft.method == PeftMethod.QLORA and quant == Quantization.NONE:
        errors.append("QLoRA requires quantization (nf4 or int8). Set training.precision.quantization.")

    if peft.method == PeftMethod.NONE and quant not in (Quantization.NONE, Quantization.GPTQ, Quantization.AWQ):
        errors.append(
            f"Quantization '{quant.value}' without PEFT is unusual. "
            "Training-time quantization (nf4/int8) typically requires LoRA/QLoRA."
        )
    return errors


def _validate_hardware_precision(config: EnvelopeConfig) -> list[str]:
    """Check precision compatibility with hardware."""
    errors = []
    gpu = config.hardware.gpu_type.upper()
    dtype = config.training.precision.compute_dtype
    quant = config.training.precision.quantization

    # BF16 requires Ampere+ (compute capability 8.0+)
    pre_ampere_gpus = {"V100", "T4"}
    if dtype == ComputeDtype.BF16 and any(g in gpu for g in pre_ampere_gpus):
        errors.append(
            f"BF16 not supported on {config.hardware.gpu_type}. "
            "Use fp16 or upgrade to Ampere+ GPU (A100, H100, L40S, RTX4090)."
        )

    # FP8 requires Hopper (H100, H200)
    if quant == Quantization.FP8 and not any(g in gpu for g in ("H100", "H200")):
        errors.append(f"FP8 quantization requires Hopper GPU (H100/H200), got {config.hardware.gpu_type}.")
    return errors


def _validate_rl_requirements(config: EnvelopeConfig) -> list[str]:
    """RL techniques need reward configuration."""
    errors = []
    if config.training.stage == Stage.RL:
        if not config.reward.functions and config.reward.reward_model is None:
            errors.append(
                f"RL technique '{config.training.technique.value}' requires reward configuration. "
                "Set reward.functions or reward.reward_model."
            )
    return errors


def _validate_preference_dataset(config: EnvelopeConfig) -> list[str]:
    """Preference techniques need chosen/rejected fields in dataset."""
    errors = []
    technique = config.training.technique
    preference_techniques = {Technique.DPO, Technique.SIMPO, Technique.ORPO, Technique.REWARD_MODELING}

    if technique in preference_techniques:
        if not config.dataset.chosen_field or not config.dataset.rejected_field:
            errors.append(
                f"Technique '{technique.value}' requires preference data. "
                "Set dataset.chosen_field and dataset.rejected_field."
            )
    return errors


def _validate_framework_technique(config: EnvelopeConfig) -> list[str]:
    """Check that the chosen framework supports the chosen technique.

    This is a soft check — the capability_matrix.py has the full mapping.
    Here we catch the most obvious incompatibilities.
    """
    errors = []
    technique = config.training.technique
    backend = config.framework.backend

    # DAPO/VAPO are only available in veRL
    verl_only = {Technique.DAPO, Technique.VAPO}
    if technique in verl_only and backend != FrameworkBackend.VERL:
        errors.append(
            f"Technique '{technique.value}' is only supported by veRL. "
            f"Got framework.backend='{backend.value}'. Set framework.backend='verl'."
        )

    # FlowRL only in veRL
    if technique == Technique.FLOWRL and backend != FrameworkBackend.VERL:
        errors.append("FlowRL is only supported by veRL. Set framework.backend='verl'.")

    # Unsloth limitations
    if backend == FrameworkBackend.UNSLOTH:
        unsupported_unsloth = {Technique.PPO, Technique.RLOO, Technique.REINFORCE_PP, Technique.DR_GRPO}
        if technique in unsupported_unsloth:
            errors.append(f"Unsloth does not support '{technique.value}'. Use TRL or veRL instead.")

    # Distillation techniques require TRL
    distillation_trl_only = {Technique.GKD, Technique.SDFT, Technique.SDPO, Technique.GOLD}
    if technique in distillation_trl_only and backend != FrameworkBackend.TRL:
        errors.append(
            f"Distillation technique '{technique.value}' is only supported by TRL. "
            f"Got framework.backend='{backend.value}'. Set framework.backend='trl'."
        )

    # Reward modeling requires TRL
    if technique == Technique.REWARD_MODELING and backend != FrameworkBackend.TRL:
        errors.append(
            f"Reward modeling is only supported by TRL. "
            f"Got framework.backend='{backend.value}'. Set framework.backend='trl'."
        )

    return errors


def _validate_fsdp(config: EnvelopeConfig) -> list[str]:
    """Validate FSDP configuration constraints."""
    errors = []
    fsdp = config.optimization.fsdp

    if not fsdp.enabled:
        return errors

    # FSDP requires multi-GPU
    if config.hardware.gpu_count < 2 and config.hardware.num_nodes < 2:
        errors.append(
            "FSDP requires gpu_count >= 2 or num_nodes >= 2. "
            "For single-GPU training, disable FSDP (optimization.fsdp.enabled: false)."
        )

    # FSDP + Unsloth is incompatible
    if config.framework.backend == FrameworkBackend.UNSLOTH:
        errors.append(
            "FSDP is not compatible with Unsloth (single-GPU only). "
            "Use TRL, Axolotl, or from_scratch for FSDP training."
        )

    # FSDP + DeepSpeed is mutually exclusive
    if config.optimization.deepspeed_stage is not None:
        errors.append(
            "FSDP and DeepSpeed cannot be used simultaneously. "
            "Choose one: optimization.fsdp.enabled or optimization.deepspeed_stage."
        )

    # QLoRA + FSDP requires use_orig_params=True
    if config.training.peft.method == PeftMethod.QLORA and not fsdp.use_orig_params:
        errors.append(
            "QLoRA with FSDP requires use_orig_params=True. "
            "Set optimization.fsdp.use_orig_params: true."
        )

    # Frameworks that handle FSDP internally
    internal_fsdp_frameworks = {FrameworkBackend.TORCHTUNE, FrameworkBackend.VERL}
    if config.framework.backend in internal_fsdp_frameworks:
        errors.append(
            f"Framework '{config.framework.backend.value}' manages FSDP internally. "
            "Do not set optimization.fsdp.enabled=true for this framework. "
            "Configure distributed training through the framework's own settings."
        )

    # CPU offload + fp16 mixed precision is unstable
    if fsdp.cpu_offload and fsdp.mixed_precision.value == "fp16":
        errors.append(
            "FSDP CPU offload with FP16 mixed precision can cause instability. "
            "Use BF16 mixed precision or disable CPU offload."
        )

    return errors


def _validate_teacher_model(config: EnvelopeConfig) -> list[str]:
    """Distillation techniques that use an external teacher need teacher_model config."""
    errors = []
    technique = config.training.technique

    # GKD and GOLD require an external teacher model
    teacher_required = {Technique.GKD, Technique.GOLD}
    if technique in teacher_required and not config.teacher_model.name_or_path:
        errors.append(
            f"Technique '{technique.value}' requires an external teacher model. "
            "Set teacher_model.name_or_path."
        )

    return errors
