# Config -- Sistema di configurazione

> `envelope/config/`

Il modulo config e' il cuore di Envelope. Definisce lo schema completo di un esperimento di fine-tuning tramite modelli Pydantic v2, gestisce il caricamento da YAML con merge dei default, e implementa validazione cross-field.

## File

| File | Responsabilita' |
|------|----------------|
| `models.py` | Schema Pydantic v2: tutti gli enum, i sub-model, e il `EnvelopeConfig` root |
| `defaults.py` | Valori default per tecnica (`TECHNIQUE_DEFAULTS`) e iperparametri (`HYPERPARAMETER_DEFAULTS`) |
| `loader.py` | Caricamento YAML, merge dei default, creazione `EnvelopeConfig` |
| `validators.py` | Validazione cross-field (PEFT+quantizzazione, hardware+precisione, RL+reward, etc.) |

## Schema: `models.py`

### Enum

Il file definisce 13 enum che tipizzano ogni campo di configurazione:

| Enum | Valori | Uso |
|------|--------|-----|
| `Stage` | `SFT=1`, `PREFERENCE=2`, `RL=3`, `DISTILLATION=4` | Stage del pipeline post-training |
| `Technique` | 19 valori (`sft`, `dpo`, `simpo`, ..., `prime`, `gkd`, `sdft`, `sdpo`, `gold`, `reward_modeling`) | Tecnica di training |
| `PeftMethod` | `none`, `lora`, `qlora`, `dora`, `rslora` | Metodo PEFT |
| `ComputeDtype` | `fp16`, `bf16`, `fp32` | Precisione di calcolo |
| `Quantization` | `none`, `nf4`, `int8`, `gptq`, `awq`, `fp8` | Tipo di quantizzazione |
| `DatasetFormat` | `chat`, `instruction`, `preference`, `rl` | Formato del dataset |
| `RewardType` | `verifiable`, `learned`, `custom`, `combined` | Tipo di reward |
| `FlashAttentionVersion` | `v2`, `v3` | Versione flash attention |
| `AttnImplementation` | `eager`, `sdpa`, `flash_attention_2` | Implementazione attention |
| `GradientCheckpointingMode` | `full`, `unsloth`, `selective` | Modalita' gradient checkpointing |
| `VllmMode` | `colocate`, `spmd` | Modalita' vLLM per rollout |
| `SaveStrategy` | `steps`, `epoch`, `no` | Strategia di salvataggio |
| `FrameworkBackend` | `trl`, `unsloth`, `axolotl`, `torchtune`, `verl`, `openrlhf`, `llamafactory`, `nemo` | Framework backend |

### Mapping fondamentali

```python
# Ogni tecnica mappa a uno stage
TECHNIQUE_STAGE_MAP: dict[Technique, Stage] = {
    Technique.SFT: Stage.SFT,
    Technique.DPO: Stage.PREFERENCE,
    Technique.GRPO: Stage.RL,
    # ... etc.
}

# Tecniche che NON richiedono un modello di riferimento
REFERENCE_FREE_TECHNIQUES = {Technique.SFT, Technique.SIMPO, Technique.ORPO, Technique.KTO}
```

### Sub-model

Il `EnvelopeConfig` e' composto da 12 sub-model indipendenti:

| Model | Campi principali |
|-------|-----------------|
| `ExperimentConfig` | `name`, `description`, `tags`, `seed`, `run_id` |
| `ModelConfig` | `name_or_path`, `revision`, `tokenizer_name_or_path`, `trust_remote_code`, `attn_implementation`, `chat_template`, `max_seq_length` |
| `PeftConfig` | `method`, `r`, `lora_alpha`, `lora_dropout`, `target_modules`, `bias`, `use_dora`, `use_rslora`, `modules_to_save` |
| `PrecisionConfig` | `compute_dtype`, `quantization`, `double_quantization`, `quantization_type` |
| `TrainingConfig` | `stage` (auto), `technique`, `peft`, `precision`, `technique_args` |
| `PrepareConfig` | `cache_dir` (default `./data_cache`), `num_proc` (default 4) |
| `DatasetConfig` | `train_uri`, `eval_uri`, `subset`, `split_train`, `format`, `prompt_field`, `chosen_field`, `rejected_field`, `label_field`, `max_samples`, `prepare: PrepareConfig` |
| `RewardConfig` | `type`, `functions` (lista di `RewardFunctionConfig`), `reward_model` |
| `HardwareConfig` | `gpu_type`, `gpu_count`, `num_nodes`, `cpu_per_gpu`, `remote` (`RemoteConfig`) |
| `OptimizationConfig` | `flash_attention`, `gradient_checkpointing`, `sequence_packing`, `compile_model`, `fused_optimizers`, `vllm_rollout`, `vllm_mode`, `deepspeed_stage`, `fsdp` |
| `OutputConfig` | `dir`, `logging_steps`, `save_strategy`, `save_steps`, `report_to`, `wandb_project`, `push_to_hub` |
| `TeacherModelConfig` | `name_or_path`, `tokenizer_name_or_path`, `init_kwargs` -- configurazione del modello teacher per tecniche di distillazione (GKD, GOLD) |

### Validatori Pydantic

I model_validator agiscono automaticamente alla creazione:

1. **`PeftConfig.validate_peft_options`**: Se `method=dora`, setta `use_dora=True`; se `method=rslora`, setta `use_rslora=True`
2. **`PrecisionConfig.validate_quantization`**: Se `quantization=none`, disabilita `double_quantization`
3. **`TrainingConfig.validate_stage_technique`**: Setta automaticamente lo `stage` dalla `technique` usando `TECHNIQUE_STAGE_MAP`
4. **`EnvelopeConfig.validate_cross_fields`**: Disabilita il reference model per tecniche reference-free; auto-setta NF4 per QLoRA senza quantizzazione
5. **`EnvelopeConfig._validate_teacher_model`**: Verifica che `teacher_model` sia presente per le tecniche che lo richiedono (GKD, GOLD); emette warning se specificato per tecniche che non lo usano

## Default: `defaults.py`

### `HYPERPARAMETER_DEFAULTS`

Valori che vengono iniettati nel `train.py` generato come fallback quando non vengono specificati override tramite variabili d'ambiente:

```python
{
    "learning_rate": 1e-5,
    "per_device_train_batch_size": 2,
    "warmup_ratio": 0.1,
    "weight_decay": 0.01,
    "num_train_epochs": 3,
    "gradient_accumulation_steps": 4,
    "lr_scheduler_type": "cosine",
    "max_grad_norm": 1.0,
}
```

### `TECHNIQUE_DEFAULTS`

Default specifici per ogni tecnica. Usati dal loader per pre-popolare `technique_args` quando l'utente non li specifica:

- **GRPO**: `num_generations=16`, `max_completion_length=512`, `epsilon=0.2`, `beta=0.04`, `temperature=1.0`
- **DAPO**: come GRPO + `epsilon_low/high`, `dynamic_sampling`, `overlong_filtering`, `token_level_pg`
- **DPO**: `beta=0.1`, `dpo_variant="standard"`
- **SimPO**: `beta=2.0`, `gamma=1.0`
- **KTO**: `lambda_w=1.0`, `lambda_l=1.33`
- ... (vedi `defaults.py` per la lista completa di tutte le 19 tecniche)

## Loader: `loader.py`

La pipeline di caricamento e':

```
load_yaml(path) ─── Parse YAML grezzo
       │
merge_technique_defaults(data) ─── Merge default tecnica in technique_args
       │
inject_hparam_defaults(data) ─── Aggiunge _hparam_defaults
       │
EnvelopeConfig.model_validate(raw) ─── Pydantic validation
       │
config._hparam_defaults = ... ─── Attach extra per il generatore
```

### Funzioni

- **`load_yaml(path)`**: Carica un file `.yaml`/`.yml`, verifica che esista e non sia vuoto
- **`merge_technique_defaults(data)`**: Unisce `TECHNIQUE_DEFAULTS[technique]` con i `technique_args` gia' presenti (i valori dell'utente hanno priorita')
- **`inject_hparam_defaults(data)`**: Aggiunge `_hparam_defaults` al dizionario per il template
- **`load_config(path)`**: Pipeline completa, ritorna un `EnvelopeConfig` validato
- **`dump_config(config, path)`**: Serializza un `EnvelopeConfig` in YAML (usato per il `config.yaml` frozen nel setup)

## Validators: `validators.py`

Sei validatori cross-field che controllano vincoli tra sezioni diverse della config:

### `_validate_peft_quantization`
- QLoRA richiede quantizzazione (nf4 o int8)
- Quantizzazione nf4/int8 senza PEFT e' anomala (warning)
- GPTQ/AWQ senza PEFT e' ok (quantizzazione inference-time)

### `_validate_hardware_precision`
- BF16 richiede GPU Ampere+ (compute capability >= 8.0): A100, H100, L40S, RTX4090
- FP8 richiede GPU Hopper: H100, H200
- GPU pre-Ampere (V100, T4) supportano solo FP16/FP32

### `_validate_rl_requirements`
- Tecniche RL (stage=3) richiedono almeno una `reward.functions` o un `reward.reward_model`
- SFT e preference sono esenti

### `_validate_preference_dataset`
- DPO, SimPO, ORPO richiedono `chosen_field` e `rejected_field` nel dataset
- Altre tecniche non hanno questo vincolo

### `_validate_framework_technique`
- DAPO, VAPO, FlowRL: solo veRL
- Unsloth: non supporta PPO, RLOO, REINFORCE++, Dr.GRPO
- Questo e' un controllo veloce; la matrice completa e' in `capability_matrix.py`

### `_validate_teacher_model`
- Tecniche GKD e GOLD richiedono `teacher_model.name_or_path`
- SDFT e SDPO non richiedono teacher model (self-distilled)
- Se `teacher_model` e' specificato per una tecnica non di distillazione, emette warning

### `ConfigValidationError`

Eccezione custom che raggruppa tutti gli errori:

```python
class ConfigValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
```

Usata da `validate_config_or_raise()` che lancia l'eccezione se ci sono errori, altrimenti passa silenziosamente.
