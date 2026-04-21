# Workflow — FineTuning Envelope

Guida step-by-step per generare setup di training

Questo documento e' pensato per due tipi di utenti:

- **Programmatori umani** che seguono i passi manualmente
- **Coding agents** (Claude Code, Copilot, Codex) che usano questo file come contesto operativo

**Scenario di esempio**: fine-tuning di **Qwen2.5-7B** con **GRPO + QLoRA** per math reasoning.

---

## Prerequisiti

| Requisito | Versione minima | Verifica |
|-----------|----------------|----------|
| Python | 3.10+ | `python --version` |
| uv | 0.1+ | `uv --version` |
| GPU NVIDIA | CC >= 7.0 | `nvidia-smi` |
| CUDA toolkit | 11.8+ | `nvcc --version` |

---

## FASE 0 — Installazione (una tantum)

```bash
# 1. Clona il repo
cd ~/repo
git clone <url> envelope
cd envelope

# 2. Crea e attiva il virtual environment
uv venv --python 3.10 .venv
source .venv/bin/activate

# 3. Installa il progetto in modalita' editable
uv pip install -e ".[dev]"
```

**Verifica**:

```bash
envelope --help
```

---

## FASE 1 — Esplorazione e scelta della tecnica

Prima di scrivere il config, esplora cosa e' disponibile:

```bash
# Quali tecniche esistono?
envelope techniques

# Quali framework supportano GRPO?
envelope compatible grpo
# Output atteso: trl, unsloth, verl, openrlhf
```

**Decisione**: scegli la tecnica (`grpo`) e il framework backend (`trl`).

> **Per coding agents**: le 19 tecniche sono elencate in `docs/techniques.md`.
> La compatibility matrix si trova in `envelope/frameworks/capability_matrix.py`.

---

## FASE 2 — Scrivi il file YAML di configurazione

Copia un esempio e personalizzalo:

```bash
cp configs/examples/grpo_qlora_qwen.yaml configs/my_grpo_math.yaml
```

Le sezioni principali del YAML sono:

| Sezione | Cosa definisce | Esempio |
|---------|---------------|---------|
| `experiment` | Nome, descrizione, tags | `name: "grpo-qlora-qwen-math"` |
| `model` | LLM (path HuggingFace), `max_seq_length` | `name_or_path: "Qwen/Qwen2.5-7B-Instruct"` |
| `training.technique` | Tecnica di training | `technique: "grpo"` |
| `training.peft` | Metodo PEFT, rank, target modules | `method: "qlora"`, `r: 32` |
| `training.precision` | Dtype, quantizzazione | `compute_dtype: "bf16"`, `quantization: "nf4"` |
| `training.technique_args` | Parametri tecnica-specifici | `num_generations: 16`, `epsilon: 0.2` |
| `dataset` | URI dataset HuggingFace, formato | `train_uri: "argilla/magpie-ultra-v1.0"` |
| `reward` | Tipo reward, funzioni/modello | `type: "verifiable"` |
| `hardware` | GPU type, count | `gpu_type: "A100-80GB"`, `gpu_count: 1` |
| `framework` | Backend scelto | `backend: "trl"` |

**Esempio completo** (GRPO + QLoRA su Qwen):

```yaml
experiment:
  name: "grpo-qlora-qwen-math"
  description: "GRPO with QLoRA on Qwen2.5-7B"
  tags: ["grpo", "qlora", "math"]

model:
  name_or_path: "Qwen/Qwen2.5-7B-Instruct"
  trust_remote_code: true
  max_seq_length: 2048

training:
  technique: "grpo"
  peft:
    method: "qlora"
    r: 32
    lora_alpha: 64
    target_modules: ["q_proj", "k_proj", "v_proj", "o_proj"]
  precision:
    compute_dtype: "bf16"
    quantization: "nf4"
  technique_args:
    num_generations: 16
    max_completion_length: 512
    epsilon: 0.2
    beta: 0.04

dataset:
  train_uri: "argilla/magpie-ultra-v1.0"
  format: "rl"

reward:
  type: "verifiable"
  functions:
    - name: "math_correctness"
      module_path: "rewards.math_verify"
      weight: 1.0

hardware:
  gpu_type: "A100-80GB"
  gpu_count: 1

framework:
  backend: "trl"
```

### Multi-GPU con FSDP

Per piu' GPU, aggiungi `optimization.fsdp`:

```yaml
hardware:
  gpu_type: "A100-80GB"
  gpu_count: 4

optimization:
  fsdp:
    enabled: true
    sharding_strategy: "full_shard"   # full_shard (ZeRO-3) | shard_grad_op (ZeRO-2)
    mixed_precision: "bf16"
```

| Scenario | Strategia FSDP |
|----------|---------------|
| 1 GPU | Non abilitare |
| Multi-GPU, modello entra in VRAM | `shard_grad_op` (ZeRO-2) |
| Multi-GPU, modello non entra | `full_shard` (ZeRO-3) |
| Multi-nodo | `full_shard` + `num_nodes > 1` |

> Vincoli: FSDP supportato da TRL, Axolotl, LlamaFactory, From Scratch. Non compatibile con Unsloth (single-GPU only) e OpenRLHF (usa DeepSpeed). Torchtune e veRL gestiscono FSDP internamente.

### Framework Support Matrix

Tutti gli 8 framework sono supportati e generano setup funzionanti:

| Framework | Tipo | Tecniche | 
|-----------|------|----------|
| **TRL** | Single-node | sft, dpo, grpo, ppo, gkd, distillation, reward_modeling |
| **Unsloth** | Single-node | sft, dpo, grpo | 
| **Torchtune** | Single-node | sft, dpo | 
| **Axolotl** | Single-node | sft, dpo | 
| **veRL** | Multi-node | grpo, ppo, dapo, vapo | 
| **OpenRLHF** | Multi-node | sft, dpo, grpo, ppo | 
| **LlamaFactory** | Multi-node | sft, dpo, kto, orpo |
| **From Scratch** | PyTorch raw | tutte le 19 tecniche | 

Vedi `docs/frameworks.md` per dettagli su ogni backend.

### 3 Example Configurations

Copia uno dei 3 example configs per iniziare rapidamente:

```bash
# QLoRA + SFT (standard single-GPU setup)
cp examples/qlofa-sft.yaml configs/my_config.yaml

# Distillation con teacher model (GKD)
cp examples/distillation-gkd.yaml configs/my_distill.yaml

# TorchTune backend (nuovo, full YAML config)
cp examples/torchtune-sft.yaml configs/my_torchtune.yaml
```

Ogni esempio è minimale ma completo, pronto per essere adattato.

## FASE 4 — Genera il setup

```bash
envelope setup --name grpo-math-v1 --config configs/my_grpo_math.yaml
# oppure:
make setup NAME=grpo-math-v1 CONFIG=configs/my_grpo_math.yaml
```

Output generato:

```
setups/setup_grpo-math-v1/
├── prepare.py         # Preparazione dataset con caching in .cache/*
├── train.py           # Script completo, legge da .cache/* e da config.yaml
├── merge.py           # [opzionale] script epr fare ckp/model merging
├── config.yaml        # Config file che tocca ogni aspetto del progetto, dagli hyperparameters all'HW
├── requirements.txt   # Dipendenze pip
└── modules/
    ├── rewards/           # (solo per tecniche RL)
    ├  ├── __init__.py
    ├  └── math_verify.py
    └── */
```

## FASE 5 — Training singolo (test manuale)

```bash
cd setups/setup_grpo-math-v1
pip install -r requirements.txt
python prepare.py    # Scarica e cachea il dataset in ./data_cache/ (idempotente)
bash train.py          # train.py importa da prepare.py, non ri-scarica i dati
```

---

## FASE 6 — Itera

In base ai risultati, le opzioni sono:

| Azione | Quando |
|--------|--------|
| **Modificare il config YAML e rigenerare il setup** | I risultati suggeriscono cambi a tecnica, modello, o parametri strutturali |
| **Cambiare tecnica o framework** | La tecnica corrente non converge, o un altro framework offre vantaggi |
| **Scalare le GPU / abilitare FSDP** | Il modello non entra in VRAM, o serve piu' throughput |

---

## Riepilogo comandi

### Comandi CLI

| Comando | Descrizione |
|---------|-------------|
| `envelope techniques` | Lista le 19 tecniche registrate |
| `envelope frameworks` | Lista gli 8 framework backend |
| `envelope compatible TECNICA` | Framework compatibili con una tecnica |
| `envelope validate --config FILE` | Valida un config YAML |
| `envelope setup --name NAME --config FILE` | Genera una directory setup |

---

## Riferimenti Ulteriori

- **Architettura tecnica**: `docs/architecture.md`
- **Schema configurazione**: `docs/config.md`
- **Tecniche di training**: `docs/techniques.md` (19 tecniche documentate)
- **Framework backend**: `docs/frameworks.md` (8 framework, capability matrix)
- **Diagnostica esecuzione**: `docs/diagnostics.md`
- **Ottimizzazioni recenti**: `docs/optimization-notes.md` (refactoring april 2026)
- **FSDP multi-GPU**: `docs/fsdp.md`
- **Training from scratch**: `docs/from-scratch.md`

