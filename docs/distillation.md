# Tecniche di Distillazione

> `envelope/techniques/distillation/`

Quattro tecniche di distillazione basate sull'API sperimentale di TRL v1. Permettono di trasferire conoscenza da un modello teacher a uno student, o di usare self-distillation per migliorare il modello senza un teacher esterno.

## Overview

| Tecnica | Stage | Richiede teacher_model | Richiede reward | Import path |
|---------|-------|----------------------|----------------|-------------|
| `gkd` | DISTILLATION | Si' | No | `envelope.techniques.distillation.gkd` |
| `sdft` | DISTILLATION | No (self-distilled) | No | `envelope.techniques.distillation.sdft` |
| `sdpo` | DISTILLATION | No (self-distilled) | Si' | `envelope.techniques.distillation.sdpo` |
| `gold` | DISTILLATION | Si' | No | `envelope.techniques.distillation.gold` |

## Dettaglio per tecnica

### `gkd` -- Generalized Knowledge Distillation

Distillazione generalizzata basata su JSD (Jensen-Shannon Divergence) loss con interpolazione configurabile tra forward e reverse KL. Richiede un modello teacher esplicito.

**Technique args**:
- `jsd_interpolation` (0.5): Peso dell'interpolazione tra forward KL e reverse KL nella JSD loss. `0.0` = pura forward KL, `1.0` = pura reverse KL.
- `temperature` (2.0): Temperatura per il softmax delle distribuzioni teacher e student.
- `max_completion_length` (512): Lunghezza massima delle generazioni.

**Note d'uso**:
- Richiede `teacher_model.name_or_path` nella configurazione.
- Il teacher puo' essere un modello piu' grande della stessa famiglia o un modello di famiglia diversa.
- La JSD loss bilancia esplorazione (forward KL) e mode-seeking (reverse KL).

### `sdft` -- Self-Distilled Fine-Tuning

Self-distillation senza teacher esterno. Il modello usa una copia di se' stesso (prima del training) come riferimento implicito. Supporta `privileged_context`: informazioni aggiuntive disponibili solo durante il training (es. chain-of-thought, spiegazioni) che non saranno disponibili a inference.

**Technique args**:
- `privileged_context` (False): Se True, il dataset deve contenere un campo `context` con informazioni privilegiate.
- `temperature` (1.0): Temperatura per il softmax.
- `alpha_sdft` (0.5): Peso della self-distillation loss rispetto alla SFT loss standard.

**Note d'uso**:
- Non richiede un teacher model esterno -- il modello stesso funge da teacher.
- Utile per raffinare un modello gia' pre-addestrato mantenendo la distribuzione originale.
- Il `privileged_context` e' particolarmente efficace per il training su task di reasoning.

### `sdpo` -- Self-Distilled Preference Optimization

Combina self-distillation con reinforcement learning da preferenze. Il modello usa se' stesso come riferimento e ottimizza tramite reward functions.

**Technique args**:
- `beta` (0.1): Coefficiente KL penalty (come DPO).
- `temperature` (1.0): Temperatura per il softmax.
- `num_generations` (8): Numero di completamenti generati per prompt.
- `max_completion_length` (512): Lunghezza massima delle generazioni.

**Note d'uso**:
- Richiede `reward.functions` nella configurazione (come le tecniche RL).
- Combina i vantaggi della self-distillation (stabilita') con l'ottimizzazione da preferenze (allineamento).
- Efficace come step intermedio tra SFT e full RL.

### `gold` -- Generalized Online Distillation

Distillazione online che supporta cross-tokenizer distillation tramite ULD (Universal Logit Distillation) loss. Permette di distillare da un teacher con tokenizer diverso dallo student.

**Technique args**:
- `temperature` (2.0): Temperatura per il softmax.
- `uld_loss` (True): Usa ULD loss per gestire tokenizer diversi tra teacher e student.
- `max_completion_length` (512): Lunghezza massima delle generazioni.

**Note d'uso**:
- Richiede `teacher_model.name_or_path` nella configurazione.
- La ULD loss mappa le distribuzioni di token tra vocabolari diversi, rendendo possibile la distillazione cross-famiglia (es. Llama teacher -> Qwen student).
- Se teacher e student condividono lo stesso tokenizer, la ULD loss si riduce alla KL divergence standard.

## `TeacherModelConfig`

Sub-model Pydantic che definisce il modello teacher per le tecniche di distillazione:

```python
class TeacherModelConfig(BaseModel):
    name_or_path: str                          # Nome HuggingFace o path locale del teacher
    tokenizer_name_or_path: str | None = None  # Tokenizer (default: stesso del teacher)
    init_kwargs: dict[str, Any] = {}           # Kwargs passati a from_pretrained()
```

Va specificato sotto `teacher_model` nella configurazione YAML:

```yaml
teacher_model:
  name_or_path: "Qwen/Qwen2.5-72B-Instruct"
  tokenizer_name_or_path: null  # usa quello del teacher
  init_kwargs:
    torch_dtype: "bfloat16"
    device_map: "auto"
```

## Esempio di configurazione

Riferimento: `configs/examples/gkd_lora_trl.yaml`

```yaml
experiment:
  name: "gkd-qwen-distill"
  description: "GKD distillation from 72B to 7B"

model:
  name_or_path: "Qwen/Qwen2.5-7B-Instruct"
  max_seq_length: 2048

teacher_model:
  name_or_path: "Qwen/Qwen2.5-72B-Instruct"
  init_kwargs:
    torch_dtype: "bfloat16"
    device_map: "auto"

training:
  technique: "gkd"
  peft:
    method: "lora"
    r: 16
    lora_alpha: 32
  precision:
    compute_dtype: "bf16"
  technique_args:
    jsd_interpolation: 0.5
    temperature: 2.0

dataset:
  train_uri: "HuggingFaceH4/ultrachat_200k"
  format: "chat"

framework:
  backend: "trl"
```

## Compatibilita'

Le tecniche di distillazione sono supportate **esclusivamente** dal framework TRL (`trl>=1.0.0`). Questo e' dovuto alla dipendenza dall'API sperimentale di TRL v1 per i trainer di distillazione (`GKDTrainer`, `SDFTTrainer`, etc.).

| Tecnica | TRL | Unsloth | Axolotl | Torchtune | veRL | OpenRLHF | LlamaFactory | From Scratch |
|---------|-----|---------|---------|-----------|------|----------|-------------|-------------|
| gkd | x | - | - | - | - | - | - | - |
| sdft | x | - | - | - | - | - | - | - |
| sdpo | x | - | - | - | - | - | - | - |
| gold | x | - | - | - | - | - | - | - |
