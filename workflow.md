# Workflow — FineTuning Envelope

Guida step-by-step per generare setup di training: dall'installazione alla generazione e lancio di un esperimento.

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

| Framework | Tipo | Tecniche | Livello |
|-----------|------|----------|--------|
| **TRL** | Single-node | sft, dpo, grpo, ppo, gkd, distillation, reward_modeling | ✅ Completo |
| **Unsloth** | Single-node | sft, dpo, grpo | ✅ Completo |
| **Torchtune** | Single-node | sft, dpo | ✅ Completo |
| **Axolotl** | Single-node | sft, dpo | ✅ Completo |
| **veRL** | Multi-node | grpo, ppo, dapo, vapo | ✅ Completo |
| **OpenRLHF** | Multi-node | sft, dpo, grpo, ppo | ✅ Completo |
| **LlamaFactory** | Multi-node | sft, dpo, kto, orpo | ✅ Completo |
| **From Scratch** | PyTorch raw | tutte le 19 tecniche | ✅ Completo |

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

---

## FASE 3 — Valida il config

```bash
envelope validate --config configs/my_grpo_math.yaml
```

Il sistema verifica:

1. Parsing YAML
2. Merge dei default per la tecnica (es. `grpo` -> `num_generations=16`)
3. Validazione Pydantic v2 (tipi, enum, vincoli di range)
4. Cross-validation:
   - QLoRA richiede quantizzazione? Presente.
   - GPU supporta BF16? Solo se CC >= 8.0.
   - Tecnica RL ha reward? Verifica.
   - Framework supporta la tecnica? Verifica.
5. Suggerimenti hardware (flash attention, gradient checkpointing)

Correggi eventuali errori e ri-valida finche' tutto passa.

---

## FASE 4 — Genera il setup

```bash
envelope setup --name grpo-math-v1 --config configs/my_grpo_math.yaml
# oppure:
make setup NAME=grpo-math-v1 CONFIG=configs/my_grpo_math.yaml
```

Output generato:

```
setups/setup_grpo-math-v1/
├── prepare.py       # Preparazione dataset con caching idempotente
├── train.py           # Script completo, contiene resolve_hparam() per env vars
├── run.sh             # Script di lancio (python / accelerate launch / torchrun)
├── config.yaml        # Config frozen (snapshot immutabile)
├── requirements.txt   # Dipendenze pip
└── rewards/           # (solo per tecniche RL)
    ├── __init__.py
    └── math_verify.py
```

**Importante**: questa directory e' **immutabile**. Non modificare mai i file al suo interno (eccezione: `data_cache/` viene creata a runtime da `prepare.py`).

> **Per coding agents**: `train.py` contiene la funzione `resolve_hparam(name, default)` che legge `HPARAM_{NAME.upper()}` dalle env vars. Questo e' il meccanismo per sovrascrivere gli iperparametri a runtime senza toccare i file.

## FASE 5 — Training singolo (test manuale)

```bash
cd setups/setup_grpo-math-v1
pip install -r requirements.txt
python prepare.py    # Scarica e cachea il dataset in ./data_cache/ (idempotente)
bash run.sh          # train.py importa da prepare.py, non ri-scarica i dati
```

Lo script emette su stdout linee strutturate per tracciare i risultati:

```
EXPERIMENT_STATUS:STARTED
EXPERIMENT_STATUS:TRAINING epoch=1 loss=2.341
EXPERIMENT_RESULT:{"reward_mean": 0.72, "loss": 1.23, "accuracy": 0.85}
EXPERIMENT_STATUS:COMPLETED
```

### Override manuali

Sovrascrivere iperparametri senza modificare alcun file:

```bash
HPARAM_LEARNING_RATE=3e-5 HPARAM_PER_DEVICE_TRAIN_BATCH_SIZE=4 bash run.sh
```

Se va in OOM: riduci `num_generations`, `max_seq_length`, o aggiungi quantizzazione nel config YAML e ri-genera il setup dalla FASE 4.

### Nuovo: hparam_overrides nel YAML

A partire dalla refactoring di aprile 2026, puoi anche specificare overrides direttamente nel YAML config:

```yaml
experiment:
  name: "my-experiment"

# ... altre sezioni ...

# Opzionale: sovrascrivi hyperparameter defaults nel YAML
hparam_overrides:
  learning_rate: 2e-4
  per_device_train_batch_size: 8
  num_epochs: 3
```

Al momento della generazione del setup, questi overrides vengono embeddati in `train.py` come default. Le env vars `HPARAM_*` continuano a sovrascrivere i valori nel config (stesso meccanismo di prima).

**Precedenza** (dal più specifico al più generale):
1. `HPARAM_*` env var → priorità massima
2. `hparam_overrides` nel config YAML
3. Framework defaults (TRL, Unsloth, etc.)
4. Envelope defaults globali

---

## Architettura: Worker-Master Async Pattern

Il pattern Worker-Master define l'architettura complessiva del sistema di lineage tracking. Worker (GPU node) e Master (CPU node) comunicano asincronamente via HTTP per sincronizzare checkpoint, metriche, e cambiamenti di configurazione.

### Spatial and Temporal Separation

```
┌─── GPU NODE (setup_{name}/) ────────────────────────────────────┐
│                                                                    │
│  run.sh (generated from run.sh.j2 template)                      │
│  ├─ Start daemon: python -m worker.daemon                        │
│  ├─ Wait: .handshake_done ← Master /handshake POST              │
│  └─ Run: train.py (independent of daemon health)                 │
│                                                                    │
│  worker/daemon.py (Phase 6)                                      │
│  ├─ [1] Handshake: POST /handshake → exp_id                      │
│  ├─ [2] Watch: lineage/to_transfer/, training_metrics/          │
│  ├─ [3] Queue: CheckpointPush, SyncEvent events                 │
│  └─ [4] Async Push: exponential backoff retry                    │
│                                                                    │
│  Local persistence                                                │
│  ├─ .worker_state.json (atomic state via tmp+rename)            │
│  ├─ transfer_log.jsonl (append-only audit trail)                │
│  └─ .handshake_done, .exp_id (markers)                           │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
                             │
                             │ HTTP/JSON
                             ↓
┌─── MASTER NODE ─────────────────────────────────────────────────┐
│                                                                   │
│  Master API (FastAPI, Phase 4)                                  │
│  ├─ POST /handshake → strategy (NEW/RESUME/BRANCH/RETRY)        │
│  ├─ POST /checkpoint_push → validate & store                    │
│  ├─ POST /status_update → track lifecycle                       │
│  ├─ POST /merge → combine checkpoints                           │
│  └─ POST /sync_event → async event processing                   │
│                                                                   │
│  Master lineage store (Phase 2)                                  │
│  ├─ Neo4j 5.x with 5 UNIQUE constraints                         │
│  ├─ Node types: :Experiment, :Checkpoint, :Recipe, :Model      │
│  ├─ Relations: DERIVED_FROM, RETRY_FROM, MERGED_FROM            │
│  └─ APOC triggers: auto-timestamps, orphan validation            │
│                                                                   │
│  Observability (Phase 3)                                         │
│  ├─ OpenTelemetry SDK                                            │
│  ├─ FastAPI auto-instrumentation                                │
│  └─ Phoenix UI for trace visualization                          │
│                                                                   │
└────────────────────────────────────────────────────────────────────┘

Data Flow:
├─ Worker: train.py writes checkpoint → daemon observes → queues event
├─ Worker: daemon sends HTTP POST /checkpoint_push
├─ Master: FastAPI receives → LineageController validates
├─ Master: creates Neo4j Checkpoint node + relations
├─ Master: returns 200 + checkpoint_id
└─ Worker: daemon logs event to transfer_log.jsonl (audit trail)
```

### Key Design Properties

**Decoupled**: Training proceeds unblocked even if daemon or Master unavailable. No blocking calls during train.py.

**Async**: Checkpoint sync happens in background with exponential backoff retry. Worker doesn't wait for network round-trips.

**Atomic**: Local state persisted via tmp+rename pattern (atomic on POSIX). transfer_log.jsonl is append-only for forensics.

**Traceable**: Every event has event_id, timestamp, source for debugging and replay. Neo4j audit trail immutable.

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

### Makefile shortcuts

| Comando | Descrizione |
|---------|-------------|
| `make setup NAME=X CONFIG=Y` | Genera setup |
| `make validate CONFIG=Y` | Valida config |
| `make test` | Esegui test suite |
| `make lint` | Linting con ruff |
| `make format` | Formattazione con ruff |

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
- **3 example configs**: `examples/qlofa-sft.yaml`, `examples/distillation-gkd.yaml`, `examples/torchtune-sft.yaml`
