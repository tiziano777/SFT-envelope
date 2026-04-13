# Generator -- Generazione setup e template Jinja2

> `envelope/generators/`

Il modulo generator e' l'orchestratore principale di Envelope. Prende un file YAML di configurazione e produce una directory `setup_{name}/` autocontenuta pronta per il training.

## File

| File | Responsabilita' |
|------|----------------|
| `setup_generator.py` | Orchestratore: load, validate, render, output |
| `templates/prepare.py.j2` | Template per data preparation (tutti i framework) |
| `templates/train_grpo_trl.py.j2` | Template per GRPO + TRL |
| `templates/train_sft_trl.py.j2` | Template per SFT + TRL |
| `templates/run.sh.j2` | Script di lancio |
| `templates/requirements.txt.j2` | Dipendenze pip |
| `templates/train_dpo_trl.py.j2` | Template per DPO + TRL |
| `templates/train_gkd_trl.py.j2` | Template per GKD + TRL |
| `templates/train_sdft_trl.py.j2` | Template per SDFT + TRL |
| `templates/train_sdpo_trl.py.j2` | Template per SDPO + TRL |
| `templates/train_gold_trl.py.j2` | Template per GOLD + TRL |
| `templates/train_reward_modeling_trl.py.j2` | Template per Reward Modeling + TRL |

## Setup Generator -- `setup_generator.py`

### `generate_setup(config_path, name, output_base, apply_suggestions)`

Pipeline completa in 12 step:

```
1. discover_plugins()          # Registra tutti i plugin
2. load_config(config_path)    # YAML -> EnvelopeConfig
3. validate_config_or_raise()  # Cross-field validation
4. technique_registry.get()    # Resolve tecnica
5. framework_registry.get()    # Resolve framework
6. check_or_raise()            # Compatibilita' tecnica x framework
7. technique.validate_config() # Validazione specifica tecnica
8. framework.validate_config() # Validazione specifica framework
9. suggest_optimizations()     # Suggerimenti HW
10. Jinja2 render train.py     # Template tecnica x framework
10b. Jinja2 render prepare.py  # Template preparazione dati (unico per tutti)
11. Jinja2 render run.sh       # Script di lancio
12. Jinja2 render requirements # Dipendenze pip
13. dump_config()              # config.yaml frozen
14. Copy reward modules        # Se RL con reward functions
15. Copy diagnostics.py        # Modulo diagnostica runtime
```

**Parametri**:
- `config_path`: Percorso al file YAML
- `name`: Nome dell'esperimento (usato nella directory: `setup_{name}`)
- `output_base`: Directory base per gli output (default: `setups`)
- `apply_suggestions`: Se True, applica automaticamente i suggerimenti HW

**Ritorna**: `Path` alla directory generata

### Template fallback

Se un template `train_{technique}_{framework}.py.j2` non esiste, il generatore crea un placeholder:

```python
# Template 'train_dapo_verl.py.j2' not yet implemented.
# This is a placeholder. Add the template to envelope/generators/templates/
raise NotImplementedError('Template train_dapo_verl.py.j2 not found')
```

Questo permette al sistema di funzionare anche con combinazioni per cui il template non e' ancora scritto.

### Copia reward modules

Per tecniche RL con reward functions definite, il generatore:
1. Crea `setup_*/rewards/`
2. Crea `rewards/__init__.py`
3. Copia i moduli sorgente delle reward functions nella directory

## Template Jinja2

### Naming convention

```
train_{technique}_{framework}.py.j2
```

Esempi: `train_grpo_trl.py.j2`, `train_sft_trl.py.j2`

### Contesto disponibile

Ogni template riceve il seguente contesto:

```python
{
    "config": EnvelopeConfig,            # Config completa
    "technique_args": dict,            # Args specifici tecnica
    "hparam_defaults": dict,               # Default iperparametri
    "suggestions": dict,               # Suggerimenti HW
    "technique_plugin": BaseTechnique,  # Istanza del plugin tecnica
    "framework_plugin": BaseFrameworkAdapter,  # Istanza dell'adapter
    "launch_command": str,             # Solo per run.sh.j2
    "requirements": list[str],         # Solo per requirements.txt.j2
}
```

### Template `train_grpo_trl.py.j2`

Il template di riferimento per GRPO + TRL. Struttura del file generato:

```python
#!/usr/bin/env python3
"""Training script generato da FineTuning-Envelope."""

# 1. Imports (torch, transformers, trl, peft, etc.)

# 2. Risoluzione iperparametri
#    Legge HPARAM_* da env vars, con fallback ai default
def resolve_hparam(name, default, dtype=float):
    env_key = f"HPARAM_{name.upper()}"
    val = os.environ.get(env_key)
    if val is not None:
        return dtype(val)
    return default

learning_rate = resolve_hparam("learning_rate", {{ hparam_defaults.learning_rate }})
batch_size = resolve_hparam("per_device_train_batch_size", {{ hparam_defaults.per_device_train_batch_size }}, int)
# ... etc.

# 3. Structured output emission
print("EXPERIMENT_STATUS:STARTED")

# 4. Model loading (con PEFT/quantizzazione se configurato)

# 5. Dataset loading

# 6. Reward functions (se RL)

# 7. Trainer configuration (GRPOTrainer / SFTTrainer / etc.)

# 8. Training loop

# 9. Risultati strutturati
print(f"EXPERIMENT_RESULT:{{json.dumps(metrics)}}")
print("EXPERIMENT_STATUS:COMPLETED")
```

### Template `run.sh.j2`

```bash
#!/bin/bash
set -euo pipefail

# Activate environment
source .venv/bin/activate 2>/dev/null || true

# Launch training
{{ launch_command }}
```

Il `launch_command` viene dal framework adapter (es. `python train.py`, `accelerate launch ...`, etc.).

### Template `requirements.txt.j2`

```
{% for req in requirements %}
{{ req }}
{% endfor %}
```

## Output generato

Una directory `setup_{name}/` contiene:

```
setup_grpo-math-v1/
├── prepare.py       # Preparazione dataset con caching idempotente
├── train.py           # Script di training completo
├── diagnostics.py     # Modulo diagnostica runtime (vedi docs/diagnostics.md)
├── run.sh             # Script di lancio (chmod +x)
├── config.yaml        # Config frozen (tutto l'input)
├── requirements.txt   # Dipendenze pip
└── rewards/           # (solo per RL con reward functions)
    ├── __init__.py
    └── math_verify.py # Copiato dal sorgente
```

A runtime, `prepare.py` crea una directory `data_cache/` per il caching idempotente dei dataset preprocessati.

### Worker Middleware Injection (Step 16)

**Fase 7** (Generator Integration) aggiunge un passo cruciale alla pipeline di generazione: **step 16 — Worker Middleware Injection**.

Questo passo esegue la funzione `inject_worker_middleware(setup_dir)` dopo il rendering di tutti i template. Il suo compito:

1. **Copia i moduli worker dal progetto envelope** nel setup generato:
   - `envelope/middleware/worker/` → `setup_{name}/worker/`
   - `envelope/middleware/shared/` → `setup_{name}/shared/`

2. **Aggiorna requirements.txt** aggiungendo tre dipendenze critiche:
   - `watchdog` — Monitora filesystem (lineage/to_transfer/, training_metrics/)
   - `httpx` — Client HTTP asincrono per comunicazione Master
   - `paramiko` — SSH per connessioni remote (future)

#### Codice di referenza

La funzione `inject_worker_middleware()` in `setup_generator.py`:

```python
def inject_worker_middleware(setup_dir: Path) -> None:
    """Copy envelope/middleware/ to setup_{name}/.

    Creates:
    - setup/{name}/worker/ (daemon, connection, pusher)
    - setup/{name}/shared/ (state models, connection models)
    - Updates requirements.txt with watchdog, httpx, paramiko

    Idempotent: safe to re-run.
    """
    middleware_src = Path(__file__).parent.parent / "middleware"

    # Copy worker modules
    worker_src = middleware_src / "worker"
    worker_dst = setup_dir / "worker"
    if not worker_dst.exists():
        shutil.copytree(worker_src, worker_dst)

    # Copy shared models
    shared_src = middleware_src / "shared"
    shared_dst = setup_dir / "shared"
    if not shared_dst.exists():
        shutil.copytree(shared_src, shared_dst)

    # Update requirements.txt
    req_file = setup_dir / "requirements.txt"
    existing = req_file.read_text() if req_file.exists() else ""
    new_reqs = ["watchdog>=4.0", "httpx>=0.27", "paramiko>=3.0"]

    for req in new_reqs:
        if req not in existing:
            existing += f"\n{req}\n"

    req_file.write_text(existing)
```

#### Struttura creata

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

↓ (step 16) inject_worker_middleware() ↓

setup_{name}/
├── worker/            (copia di envelope/middleware/worker/)
│   ├── daemon.py
│   ├── connection.py
│   ├── pusher.py
│   └── __init__.py
├── shared/            (copia di envelope/middleware/shared/)
│   ├── models.py
│   ├── state.py
│   └── __init__.py
├── prepare.py
├── train.py
├── run.sh
├── requirements.txt   (+ watchdog, httpx, paramiko aggiunti)
└── config.yaml
```

#### Perche' serve

Ogni setup generato e' autocontenuto. Include tutto il necessario per lanciare un training senza dipendere da installazioni globali. Il worker daemon e le utility condivise sono fondamentali per:
- **Handshake**: comunicazione iniziale col Master per ottenere experiment_id
- **Checkpoint tracking**: watchdog monitora i checkpoint scritti durante il training
- **Async push**: daemon invia checkpoints al Master in background con retry

#### Idempotenza

Il passo 16 e' **idempotente**:
- Usa `os.path.exists()` prima di copiare
- Se le directory worker/ e shared/ gia' esistono, salta la copia
- Sicuro da eseguire piu' volte sullo stesso setup

#### Uso in run.sh

Il file `run.sh.j2` generato usa i moduli iniettati:

```bash
# Avvia il worker daemon in background
python -m worker.daemon &
DAEMON_PID=$!
echo $DAEMON_PID > .daemon.pid

# Attendi handshake completato
while [ ! -f ".handshake_done" ] && [ $ELAPSED -lt 30 ]; do
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

# Esegui training
python train.py ...
```

Vedi `workflow.md` "FASE 16" per la descrizione completa del daemon lifecycle e della comunicazione Master-Worker.

---

### Proprieta' della directory

- **Autocontenuta**: tutto il necessario per il training e' dentro la cartella
- **Immutabile**: i file non vengono mai modificati dall'esterno (solo override via env vars). Eccezione: `data_cache/` creata da `prepare.py`
- **Riproducibile**: `config.yaml` cattura l'intera configurazione
- **Portatile**: puo' essere copiata su una macchina remota e eseguita

## Come aggiungere un template

1. Crea `envelope/generators/templates/train_{technique}_{framework}.py.j2`
2. Usa il contesto disponibile (vedi sopra)
3. Includi la risoluzione iperparametri con `resolve_hparam()`
4. Includi l'emissione di risultati strutturati (`EXPERIMENT_RESULT:`)
5. Testa con `make setup NAME=test CONFIG=...`

Esempio minimo:

```jinja2
#!/usr/bin/env python3
"""{{ config.experiment.name }} -- {{ config.training.technique.value }} + {{ config.framework.backend.value }}"""
import os, json

def resolve_hparam(name, default, dtype=float):
    val = os.environ.get(f"HPARAM_{name.upper()}")
    return dtype(val) if val is not None else default

lr = resolve_hparam("learning_rate", {{ hparam_defaults.learning_rate }})

print("EXPERIMENT_STATUS:STARTED")
# ... training logic ...
metrics = {"loss": final_loss}
print(f"EXPERIMENT_RESULT:{json.dumps(metrics)}")
print("EXPERIMENT_STATUS:COMPLETED")
```
