"""Pydantic v2 models for the complete configuration schema.

Every YAML field maps to a typed, validated model. This is the single source of truth
for configuration structure across the entire envelope system.
"""

from __future__ import annotations
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ─── Enums ───


class Stage(int, Enum):
    SFT = 1
    PREFERENCE = 2
    RL = 3
    MERGE = 4


class Technique(str, Enum):
    # Stage 1
    SFT = "sft"
    # Stage 2
    DPO = "dpo"
    SIMPO = "simpo"
    KTO = "kto"
    ORPO = "orpo"
    # Stage 3 - PPO family
    PPO = "ppo"
    GRPO = "grpo"
    DAPO = "dapo"
    VAPO = "vapo"
    # Stage 3 - REINFORCE family
    RLOO = "rloo"
    REINFORCE_PP = "reinforce_pp"
    DR_GRPO = "dr_grpo"
    # Stage 3 - Flow
    FLOWRL = "flowrl"
    PRIME = "prime"
    # Distillation
    GKD = "gkd"
    SDFT = "sdft"
    SDPO = "sdpo"
    GOLD = "gold"
    # Reward modeling
    REWARD_MODELING = "reward_modeling"


class PeftMethod(str, Enum):
    NONE = "none"
    LORA = "lora"
    QLORA = "qlora"
    DORA = "dora"
    RSLORA = "rslora"


class ComputeDtype(str, Enum):
    FP16 = "fp16"
    BF16 = "bf16"
    FP32 = "fp32"


class Quantization(str, Enum):
    NONE = "none"
    NF4 = "nf4"
    INT8 = "int8"
    GPTQ = "gptq"
    AWQ = "awq"
    FP8 = "fp8"


class DatasetFormat(str, Enum):
    CHAT = "chat"
    INSTRUCTION = "instruction"
    PREFERENCE = "preference"
    RL = "rl"


class RewardType(str, Enum):
    VERIFIABLE = "verifiable"
    LEARNED = "learned"
    CUSTOM = "custom"
    COMBINED = "combined"


class FlashAttentionVersion(str, Enum):
    V2 = "v2"
    V3 = "v3"


class AttnImplementation(str, Enum):
    EAGER = "eager"
    SDPA = "sdpa"
    FLASH_ATTENTION_2 = "flash_attention_2"


class GradientCheckpointingMode(str, Enum):
    FULL = "full"
    UNSLOTH = "unsloth"
    SELECTIVE = "selective"


class VllmMode(str, Enum):
    COLOCATE = "colocate"
    SPMD = "spmd"


class SaveStrategy(str, Enum):
    STEPS = "steps"
    EPOCH = "epoch"
    NO = "no"


class FrameworkBackend(str, Enum):
    TRL = "trl"
    UNSLOTH = "unsloth"
    AXOLOTL = "axolotl"
    TORCHTUNE = "torchtune"
    VERL = "verl"
    OPENRLHF = "openrlhf"
    LLAMAFACTORY = "llamafactory"
    NEMO = "nemo"
    FROM_SCRATCH = "from_scratch"


class FSDPShardingStrategy(str, Enum):
    FULL_SHARD = "full_shard"
    SHARD_GRAD_OP = "shard_grad_op"
    NO_SHARD = "no_shard"
    HYBRID_SHARD = "hybrid_shard"


class FSDPAutoWrapPolicy(str, Enum):
    TRANSFORMER_BASED = "transformer_based"
    SIZE_BASED = "size_based"


class FSDPMixedPrecision(str, Enum):
    NONE = "none"
    BF16 = "bf16"
    FP16 = "fp16"


class FSDPBackwardPrefetch(str, Enum):
    BACKWARD_PRE = "backward_pre"
    BACKWARD_POST = "backward_post"


class RemoteBackend(str, Enum):
    SSH = "ssh"
    SLURM = "slurm"


# ─── Mapping technique → stage ───

TECHNIQUE_STAGE_MAP: dict[Technique, Stage] = {
    Technique.SFT: Stage.SFT,
    Technique.DPO: Stage.PREFERENCE,
    Technique.SIMPO: Stage.PREFERENCE,
    Technique.KTO: Stage.PREFERENCE,
    Technique.ORPO: Stage.PREFERENCE,
    Technique.PPO: Stage.RL,
    Technique.GRPO: Stage.RL,
    Technique.DAPO: Stage.RL,
    Technique.VAPO: Stage.RL,
    Technique.RLOO: Stage.RL,
    Technique.REINFORCE_PP: Stage.RL,
    Technique.DR_GRPO: Stage.RL,
    Technique.FLOWRL: Stage.RL,
    Technique.PRIME: Stage.RL,
    # Distillation (SFT-like except SDPO which is RL)
    Technique.GKD: Stage.SFT,
    Technique.SDFT: Stage.SFT,
    Technique.SDPO: Stage.RL,
    Technique.GOLD: Stage.SFT,
    # Reward modeling
    Technique.REWARD_MODELING: Stage.PREFERENCE,
}

# Techniques that do NOT require a reference model
REFERENCE_FREE_TECHNIQUES = {
    Technique.SFT, Technique.SIMPO, Technique.ORPO, Technique.KTO,
    Technique.GKD, Technique.SDFT, Technique.GOLD, Technique.SDPO,
    Technique.REWARD_MODELING,
}


# ─── Sub-models ───


class ExperimentConfig(BaseModel):
    name: str = Field(..., min_length=1, description="Unique experiment name")
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    seed: int = 42
    run_id: str | None = None


class ModelConfig(BaseModel):
    name_or_path: str = Field(..., min_length=1, description="HuggingFace model ID or local path")
    revision: str = "main"
    tokenizer_name_or_path: str | None = None
    trust_remote_code: bool = False
    attn_implementation: AttnImplementation | None = AttnImplementation.FLASH_ATTENTION_2
    chat_template: str | None = None
    max_seq_length: int = Field(2048, gt=0)
    vocab_size: int | None = None


class PeftConfig(BaseModel):
    method: PeftMethod = PeftMethod.NONE
    r: int = Field(16, gt=0, description="LoRA rank")
    lora_alpha: int = Field(32, gt=0, description="LoRA scaling factor")
    lora_dropout: float = Field(0.05, ge=0.0, le=1.0)
    target_modules: list[str] = Field(
        default_factory=lambda: ["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    bias: str = "none"
    task_type: str = "CAUSAL_LM"
    use_dora: bool = False
    use_rslora: bool = False
    modules_to_save: list[str] | None = None

    @model_validator(mode="after")
    def validate_peft_options(self) -> PeftConfig:
        if self.method == PeftMethod.DORA:
            self.use_dora = True
        if self.method == PeftMethod.RSLORA:
            self.use_rslora = True
        return self


class PrecisionConfig(BaseModel):
    compute_dtype: ComputeDtype = ComputeDtype.BF16
    quantization: Quantization = Quantization.NONE
    double_quantization: bool = True
    quantization_type: str = "nf4"

    @model_validator(mode="after")
    def validate_quantization(self) -> PrecisionConfig:
        if self.quantization == Quantization.NONE:
            self.double_quantization = False
        return self


class TrainingConfig(BaseModel):
    stage: Stage = Stage.RL
    technique: Technique = Technique.GRPO
    peft: PeftConfig = Field(default_factory=PeftConfig)
    precision: PrecisionConfig = Field(default_factory=PrecisionConfig)
    technique_args: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_stage_technique(self) -> TrainingConfig:
        expected_stage = TECHNIQUE_STAGE_MAP.get(self.technique)
        if expected_stage is not None:
            self.stage = expected_stage
        return self


class PrepareConfig(BaseModel):
    """Configuration for the data preparation step (prepare.py)."""
    cache_dir: str = Field("./data_cache", description="Directory for cached preprocessed data")
    num_proc: int = Field(4, gt=0, description="Number of parallel workers for preprocessing")


class DatasetConfig(BaseModel):
    train_uri: str = Field(..., min_length=1, description="HF dataset ID, local path, or URL")
    eval_uri: str | None = None
    subset: str | None = None
    split_train: str = "train"
    split_eval: str = "test"
    format: DatasetFormat = DatasetFormat.CHAT
    text_field: str | None = None
    prompt_field: str = "prompt"
    chosen_field: str = "chosen"
    rejected_field: str = "rejected"
    label_field: str | None = None
    max_samples: int | None = Field(None, gt=0)
    preprocessing: str | None = None
    prepare: PrepareConfig = Field(default_factory=PrepareConfig)


class RewardFunctionConfig(BaseModel):
    name: str
    module_path: str
    weight: float = 1.0
    args: dict[str, Any] = Field(default_factory=dict)


class RewardConfig(BaseModel):
    type: RewardType = RewardType.VERIFIABLE
    functions: list[RewardFunctionConfig] = Field(default_factory=list)
    reward_model: str | None = None


class ReferenceModelConfig(BaseModel):
    enabled: bool = True
    name_or_path: str | None = None
    share_layers: bool = True


class TeacherModelConfig(BaseModel):
    """Configuration for teacher model in distillation techniques (GKD, GOLD)."""

    name_or_path: str | None = None
    tokenizer_name_or_path: str | None = None  # For cross-tokenizer distillation (GOLD)
    init_kwargs: dict[str, Any] = Field(default_factory=dict)


class RemoteConfig(BaseModel):
    enabled: bool = False
    backend: RemoteBackend = RemoteBackend.SSH
    host: str | None = None
    user: str | None = None
    slurm_partition: str | None = None
    slurm_account: str | None = None


class HardwareConfig(BaseModel):
    gpu_type: str = "A100-80GB"
    gpu_count: int = Field(1, gt=0)
    num_nodes: int = Field(1, gt=0)
    cpu_per_gpu: int = Field(8, gt=0)
    memory_per_gpu: int | None = None
    remote: RemoteConfig = Field(default_factory=RemoteConfig)


class FSDPConfig(BaseModel):
    """Configuration for Fully Sharded Data Parallel (FSDP).

    Only relevant for multi-GPU training. When enabled=False (default),
    single-GPU behavior is unchanged.
    """

    enabled: bool = False
    sharding_strategy: FSDPShardingStrategy = FSDPShardingStrategy.FULL_SHARD
    auto_wrap_policy: FSDPAutoWrapPolicy = FSDPAutoWrapPolicy.TRANSFORMER_BASED
    min_num_params: int = Field(1_000_000, gt=0, description="Min params for size-based wrapping")
    cpu_offload: bool = False
    mixed_precision: FSDPMixedPrecision = FSDPMixedPrecision.NONE
    forward_prefetch: bool = True
    backward_prefetch: FSDPBackwardPrefetch = FSDPBackwardPrefetch.BACKWARD_PRE
    sync_module_states: bool = True
    use_orig_params: bool = True
    limit_all_gathers: bool = True
    activation_checkpointing: bool = False


class OptimizationConfig(BaseModel):
    flash_attention: FlashAttentionVersion | None = FlashAttentionVersion.V2
    gradient_checkpointing: bool = True
    gradient_checkpointing_mode: GradientCheckpointingMode = GradientCheckpointingMode.FULL
    sequence_packing: bool = False
    compile_model: bool = False
    fused_optimizers: bool = True
    vllm_rollout: bool = False
    vllm_mode: VllmMode = VllmMode.COLOCATE
    vllm_gpu_memory_utilization: float = Field(0.9, gt=0.0, le=1.0)
    deepspeed_stage: int | None = Field(None, ge=2, le=3)
    fsdp: FSDPConfig = Field(default_factory=FSDPConfig)

    @model_validator(mode="before")
    @classmethod
    def _coerce_fsdp_bool(cls, data: Any) -> Any:
        """Backward compat: convert fsdp: true/false to fsdp: {enabled: true/false}."""
        if isinstance(data, dict) and "fsdp" in data:
            if data["fsdp"] is True:
                data["fsdp"] = {"enabled": True}
            elif data["fsdp"] is False:
                data["fsdp"] = {"enabled": False}
        return data


class FrameworkConfig(BaseModel):
    backend: FrameworkBackend = FrameworkBackend.TRL
    version: str | None = None
    custom_args: dict[str, Any] = Field(default_factory=dict)
    triton_kernels: list[str] = Field(default_factory=list)


class OutputConfig(BaseModel):
    dir: str = "./output"
    logging_steps: int = Field(10, gt=0)
    save_strategy: SaveStrategy = SaveStrategy.STEPS
    save_steps: int = Field(500, gt=0)
    save_total_limit: int = Field(3, gt=0)
    report_to: list[str] = Field(default_factory=lambda: ["tensorboard"])
    wandb_project: str | None = None
    wandb_run_name: str | None = None
    push_to_hub: bool = False
    hub_model_id: str | None = None


# ─── Root Config ───


class EnvelopeConfig(BaseModel):
    """Complete configuration for a fine-tuning setup."""

    experiment: ExperimentConfig
    model: ModelConfig
    training: TrainingConfig = Field(default_factory=TrainingConfig)
    dataset: DatasetConfig
    reward: RewardConfig = Field(default_factory=RewardConfig)
    reference_model: ReferenceModelConfig = Field(default_factory=ReferenceModelConfig)
    teacher_model: TeacherModelConfig = Field(default_factory=TeacherModelConfig)
    hardware: HardwareConfig = Field(default_factory=HardwareConfig)
    optimization: OptimizationConfig = Field(default_factory=OptimizationConfig)
    framework: FrameworkConfig = Field(default_factory=FrameworkConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    hparam_overrides: dict[str, Any] = Field(default_factory=dict, description="Hyperparameter defaults from techniques, can be overridden at runtime via HPARAM_* env vars")

    @model_validator(mode="after")
    def validate_cross_fields(self) -> EnvelopeConfig:
        technique = self.training.technique

        # Auto-disable reference model for reference-free techniques
        if technique in REFERENCE_FREE_TECHNIQUES:
            self.reference_model.enabled = False

        # QLoRA requires NF4 or INT8 quantization
        if self.training.peft.method == PeftMethod.QLORA:
            if self.training.precision.quantization == Quantization.NONE:
                self.training.precision.quantization = Quantization.NF4

        # RL techniques should have reward config
        if self.training.stage == Stage.RL and not self.reward.functions and self.reward.reward_model is None:
            pass  # Allow empty — user may provide reward functions in the setup folder

        # Auto-set FSDP mixed precision to match compute dtype
        if self.optimization.fsdp.enabled and self.optimization.fsdp.mixed_precision == FSDPMixedPrecision.NONE:
            if self.training.precision.compute_dtype == ComputeDtype.BF16:
                self.optimization.fsdp.mixed_precision = FSDPMixedPrecision.BF16
            elif self.training.precision.compute_dtype == ComputeDtype.FP16:
                self.optimization.fsdp.mixed_precision = FSDPMixedPrecision.FP16

        return self


# ─── Recipe/Distribution Metadata ───


class RecipeEntry(BaseModel):
    """Metadata for a single distribution/dataset entry in a recipe."""

    chat_type: str = Field(..., min_length=1, description="Chat conversation type")
    dist_id: str = Field(..., min_length=1, description="Distribution unique identifier")
    dist_name: str = Field(..., min_length=1, description="Human-readable distribution name")
    dist_uri: str = Field(..., min_length=1, description="Path or URI to distribution")
    replica: int = Field(1, ge=1, description="Replication factor (N× oversampling)")
    samples: int = Field(..., gt=0, description="Total number of samples in distribution")
    system_prompt: list[str] | None = Field(None, description="System prompt templates")
    system_prompt_name: list[str] | None = Field(None, description="System prompt names")
    tokens: int = Field(..., gt=0, description="Total token count")
    words: int = Field(..., gt=0, description="Total word count")
    validation_error: str | None = Field(None, description="Validation error if any")


class RecipeConfig(BaseModel):
    """Configuration for recipe/distribution metadata (separate from training setup).

    Maps dataset paths to their metadata entries.

    Note:
        name can be None at parse time (recipe from YAML without 'name' field).
        Use ensure_name(filename) to derive name from filename before persistence.
        Filename format: "my_recipe.yaml" → "my_recipe"
    """
    recipe_id: str | None = Field(None, description="Unique recipe identifier (optional, can be set to name or UUID)")
    name: str | None = Field(None, min_length=1, description="Recipe name (must be unique)")
    description: str | None = Field(None, description="Recipe description")
    scope: str | None = Field(None, description="Scope for this recipe (e.g., 'sft', 'preference', 'rl')")
    tags: list[str] = Field([], description="Tags for categorizing recipes")
    entries: dict[str, RecipeEntry] = Field(
        ...,
        description="Mapping of dataset paths to distribution metadata"
    )

    @model_validator(mode="after")
    def validate_recipe_name(self) -> RecipeConfig:
        """Validate that name is not empty if provided and follows naming rules."""
        if self.name is not None and not self.name.strip():
            raise ValueError("Recipe name cannot be empty or whitespace")
        # Note: Uniqueness is enforced at DB layer (Neo4j constraint).
        # This validator ensures name is valid before DB checks.
        return self

    def ensure_name(self, filename: str) -> None:
        """Extract recipe name from filename and set if name is currently None.

        Extracts stem (filename without extension) from provided filename.
        Handles edge cases like "recipe.yaml.bak" → "recipe.yaml".

        Args:
            filename: Source filename (e.g., "my_recipe.yaml").

        Raises:
            ValueError: If extracted name is empty or whitespace-only.
        """
        if self.name is not None:
            # Already has a name, don't override
            return

        # Extract stem using pathlib, handling edge cases
        path = Path(filename)
        # Use rsplit to handle cases like "recipe.yaml.bak"
        name_with_extension = path.name
        if "." in name_with_extension:
            # Remove only the last extension
            extracted_name = name_with_extension.rsplit(".", 1)[0]
        else:
            extracted_name = name_with_extension

        # Validate extracted name
        if not extracted_name or not extracted_name.strip():
            raise ValueError(
                f"Recipe name required: provide 'name' field in YAML or upload file with valid filename"
            )

        self.name = extracted_name
