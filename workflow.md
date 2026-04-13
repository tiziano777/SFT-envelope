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
git clone <url> FineTuning-Envelope
cd FineTuning-Envelope

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

---

## FASE 16 — Iniezione Worker Middleware (step 16 nella generazione setup)

Durante la generazione del setup (FASE 4), dopo il rendering dei template, viene eseguito il **passo 16: inject_worker_middleware()** che copia i moduli worker daemon e le utility condivise dal progetto envelope nel setup generato.

### Cosa fa

La funzione `inject_worker_middleware()` copia il contenuto della directory `envelope/middleware/` in tre sotto-componenti all'interno del setup generato:

1. **worker/daemon.py** — Worker daemon per handshake e push asincrone
2. **shared/models.py** — Modelli per WorkerState, TransferLogEntry, ConnectionModels
3. **shared/state.py** — Gestione atomica dello stato locale

Inoltre, aggiorna automaticamente `requirements.txt` con tre dipendenze critiche:
- **watchdog** — Per osservare i file system (lineage/to_transfer/, training_metrics/)
- **httpx** — Client HTTP asincrono per comunicazione Master
- **paramiko** — SSH per connessioni remote (per future estensioni)

### Perche'

Ogni setup generato deve essere autocontenuto: contiene tutto il necessario per lanciare un training senza dipendere da installazioni globali. Il worker daemon e le utility condivise sono fondamentali per il tracciamento della lineage (Phase 6-7), quindi vengono iniettate automaticamente nel setup.

### Struttura generata

```
envelope/middleware/
├── shared/
│   ├── models.py      (WorkerState, TransferLogEntry, ConnectionModels)
│   └── __init__.py
└── worker/
    ├── daemon.py      (WorkerDaemon class)
    ├── connection.py  (BaseConnection, HTTPConnection, SSHConnection)
    ├── pusher.py      (AsyncPusher, queue + retry)
    └── __init__.py

↓ inject_worker_middleware() ↓

setup_myexp/
├── worker/
│   ├── daemon.py      (copia di envelope/middleware/worker/daemon.py)
│   ├── connection.py  (copia di envelope/middleware/worker/connection.py)
│   ├── pusher.py      (copia di envelope/middleware/worker/pusher.py)
│   └── __init__.py
├── shared/
│   ├── models.py      (copia di envelope/middleware/shared/models.py)
│   ├── state.py
│   └── __init__.py
├── prepare.py
├── train.py
├── run.sh
├── requirements.txt   (+ watchdog, httpx, paramiko aggiunti)
└── config.yaml
```

### Idempotenza

Il passo 16 è idempotente: utilizza `os.path.exists()` per verificare prima di copiare. Se il setup è già stato generato e le directory worker/ e shared/ esistono, il passo salta la copia. Questo rende sicuro rigenerare lo stesso setup senza corrompere i file.

### Link con run.sh

Il file `run.sh` generato (da template `run.sh.j2`) usa questi moduli iniettati:
- Avvia il worker daemon in background: `python -m worker.daemon`
- Attende la comunicazione col Master via handshake
- Durante il training, il daemon osserva i checkpoint scritti e li invia al Master

Vedi **Worker Daemon Lifecycle** (sezione seguente) per dettagli sul flusso di esecuzione.

### Worker Daemon Lifecycle in Generated run.sh

Il file `run.sh` generato (da template `run.sh.j2`) orchestrates the complete lifecycle of the worker daemon and training process. Ecco le 5 fasi in sequenza:

**1. Daemon Bootstrap (linee 1-15)**

```bash
# Source shared environment
source .env 2>/dev/null || true

# Check if daemon already running (prevent double-start)
if [ -f ".daemon.pid" ] && kill -0 $(cat .daemon.pid) 2>/dev/null; then
    echo "✓ Daemon already running (PID: $(cat .daemon.pid))"
else
    # Start worker daemon in background
    python -m worker.daemon &
    DAEMON_PID=$!
    echo $DAEMON_PID > .daemon.pid
    echo "✓ Started daemon (PID: $DAEMON_PID)"
fi
```

**2. Handshake Wait (linee 16-25)**

Dopo l'avvio del daemon, il run.sh attende il completamento della comunicazione col Master. Questo avviene via loop sul marker file `.handshake_done`:

```bash
# Loop con 30-second timeout (configurable via HANDSHAKE_TIMEOUT)
HANDSHAKE_TIMEOUT=${HANDSHAKE_TIMEOUT:-30}
ELAPSED=0

while [ $ELAPSED -lt $HANDSHAKE_TIMEOUT ]; do
    if [ -f ".handshake_done" ]; then
        EXP_ID=$(cat .exp_id)
        echo "✓ Handshake complete. Experiment: $EXP_ID"
        break
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

if [ ! -f ".handshake_done" ]; then
    echo "⚠ Handshake timeout. Running in degraded mode (no lineage sync)"
fi
```

**Cosa accade durante handshake:**
- Il daemon contatta il Master API all'indirizzo `$MASTER_API_URL` (default: http://localhost:8000)
- Invia un POST /handshake con config_hash, code_hash, req_hash
- Master risponde con una strategia (NEW, RESUME, BRANCH, RETRY) e un experiment_id unico
- Il daemon salva experiment_id in `.exp_id` e crea il marker `.handshake_done`
- Se il Master è irraggiungibile o timeout scade, il training continua in "degraded mode" (nessuna lineage)

**3. Training Loop (linee 26-40)**

Una volta che il handshake è completato (o timeout), il training.py viene eseguito con la configurazione completa:

```bash
# Run user's train.py with all config
python train.py \
    --config config.yaml \
    --output_dir ./outputs \
    --num_train_epochs 3 \
    --learning_rate 2e-4
```

**Durante il training:**
- Il daemon continua a girare in background
- Watchdog monitora le directory critiche:
  - `lineage/to_transfer/` — Checkpoint in attesa di essere inviati
  - `training_metrics/` — Metriche di allenamento
  - `config/rewards/` — Cambiamenti nella configurazione reward
- Il daemon legge i checkpoint e costruisce eventi CheckpointPush
- AsyncPusher invia gli eventi al Master **asincronamente** con retry esponenziale (2s, 4s, 8s, ..., max 5 min)
- Il training.py non è bloccato; procede indipendentemente dal successo del daemon

**4. Training Complete (linee 41-45)**

Quando train.py completa (successo o errore), run.sh segnala al daemon di entrare in "flush mode":

```bash
# train.py exit status (0=success, 1=failure)
TRAIN_EXIT=$?

# Create .training_done marker file
touch .training_done

if [ $TRAIN_EXIT -eq 0 ]; then
    echo "✓ Training completed successfully"
else
    echo "✗ Training failed with exit code $TRAIN_EXIT"
fi
```

**5. Daemon Flush & Cleanup (linee 46-50)**

Il daemon entra in "one-shot mode": dopo aver inviato tutti gli eventi in coda e scritto il transfer_log finale, il daemon esce:

```bash
# Wait for daemon to flush (5 second timeout per flush)
FLUSH_TIMEOUT=5
FLUSH_START=$(date +%s)

while kill -0 $(cat .daemon.pid) 2>/dev/null; do
    FLUSH_ELAPSED=$(($(date +%s) - FLUSH_START))
    if [ $FLUSH_ELAPSED -gt $FLUSH_TIMEOUT ]; then
        echo "⚠ Daemon flush timeout. Killing daemon."
        kill -9 $(cat .daemon.pid) 2>/dev/null || true
        break
    fi
    sleep 0.5
done

# Cleanup (optional; keep for debugging)
rm -f .daemon.pid .handshake_done
```

### Timeline Diagram

```
time →
┌──────────────────────────────────────────────────────────────────┐
│  Phase 1              Phase 2           Phase 3      Phase 4 & 5  │
│  Daemon Bootstrap     Handshake Wait   Training     Flush & Exit  │
│                                                                     │
│ ┌───────────────┐    ┌──────────────┐  ┌─────────┐ ┌────────────┐│
│ │daemon start   │    │check         │  │train.py │ │flush logs  ││
│ │in background  │    │.handshake_   │  │runs     │ │daemon exit ││
│ │save PID       │    │_done marker  │  │         │ │            ││
│ │(max 30s)      │───→│              │→ │daemon   │ │transfer_   ││
│ │               │    │timeout?      │  │watches  │ │log.jsonl ✓ ││
│ │               │    │degraded      │  │async    │ │            ││
│ │               │    │mode if no    │  │push     │ │            ││
│ │               │    │.handshake    │  │backoff  │ │            ││
│ └───────────────┘    │.exp_id ✓     │  │         │ │            ││
│        ↓             └──────────────┘  │         │ └────────────┘│
│  ~1-2 seconds        ~0-30 seconds     │  hours  │    ~5 seconds ││
└──────────────────────────────────────────────────────────────────┘
                                           ↓
                        Worker (GPU) ← HTTP/async → Master (CPU)
                          lineage sync in background
```

### State Files Created

Durante l'esecuzione vengono creati questi file di stato:

| File | Quando | Contenuto | Esempio |
|------|--------|-----------|---------|
| `.daemon.pid` | Daemon bootstrap | Process ID del daemon | `12345` |
| `.exp_id` | Handshake OK | ID esperimento univoco | `e-20260413-001` |
| `.handshake_done` | Handshake OK | Marker file (vuoto) | (exists) |
| `.training_done` | Training completo | Marker file (vuoto) | (exists) |
| `.worker_state.json` | Runtime | Stato atomico del daemon | `{status: "training", ...}` |
| `transfer_log.jsonl` | Runtime | Audit trail di tutti gli eventi | Una riga per evento |

### Degraded Mode (Master Unavailable)

Se il Master è irraggiungibile durante la handshake (timeout di 30s), il setup continua in "degraded mode":
- Training procede normalmente
- Nessun experiment_id assegnato
- Il daemon continua a girare, tentando di riconnessione con backoff esponenziale
- Al successivo lancio, se il Master è back online, il daemon prova di nuovo il handshake
- I checkpoint rimangono in `lineage/to_transfer/` fino a quando il handshake ha successo

---

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
