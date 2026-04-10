# AI Experiment Lineage System — Architecture & Implementation Guide

> **Documento unificato** per la progettazione, implementazione e integrazione del sistema di tracciamento del lineage di esperimenti AI.
> Ottimizzato per lettura da parte di agenti AI (Claude Code) e pianificazione task-oriented.

---

## Indice

0. [Ottimizzazione Preventiva](#0-ottimizzazione-preventiva)
1. [Visione d'insieme](#1-visione-dinsieme)
2. [Struttura del Progetto](#2-struttura-del-progetto)
3. [Data Model — Neo4j Graph Schema](#3-data-model--neo4j-graph-schema)
4. [Shared Layer — Dataclass e Hashing](#4-shared-layer--dataclass-e-hashing)
5. [Worker Layer — Esecuzione Locale](#5-worker-layer--esecuzione-locale)
6. [Master Layer — Orchestratore Centrale](#6-master-layer--orchestratore-centrale)
7. [Logica di Branching e Casistiche](#7-logica-di-branching-e-casistiche)
8. [Protocollo di Comunicazione](#8-protocollo-di-comunicazione)
9. [Integrazione nel Generator Esistente](#9-integrazione-nel-generator-esistente)
10. [Osservabilità — OpenTelemetry e Phoenix](#10-osservabilità--opentelemetry-e-phoenix)
11. [Infrastruttura e Deployment](#11-infrastruttura-e-deployment)
12. [Testing e Simulazione](#12-testing-e-simulazione)
13. [Criticità e Soluzioni Architetturali](#13-criticità-e-soluzioni-architetturali)
14. [Ordine di Implementazione Consigliato](#14-ordine-di-implementazione-consigliato)

---
## 0. Ottimizzazione Preventiva
Dobbiamo applicare molti cambiamenti su questa codebase, prima di farlo, vorrei che la leggessi e cercassi di capire quali sono i punti critici che possono generare errori, overheads, vincoli troppo stringenti che potrebbero alterarne la flessibilità, estendibilità e modularità dei moduli. Cerca anche di capire quali info sono inutili, per snellire il progetto attuale ove serve, mantenendo comunque la stessa utilità marginale senza compromettere il progetto. Esegui dei test, magari creando nuovi exmples/* e nuovi setups/*. Poi rifletti le eventuali semplificazioni prima su workflow.md e README.md ove necessario, poi nelle docs/*.md ove necessario, e poi in questo file (dal capitolo 1 in poi) unificando il progetto di integrazione sulle nostre nuove fondamenta, cosi da agevolare l'integrazione che stiamo proponendo. Una volta semlificata la codebase e unificato integrazione con questo file, pianifica ed esegui il piano. ricorda che hai a disposizione le skill di claude per otitmizzare contesto, leggere codebases in modo strutturato, e gestire context e altro ancora!

## 1. Visione d'insieme

### 1.1 Contesto

Il progetto **FineTuning-Envelope** è un generatore di scaffold per esperimenti di fine-tuning LLM. Ogni scaffold (`setups/setup_{name}/`) contiene script di training, configurazioni, requisiti e reward functions.

L'obiettivo di questa fase è estendere il sistema con un **layer di tracciamento del lineage** che:

- Registra ogni esperimento, checkpoint e relazione di derivazione in un grafo Neo4j.
- Funziona su macchine fisicamente separate (GPU worker ↔ DB master) con comunicazione asincrona.
- Si integra nel generatore esistente senza rompere nulla: ogni nuovo scaffold includerà automaticamente il middleware Worker.
- Il master crea dei scaffold/setup, che vengono scritti manualmente sul worker (copia fisica sia nel envelope che su GPU worker), il setup è autoconsistente e ha i moduli per comunicare risultati del train al master che scrive tutto nel DB.

### 1.2 Architettura a Due Macchine

```
┌─────────────────────────────────┐        ┌──────────────────────────────────┐
│          WORKER (GPU)           │        │           MASTER (CPU)           │
│                                 │        │                                  │
│  train.py ──→ emette eventi     │        │  FastAPI (master/api/)           │
│  daemon.py ──→ raccoglie eventi │──SSH──▶│  LineageController               │
│  pusher.py ──→ coda asincrona   │  HTTP  │  Neo4j Repository                │
│  lineage/to_transfer/           │        │  Storage Writer (URI astratto)   │
│  lineage/worker_state.json      │        │  Neo4j DB + APOC                 │
└─────────────────────────────────┘        │  Phoenix OTEL Collector          │
                                           └──────────────────────────────────┘
                                                         │
                                           ┌─────────────▼──────────────────┐
                                           │   Phoenix UI (port 6006)        │
                                           │   Osservabilità messaggi        │
                                           │   Master ↔ Worker               │
                                           └────────────────────────────────┘
```

Il Worker non attende il Master: scrive localmente e sincronizza in background. Il protocollo di comunicazione è astratto (SSH in produzione, HTTP per test locali).

Nota: Il worker però deve sapere quello che sta facendo, che esperimento sta eseguendo (exp_id)

---

## 2. Struttura del Progetto

### 2.1 Layout Completo (esistente + nuovo)

```
FineTuning-Envelope/
│
├── envelope/                              # [ESISTENTE] Core del generatore
│   ├── cli.py
│   ├── config/                            # Defaults/Loaders/Models/Validators
│   ├── registry/                          # Plugin system
│   ├── diagnostics/                       # esegue controlli per anomalie di trainign results
│   ├── hardware/                          # HW setup spec
│   ├── rewards/                           # pool of util rewards
│   ├── techniques/                        # 19 plugin tecnica (sft, rl, preference...)
│   ├── frameworks/
│   │   ├── capability_matrix.py           # [MOD] aggiunge entry 'merge'
│   │   └── ...
│   ├── generators/                        # Templates and generator
│   │   ├── setup_generator.py             # [MOD] aggiunge step 16: inject_worker_middleware()
│   │   └── templates/
│   │       ├── run.sh.j2                  # [MOD] aggiunge daemon lifecycle
│   │       ├── requirements.txt.j2        # [MOD] aggiunge watchdog, httpx, paramiko
│   │       └── merge.py.j2                # [NUOVO] template scaffold merge
│   │
│   └── middleware/                        # [NUOVO] sorgente dei moduli copiati negli scaffold
│       ├── shared/
│       │   ├── __init__.py
│       │   ├── dataclasses.py             # Pydantic: tutti i nodi + relazioni + envelope
│       │   └── hashing.py                 # ConfigHasher + ConfigSnapshot
│       └── worker/
│           ├── __init__.py
│           ├── daemon.py                  # Entry point processo separato
│           ├── local_persistence.py       # WorkerState + manifest + snapshot
│           ├── fs_watcher.py              # Watchdog filesystem
│           ├── pusher.py                  # Coda asincrona verso Master
│           └── connection/
│               ├── __init__.py
│               ├── base.py                # ABC BaseConnection
│               ├── http.py                # HTTPConnection (httpx)
│               └── ssh.py                 # SSHConnection (paramiko)
│
├── master/                                # [NUOVO] servizio deployabile indipendente
│   ├── api/
│   │   ├── app.py
│   │   ├── routes.py
│   │   ├── lineage_controller.py
│   │   └── middleware.py                  # X-API-Key auth
│   ├── neo4j/
│   │   ├── client.py                      # Driver singleton
│   │   ├── repository.py                  # Query Cypher atomiche
│   │   ├── schema.cypher
│   │   └── triggers.cypher                # APOC: created_at, updated_at, validation
│   ├── storage/
│   │   ├── base.py                        # ABC BaseStorageWriter
│   │   ├── local.py                       # LocalStorageWriter (file:///)
│   │   ├── resolver.py                    # URIResolver: prefisso → writer
│   │   └── stubs/                         # S3, NFS (stub per ora)
│   ├── observability/                     # [NUOVO] OpenTelemetry + Phoenix
│   │   ├── __init__.py
│   │   └── tracing.py                     # setup_tracing() + get_tracer()
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── .env.example
│
├── setups/setup_{name}/                   # [GENERATO a runtime]
│   ├── prepare.py
│   ├── train.py
│   ├── run.sh                             # [MOD] lancia daemon + train
│   ├── config.yaml
│   ├── requirements.txt
│   ├── rewards/
│   ├── worker/                            # [NUOVO] copiato da middleware/worker/
│   ├── shared/                            # [NUOVO] copiato da middleware/shared/
│   └── lineage/                           # [NUOVO] creato a runtime dal daemon
│       ├── worker_state.json
│       ├── transfer_log.jsonl             # Audit trail append-only
│       ├── .handshake_done                # Flag: daemon → train.py
│       ├── .training_done                 # Flag: train.py → daemon
│       ├── .exp_id                        # Una riga: exp_id corrente
│       ├── snapshots/{snapshot_id}/
│       │   ├── config.yaml
│       │   ├── requirements.txt
│       │   └── manifest.json              # {file: sha256} + aggregated_hash
│       └── to_transfer/{exp_id}/
│           ├── config/
│           ├── sw_requirements/
│           ├── hw_requirements/
│           ├── hw_metrics/
│           ├── training_metrics/          # append-mode
│           ├── rewards/
│           └── checkpoints/
│               ├── {ckp_id}/              # pesi fisici
│               └── results/{ckp_id}/     # solo metriche, senza pesi
│
├── tests/
│    ├── lineage/                         # [NUOVO]
│    └── *                                 # Integration / unit
│
├── configs/examples/*  
├── docs/*
├── workflow.md
├── README.md         
├── Makefile                               # [MOD] target master-*
└── pyproject.toml                         # [MOD] extras opzionali [master]
```

### 2.2 Principio di Modifica Chirurgica

Solo i seguenti file **esistenti** vengono modificati. Tutto il resto è **aggiunta pura**:

| File | Tipo | Cosa cambia |
|------|------|-------------|
| `envelope/generators/setup_generator.py` | Addizione | Step 16: `inject_worker_middleware()` |
| `envelope/generators/templates/run.sh.j2` | Modifica | Blocco daemon lifecycle prima/dopo `launch_command` |
| `envelope/generators/templates/requirements.txt.j2` | Modifica | Aggiunge `watchdog`, `httpx`, `paramiko` |
| `envelope/frameworks/capability_matrix.py` | Addizione | Entry `merge` come tecnica speciale no-GPU |
| `Makefile` | Addizione | Target `master-*` |
| `pyproject.toml` | Addizione | Extra opzionale `[master]` |

---

## 3. Data Model — Neo4j Graph Schema

### 3.1 Nodi

#### `Recipe`
Punto di ingresso di ogni esperimento. Contiene la configurazione dichiarativa.

```python
@dataclass
class RecipeNode:
    recipe_id: str          # UUID
    name: str               # UNIQUE
    description: str
    scope: str              
    tasks: list[str]
    tags: list[str]
    issued: datetime
    modified: datetime
    derived_from: Optional[str]   # UUID auto-riferimento
    config_yaml: str        # config.yaml frozen, recipe conf non deve cambiare mai!
```

Il campo `config_yaml` contiene uno snapshot delle location dei vari datasets:

```yaml
/path/to/dataset/ARC-Challenge/downsampled__0.7__en:
  chat_type: simple_chat_cycle2
  dist_id: ecef45fc-ba10-471d-a8ba-39172cdbf388
  samples: 1603
  tokens: 141889
```

#### `Model`
Modello base su cui eseguire SFT.

| Campo | Tipo | Note |
|-------|------|------|
| `id` | UUID | |
| `model_name` | str | UNIQUE |
| `version` | str | |
| `uri` | str | Path locale o remoto |
| `url` | str | HuggingFace/altro hub |
| `doc_url` | str | |
| `architecture_info_ref` | str | Riferimento a documento architettura |
| `description` | str | |

#### `Experiment`
Istanza di esecuzione. Cuore del tracciamento.

| Campo | Tipo | Note |
|-------|------|------|
| `exp_id` | UUID | |
| `model_id` | UUID | |
| `status` | str | `RUNNING`, `COMPLETED`, `FAILED`, `PAUSED` |
| `exit_status` | Optional[str] | Exit code o descrizione |
| `exit_msg` | Optional[str] | |
| `hash_committed_code` | str | SHA256 di `train.py` + `config.yaml` + tutti i file in `rewards/*` |
| `config` | str | Contenuto testuale di `config.yaml` (snapshot frozen al momento dell'handshake) |
| `train` | str | Contenuto testuale di `train.py` (snapshot frozen al momento dell'handshake) |
| `rewards` | list[str] | Lista dei contenuti testuali di ciascun file in `rewards/*`, nello stesso ordine di `rewards_filenames` |
| `rewards_filenames` | list[str] | Nomi dei file in `rewards/*` corrispondenti a `rewards` (es. `["math_reward.py", "format_reward.py"]`) |
| `requirements` | str | Contenuto testuale di `requirements.txt` (testo semplice) |
| `hyperparams_json` | str | JSON degli iperparametri risolti al momento dell'handshake |
| `scaffold_local_uri` | str | Path scaffold su worker |
| `scaffold_remote_uri` | str | Path scaffold su master/storage |
| `usable` | bool | L'esperimento è considerato valido |
| `manual_save` | bool | Salvato manualmente, non scartare |
| `metrics_uri` | str | Puntatore ai file di training metrics |
| `hw_metrics_uri` | str | Puntatore ai file di hw metrics |
| `description` | str | |
| `created_at` | datetime | Gestito da APOC trigger |
| `updated_at` | datetime | Gestito da APOC trigger |


#### `Checkpoint`
Entità atomica dei pesi. Può avere `uri = NULL` se scartato.

| Campo | Tipo | Note |
|-------|------|------|
| `ckp_id` | UUID | |
| `epoch` | int | |
| `run` | int | Indice della run nell'esperimento |
| `metrics_snapshot` | jsonb | JSON snapshot metriche al momento del salvataggio |
| `uri` | Optional[str] | `NULL` se scartato/perso; use prefix to identify location (optional)`worker://`, `master://`, `s3://` ... |
| `is_usable` | bool | Può essere usato per resume/branch |
| `is_merging` | bool | Partecipa a un'operazione di merge |
| `description` | str | |
| `created_at` | datetime | APOC trigger |
| `updated_at` | datetime | APOC trigger |

#### `Component`
Stack tecnologico: coppia (framework, tecnica SFT). Racchiude implicitamente la matrice di compatibilità.

| Campo | Tipo | Note |
|-------|------|------|
| `technique_code` | str | es. `grpo`, `sft`, `dpo` |
| `framework_code` | str | es. `trl`, `axolotl`, `fsdp` |
| `docs_url` | str | |
| `description` | str | |

### 3.2 Relazioni

```
(Component)  -[:USED_FOR]→     (Experiment)    # Stack tecnologico usato
(Model)      -[:SELECTED_FOR]→ (Experiment)    # Modello base selezionato
(Experiment) -[:BASED_ON]→     (Recipe)        # Configurazione di input
(Experiment) -[:PRODUCED]→     (Checkpoint)    # Checkpoint generato

(Experiment) -[:DERIVED_FROM {diff_patch: JSON}]→ (Experiment)   # Branching logico
(Experiment) -[:STARTED_FROM]→                    (Checkpoint)   # Branching fisico (opz.)
(Experiment) -[:RETRY_OF]→                        (Experiment)   # Stesso setup, nuovo tentativo

(Checkpoint) -[:MERGED_FROM]→  (Checkpoint)    # Merge N-a-1 di pesi
```

#### Proprietà della relazione `DERIVED_FROM`

Il campo `diff_patch` contiene il diff git-style completo tra i file dell'experiment precedente e quello nuovo.

| Campo | Tipo |
|-------|------|
| `config` | list[json] | 
| `hyperparams` | list[json] |
| `train` | list[json] | 
| `rewards` | list[json] | 
| `requirements` | list[json] |

esempio di json object:
```json
{
    "config": [{"line": 5, "type": "removed", "content": "  lr: 1e-4"}, ...],
    "requirements": [...],
    "train": [...],
    "rewards": {
      "math_reward.py": [...],
      "format_reward.py": []
    }
}

```

### 3.3 Constraints e Indici Neo4j

```cypher
CREATE CONSTRAINT recipe_id     IF NOT EXISTS FOR (r:Recipe)     REQUIRE r.recipe_id IS UNIQUE;
CREATE CONSTRAINT experiment_id IF NOT EXISTS FOR (e:Experiment) REQUIRE e.exp_id IS UNIQUE;
CREATE CONSTRAINT checkpoint_id IF NOT EXISTS FOR (c:Checkpoint) REQUIRE c.ckp_id IS UNIQUE;
CREATE CONSTRAINT model_name    IF NOT EXISTS FOR (m:Model)      REQUIRE m.model_name IS UNIQUE;
```

### 3.4 APOC Triggers

**Timestamp automatico** (created_at / updated_at):

```cypher
CALL apoc.trigger.install('neo4j', 'setNodeTimestamps', '
  UNWIND $createdNodes AS n
  SET n.created_at = coalesce(n.created_at, datetime()),
      n.updated_at = coalesce(n.updated_at, datetime())
  UNION ALL
  UNWIND keys($assignedNodeProperties) AS key
  UNWIND $assignedNodeProperties[key] AS map
  WITH map.node AS node, collect(map.key) AS propList
  WHERE NOT "updated_at" IN propList
  SET node.updated_at = datetime()
', {phase: "before"});
```

**Validation guard** (Checkpoint orfano):

```cypher
CALL apoc.trigger.install('neo4j', 'validateCheckpointHasExperiment', '
  UNWIND $createdNodes AS n
  WITH n WHERE "Checkpoint" IN labels(n)
  CALL apoc.util.validate(
    NOT EXISTS { MATCH (e:Experiment)-[:PRODUCED]->(n) },
    "Checkpoint %s must have a PRODUCED relationship from an Experiment",
    [n.ckp_id]
  )
  RETURN n
', {phase: "before"});
```

> **⚠️ Agent Note**: I trigger APOC richiedono che il plugin APOC sia installato e che `apoc.trigger.enabled=true` sia nella configurazione Neo4j. Verificare nel `docker-compose.yml` prima di eseguire lo schema.

---

## 4. Shared Layer — Dataclass e Hashing

**Percorso sorgente**: `envelope/middleware/shared/`
**Percorso negli scaffold**: `setups/setup_{name}/shared/`
**Dipendenze esterne**: solo `pydantic` (già presente)

### 4.1 `dataclasses.py` — Modelli Pydantic

Definisce tutti i nodi, le relazioni e gli envelope operativi. È il contratto condiviso tra Worker e Master.

```python
# Nodi Neo4j
class RecipeNode(BaseModel): ...
class ModelNode(BaseModel): ...
class ExperimentNode(BaseModel): ...
class CheckpointNode(BaseModel): ...
class ComponentNode(BaseModel): ...

# Enum relazioni
class RelationType(str, Enum):
    USED_FOR = "USED_FOR"
    SELECTED_FOR = "SELECTED_FOR"
    BASED_ON = "BASED_ON"
    PRODUCED = "PRODUCED"
    DERIVED_FROM = "DERIVED_FROM"
    STARTED_FROM = "STARTED_FROM"
    RETRY_OF = "RETRY_OF"
    MERGED_FROM = "MERGED_FROM"

# Relazione con payload
class DerivedFromRel(BaseModel):
    source_exp_id: str
    target_exp_id: str
    diff_patch: dict  # {filename: (old_hash, new_hash)}

# Enum strategia handshake
class Strategy(str, Enum):
    NEW = "NEW"
    RESUME = "RESUME"
    BRANCH = "BRANCH"
    RETRY = "RETRY"

# Envelope operativi Worker → Master
class HandshakeRequest(BaseModel):
    config_hash: str           # SHA256 aggregato dei file trigger
    hyperparams_hash: str
    req_hash: str              # SHA256 di requirements.txt (non trigger, ma tracciato)
    code_hash: str             # SHA256 di train.py (incluso nell'aggregated_hash)
    checkpoint_id_to_resume: Optional[str] = None
    scaffold_path: str
    base_exp_id: Optional[str] = None    # richiesto per BRANCH
    recipe_id: Optional[str] = None
    model_id: Optional[str] = None
    # Contenuti testuali dei file (inviati al Master per popolare ExperimentNode)
    config_text: str           # contenuto di config.yaml
    train_text: str            # contenuto di train.py
    requirements_text: str     # contenuto di requirements.txt (testo semplice)
    rewards_texts: list[str]   # contenuti dei file rewards/* (lista parallela)
    rewards_filenames: list[str]  # nomi file rewards/* (lista parallela)

class HandshakeResponse(BaseModel):
    exp_id: str
    strategy: Strategy
    base_checkpoint_uri: Optional[str] = None

class CheckpointPush(BaseModel):
    exp_id: str
    ckp_id: str
    epoch: int
    run: int
    metrics_snapshot: dict
    uri: Optional[str]         # NULL se scartato
    is_usable: bool
    transfer_policy: str       # ALL | BEST_ONLY | SKIP

class SyncEvent(BaseModel):
    event_id: str              # UUID, per idempotenza
    event_type: str
    payload: dict
    timestamp_worker: datetime
    exp_id: str
```

### 4.2 `hashing.py` — ConfigHasher e DiffEngine

#### File che attivano la creazione di un nuovo Experiment

Un nuovo `Experiment` viene creato (strategia `BRANCH` o `NEW`) ogni volta che cambia l'hash di **almeno uno** dei seguenti file:

| File | Nota |
|------|------|
| `config.yaml` | Configurazione dataset e training |
| `train.py` | Script di training principale |
| `rewards/*.py` | Qualsiasi file nella cartella rewards |

`requirements.txt` **non** fa parte del trigger hash: la sua modifica non genera un nuovo experiment, ma il suo contenuto viene comunque salvato nel nodo.

```python
class ConfigSnapshot(BaseModel):
    """Serializzabile in JSON, salvata in lineage/snapshots/."""
    snapshot_id: str           # = aggregated_hash (deterministico)
    files: dict[str, str]      # {filename: sha256} — solo i file trigger
    aggregated_hash: str       # SHA256 concatenazione hash ordinati per filename
    created_at: datetime

class ConfigHasher:
    # File trigger (path relative allo scaffold root)
    TRIGGER_FILES = ["config.yaml", "train.py"]
    TRIGGER_DIRS  = ["rewards"]  # tutti i file *.py dentro rewards/

    @staticmethod
    def hash_file(path: Path) -> str:
        """SHA256 di un singolo file."""

    @staticmethod
    def hash_config(scaffold_dir: Path) -> ConfigSnapshot:
        """
        Calcola hash solo dei file trigger (config.yaml, train.py, rewards/*).
        requirements.txt è escluso dal calcolo hash ma il suo testo viene
        letto separatamente e passato come campo `requirements` all'ExperimentNode.
        """

    @staticmethod
    def diff_snapshots(old: ConfigSnapshot, new: ConfigSnapshot) -> dict:
        """
        Ritorna {filename: (old_hash, new_hash)} per i soli file cambiati.
        Usato internamente per decidere quali file sottoporre a diff testuale.
        """
```

#### Sistema di Diff Git-Style

Sostituisce il precedente `diff_patch: JSON` con hash generici. Il diff viene calcolato lato Worker prima dell'handshake, confrontando lo snapshot corrente con quello dell'ultimo esperimento noto.

**Struttura del campo `diff_patch`** (salvato nella relazione `DERIVED_FROM`):

```json
{
  "config": [
    {"line": 5,  "type": "removed", "content": "  lr: 1e-4"},
    {"line": 5,  "type": "added",   "content": "  lr: 5e-5"},
    {"line": 12, "type": "removed", "content": "  epochs: 3"},
    {"line": 12, "type": "added",   "content": "  epochs: 5"}
  ],
  "requirements": [
    {"line": 8, "type": "added", "content": "mergekit==0.0.5"}
  ],
  "train": [
    {"line": 47, "type": "removed", "content": "    optimizer = AdamW(lr=1e-4)"},
    {"line": 47, "type": "added",   "content": "    optimizer = AdamW(lr=5e-5)"}
  ],
  "rewards": {
    "math_reward.py": [
      {"line": 23, "type": "removed", "content": "    return score * 0.8"},
      {"line": 23, "type": "added",   "content": "    return score * 1.0"}
    ],
    "format_reward.py": []
  }
}
```

Ogni entry del diff è un oggetto con:
- `line` (int): numero di riga nel file **nuovo** (per added) o **vecchio** (per removed)
- `type` (str): `"added"` | `"removed"` | `"context"` (le righe context sono opzionali, default omesse)
- `content` (str): contenuto della riga, senza `\n` finale

**Implementazione consigliata** in `hashing.py`:

```python
import difflib

class DiffEngine:
    @staticmethod
    def compute_file_diff(old_text: str, new_text: str) -> list[dict]:
        """
        Produce lista di {line, type, content} confrontando old_text e new_text
        riga per riga con difflib.unified_diff.
        Emette solo righe 'added' e 'removed' (context omesso per compattezza).
        """
        result = []
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()
        old_line_no = 0
        new_line_no = 0
        for line in difflib.unified_diff(old_lines, new_lines, lineterm=""):
            if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
                # parse @@ per aggiornare contatori riga
                continue
            if line.startswith("-"):
                old_line_no += 1
                result.append({"line": old_line_no, "type": "removed", "content": line[1:]})
            elif line.startswith("+"):
                new_line_no += 1
                result.append({"line": new_line_no, "type": "added", "content": line[1:]})
            else:
                old_line_no += 1
                new_line_no += 1
        return result

    @staticmethod
    def compute_scaffold_diff(
        old_snapshot: ConfigSnapshot,
        new_snapshot: ConfigSnapshot,
        old_texts: dict[str, str],   # {filename: contenuto}
        new_texts: dict[str, str],
    ) -> dict:
        """
        Calcola diff per tutti i file tracciati (config.yaml, requirements.txt,
        train.py, rewards/*) e ritorna la struttura diff_patch completa.
        rewards è un dict {filename: [diff_entries]}.
        """
```

> **⚠️ Agent Note**: `requirements.txt` va incluso nel diff testuale anche se **non** fa parte del trigger hash. Questo permette di vedere l'evoluzione delle dipendenze nel lineage anche senza creare nuovi experiment. Il diff di `requirements.txt` viene quindi calcolato e salvato in `diff_patch.requirements`, ma non influenza la strategia handshake.

---

## 5. Worker Layer — Esecuzione Locale

**Percorso sorgente**: `envelope/middleware/worker/`
**Percorso negli scaffold**: `setups/setup_{name}/worker/`

### 5.1 `connection/base.py` — ABC

```python
class TransferPolicy(str, Enum):
    ALL = "ALL"
    BEST_ONLY = "BEST_ONLY"
    SKIP = "SKIP"

class BaseConnection(ABC):
    @abstractmethod
    def connect(self) -> bool: ...

    @abstractmethod
    def send_metadata(self, endpoint: str, payload: dict) -> dict: ...

    @abstractmethod
    def transfer_file(
        self,
        local_path: Path,
        remote_path: str,
        policy: TransferPolicy = TransferPolicy.ALL
    ) -> bool: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def is_alive(self) -> bool: ...
```

### 5.2 `connection/http.py` — HTTPConnection

- Usa `httpx` (sync).
- Endpoint base da env var `MASTER_URL`.
- `send_metadata` → POST all'endpoint specificato.
- `transfer_file` → multipart upload.

### 5.3 `connection/ssh.py` — SSHConnection

- Usa `paramiko`.
- Hostname/user/key da env vars `MASTER_SSH_HOST`, `MASTER_SSH_USER`, `MASTER_SSH_KEY_PATH`.
- `send_metadata` → esegue `curl` sul master via canale SSH.
- `transfer_file` → `SFTPClient.put()` (o rsync via subprocess).

### 5.4 `local_persistence.py` — Stato Persistente

Gestisce `lineage/worker_state.json`. Ogni modifica è atomica (write su tmp + rename).

**Struttura `worker_state.json`**:

```json
{
  "scaffold_dir": "/path/to/setup_grpo-math-v1",
  "current_exp_id": "uuid-or-null",
  "current_run": 0,
  "strategy": "NEW|RESUME|BRANCH|RETRY",
  "config_snapshot": { "...ConfigSnapshot..." },
  "pending_events": [],
  "last_synced_at": "2025-01-01T00:00:00Z",
  "handshake_done": false,
  "transfer_log": []
}
```

**Metodi chiave**:

```python
def load_or_init(scaffold_dir: Path) -> WorkerState
def save(state: WorkerState) -> None             # atomic write (tmp + rename)
def record_event(state, event: SyncEvent)        # append a pending_events
def mark_sent(state, event_id: str)              # rimuove da pending_events
def take_snapshot(state, scaffold_dir) -> str    # snapshot_id
```

Ogni operazione appende anche a `lineage/transfer_log.jsonl` (audit trail append-only, non riscrivere).

### 5.5 `fs_watcher.py` — Watcher Filesystem

Usa `watchdog`. Monitora:

| Path monitorato | Evento emesso |
|-----------------|---------------|
| `lineage/to_transfer/` | Nuovo file → evento da pushare |
| `training_metrics/` | Append su file di log → evento incrementale |
| `config.yaml`, `requirements.txt`, `rewards/` | Cambiamento → potenziale BRANCH |

Emette eventi in una `queue.Queue` thread-safe consumata dal daemon.

### 5.6 `pusher.py` — Coda Asincrona

```python
class AsyncPusher:
    def __init__(self, connection: BaseConnection, state: WorkerState): ...

    def enqueue(self, event: SyncEvent) -> None: ...

    def run_forever(self, stop_event: threading.Event) -> None:
        """
        Loop: drain queue → send → on failure: requeue con backoff esponenziale.
        Idempotenza: ogni evento ha event_id univoco.
        Il Master ignora duplicati (stesso event_id).
        """

    def flush_and_stop(self) -> None:
        """Attende svuotamento coda, poi setta stop_event."""
```

### 5.7 `daemon.py` — Entry Point Processo Separato

Chiamato da `run.sh` **prima** di `train.py`. Argomenti CLI: `--scaffold-dir PATH --master-url URL --connection-type http|ssh`.

**Flusso di esecuzione**:

```
1. Carica/inizializza worker_state
2. Calcola ConfigSnapshot corrente
3. Confronta con snapshot precedente
   → Se diverso: registra diff come pending BRANCH event
4. HANDSHAKE bloccante con Master
   → Riceve exp_id + strategy
   → Salva in worker_state
   → Scrive lineage/.handshake_done  ← train.py aspetta questo file
5. Avvia fs_watcher (thread)
6. Avvia AsyncPusher (thread)
7. Loop principale: consuma eventi da fs_watcher → pusher.enqueue()
8. Monitora lineage/.training_done  ← scritto da train.py alla fine
9. Quando training_done: flush_and_stop() → disconnect() → exit(0)
```

**File di coordinamento** (dentro `lineage/`):

| File | Scritto da | Letto da | Significato |
|------|-----------|---------|-------------|
| `.handshake_done` | daemon | train.py | Handshake OK, training può iniziare |
| `.training_done` | train.py | daemon | Training finito, daemon può fare flush |
| `.exp_id` | daemon | train.py | Exp ID corrente per i log |

> **⚠️ Agent Note**: Il daemon deve gestire il caso in cui il Master non sia raggiungibile durante l'handshake. Dopo il timeout configurabile (default 30s), il training procede con un warning ma **senza** lineage tracking attivo. Questo è il comportamento degraded gracefully definito in `run.sh`.

---

## 6. Master Layer — Orchestratore Centrale

**Percorso**: `master/`

### 6.1 `neo4j/repository.py` — Query Cypher Atomiche

```python
class ExperimentRepository:

    def create_experiment(self,
        exp: ExperimentNode, recipe_id: str, model_id: str) -> str: ...

    def create_derived_experiment(self,
        base_exp_id: str, new_exp: ExperimentNode,
        diff_patch: dict, start_ckp_id: Optional[str]) -> str:
        """
        Crea in una sola transazione:
        (new_exp)-[:DERIVED_FROM {diff_patch}]->(base_exp)
        Se start_ckp_id: (new_exp)-[:STARTED_FROM]->(ckp)
        """

    def create_retry_experiment(self,
        base_exp_id: str, new_exp: ExperimentNode) -> str:
        """(new_exp)-[:RETRY_OF]->(base_exp)"""

    def upsert_checkpoint(self, ckp: CheckpointNode) -> str:
        """Idempotente: MERGE su ckp_id, poi SET proprietà."""

    def create_merged_checkpoint(self,
        source_ckp_ids: list[str], new_ckp: CheckpointNode) -> str:
        """Crea nuovo ckp + N relazioni MERGED_FROM."""

    def find_experiment_by_hashes(self,
        config_hash: str, hyperparams_hash: str,
        req_hash: str, code_hash: str) -> Optional[ExperimentNode]: ...

    def get_latest_checkpoint(self, exp_id: str) -> Optional[CheckpointNode]: ...

    def update_experiment_status(self,
        exp_id: str, status: str, exit_status: Optional[str]): ...
```

### 6.2 `api/lineage_controller.py` — Logica di Branching

```python
class LineageController:

    def process_handshake(self, req: HandshakeRequest) -> HandshakeResponse:
        existing = repo.find_experiment_by_hashes(
            req.config_hash, req.hyperparams_hash,
            req.req_hash, req.code_hash
        )

        # RESUME: hash identico + stesso ultimo checkpoint
        if existing and req.checkpoint_id_to_resume:
            last_ckp = repo.get_latest_checkpoint(existing.exp_id)
            if last_ckp and last_ckp.ckp_id == req.checkpoint_id_to_resume:
                return HandshakeResponse(exp_id=existing.exp_id,
                                         strategy=Strategy.RESUME, ...)

        # RETRY: hash identico, parte da zero
        if existing and not req.checkpoint_id_to_resume:
            exp_id = repo.create_retry_experiment(existing.exp_id, new_exp)
            return HandshakeResponse(exp_id=exp_id, strategy=Strategy.RETRY)

        # BRANCH: hash diverso, parte da un checkpoint esistente
        if not existing and req.checkpoint_id_to_resume:
            diff = compute_diff(req)
            exp_id = repo.create_derived_experiment(
                req.base_exp_id, new_exp, diff, req.checkpoint_id_to_resume
            )
            return HandshakeResponse(exp_id=exp_id, strategy=Strategy.BRANCH, ...)

        # NEW: primo esperimento assoluto
        exp_id = repo.create_experiment(new_exp, req.recipe_id, req.model_id)
        return HandshakeResponse(exp_id=exp_id, strategy=Strategy.NEW)
```

### 6.3 `api/routes.py` — Endpoint FastAPI

| Method | Endpoint | Handler | Descrizione |
|--------|----------|---------|-------------|
| `POST` | `/handshake` | `LineageController.process_handshake()` | Fase bloccante iniziale |
| `POST` | `/experiments/{exp_id}/checkpoints` | `repo.upsert_checkpoint()` | Push checkpoint (idempotente) |
| `PATCH` | `/experiments/{exp_id}/status` | `repo.update_experiment_status()` | Aggiorna stato esperimento |
| `POST` | `/experiments/{exp_id}/events` | log generico | Log evento generico (metriche, hw...) |
| `POST` | `/checkpoints/merge` | `repo.create_merged_checkpoint()` | Merge N checkpoint |
| `GET` | `/experiments/{exp_id}/lineage` | query grafo | Grafo completo di un esperimento |
| `GET` | `/health` | status check | Stato Neo4j + storage |

**Autenticazione**: header `X-API-Key` validato da `middleware.py`.

### 6.4 `storage/` — URI Resolver e Writer Astratto

```python
class BaseStorageWriter(ABC):
    @abstractmethod
    def write(self, local_path: Path, uri: str) -> str: ...   # ritorna URI finale
    @abstractmethod
    def read(self, uri: str) -> bytes: ...
    @abstractmethod
    def exists(self, uri: str) -> bool: ...

class LocalStorageWriter(BaseStorageWriter):
    """uri schema: file:///abs/path/to/file — copia in directory configurata del master."""

class URIResolver:
    """
    Legge prefisso URI e dispatcha al writer corretto:
    file:///  → LocalStorageWriter
    s3://     → S3StorageWriter (stub)
    nfs://    → NFSStorageWriter (stub)
    worker:// → URI locale del worker (non scaricabile direttamente)
    master:// → URI locale del master
    """
```

> **⚠️ Agent Note**: I prefissi URI `worker://` e `master://` dipendono dall'ambiente di esecuzione. Il `URIResolver` deve ricevere come parametro di configurazione il mapping prefisso → path assoluto (da `.env`). Non hardcodare path.

---

## 7. Logica di Branching e Casistiche

### 7.1 Matrice Decisionale Handshake

| Hash identico | Checkpoint richiesto | Strategia | Azione Master |
|---------------|---------------------|-----------|---------------|
| ✅ | ✅ (ultimo ckp) | **RESUME** | Ritorna `exp_id` esistente |
| ✅ | ❌ | **RETRY** | Crea nuovo `Experiment` + `RETRY_OF` |
| ❌ | ✅ | **BRANCH** | Crea nuovo `Experiment` + `DERIVED_FROM` + `STARTED_FROM` |
| ❌ | ❌ | **NEW** | Crea nuovo `Experiment` isolato |

### 7.2 Caso: RESUME (Continuità)

**Trigger**: Il Worker invia lo stesso triplo hash (`config`, `hyperparams`, `code`) e chiede di ripartire dall'ultimo checkpoint della stessa run.

**Comportamento Master**: Autorizza il proseguimento sullo stesso nodo `Experiment` senza creare nuovi nodi.

### 7.3 Caso: BRANCH (Cambio Traiettoria)

**Trigger**: Hash config/hyperparams/code diverso rispetto all'esperimento precedente + checkpoint di partenza fornito.

**Comportamento Master**:
1. Crea nuovo `Experiment`.
2. Lega con `DERIVED_FROM {diff_patch}` all'esperimento precedente.
3. Lega con `STARTED_FROM` al checkpoint fisico di partenza.

**Nota**: È possibile fare un BRANCH che parte dal modello base (senza `STARTED_FROM`), per esempio se si vuole solo cambiare gli iperparametri e ripartire da zero. In quel caso si invia solo `DERIVED_FROM`, senza `STARTED_FROM`.

### 7.4 Caso: RETRY (Nuovo Tentativo)

**Trigger**: Hash identico, nessun checkpoint di partenza (start from zero).

**Comportamento Master**: Crea nuovo `Experiment` legato al precedente con `RETRY_OF`. Preserva lo storico dei fallimenti senza contaminare i nuovi dati.

### 7.5 Caso: MERGING (Fusione di Pesi)

**Trigger**: L'utente richiede di fondere N checkpoint (inter o intra esperimento) tramite `mergekit`.

**Comportamento**:
1. Scaffold dedicato: `setup_merge_{name}/` (vedi §9.3).
2. Script `merge.py` esegue `mergekit` sui checkpoint sorgente.
3. Se l'esecuzione riesce: crea nuovo `Checkpoint` con N relazioni `MERGED_FROM`.
4. Il nuovo checkpoint non è necessariamente figlio di un `PRODUCED` (può esistere senza training attivo).

> **⚠️ Agent Note**: La relazione `MERGED_FROM` va da `new_ckp → source_ckp` (direzione: "è stato creato da"). Non invertire la direzione.

---

## 8. Protocollo di Comunicazione

### 8.1 Architettura a Strati

```
Worker                    Transport                 Master
  │                                                   │
  │  HandshakeRequest ──────────────────────────────▶ │
  │                                                   │  (bloccante)
  │  HandshakeResponse ◀────────────────────────────  │
  │                                                   │
  │  SyncEvent (fire & forget) ─────────────────────▶ │
  │  CheckpointPush    ─────────────────────────────▶ │
  │  FileTransfer      ─────────────────────────────▶ │
  │                                                   │
```

Il layer di trasporto è astratto da `BaseConnection`. La logica dei messaggi (cosa inviare, quando) è nel daemon, indipendente dal trasporto.

### 8.2 Handshake Protocol (Bloccante)

Unica fase bloccante del sistema. Il Worker non inizia il training finché non riceve `HandshakeResponse`.

1. Worker calcola i 4 hash (`config`, `hyperparams`, `requirements`, `committed_code`).
2. Worker invia `HandshakeRequest` al Master.
3. Master esegue `LineageController.process_handshake()`.
4. Master risponde con `HandshakeResponse` (exp_id + strategy).
5. Daemon scrive `lineage/.handshake_done`.
6. `run.sh` rileva il file e procede con il training.

**Timeout**: 30 secondi. Se scade, training procede in modalità degradata (senza lineage).

### 8.3 Staged Sync (Fire and Forget)

Dopo l'handshake, il Worker invia eventi in modo asincrono:

- **Idempotenza**: ogni `SyncEvent` ha un `event_id` UUID. Il Master ignora duplicati.
- **Retry con backoff**: il `AsyncPusher` fa retry esponenziale in caso di rete assente.
- **Audit trail**: ogni evento inviato viene registrato in `lineage/transfer_log.jsonl`.

### 8.4 URI Management

Il sistema supporta 5 schemi URI:

| Schema | Significato | Risolvibile da |
|--------|-------------|----------------|
| `worker:///path` | Path locale sul worker | Solo worker |
| `master:///path` | Path locale sul master | Solo master |
| `file:///path` | Path assoluto filesystem | Chiunque ha accesso |
| `s3://bucket/key` | AWS S3 (stub) | Chiunque con credenziali |
| `nfs:///mount/path` | NFS condiviso (stub) | Macchine con mount |

Se `uri = NULL`: il checkpoint esiste nel grafo (per la coerenza storica del lineage) ma i pesi sono stati scartati. La UI deve mostrare il nodo ma disabilitare "Resume" e "Download".

---

## 9. Integrazione nel Generator Esistente

### 9.0 Datamix dal Recipe al Setup

Il Recipe definisce il datamix come un dizionario di URI dataset con le rispettive repliche:
```yaml
# Esempio recipe_config (salvato in RecipeNode.config_yaml)
/nfs/mapped-data/velvet_v1/allenai/ai2_arc/ARC-Challenge/downsampled__0.7__en:
  dist_name: Downsampled__0.70__mapped__ARC-Challenge/en
  replica: 1
  samples: 1603
  tokens: 141889
  chat_type: simple_chat_cycle2

/nfs/mapped-data/velvet_v1/openai/gsm8k/main/en:
  dist_name: GSM8K/main/en
  replica: 3
  samples: 7473
  tokens: 892044
  chat_type: simple_chat_cycle2
```
Il config.yaml dello scaffold ha attualmente una sezione dataset pensata per un singolo dataset con URI e campi fissi. Questa struttura deve essere estesa per supportare il datamix multi-sorgente definito nel Recipe.

#### Nuova Struttura dataset nel config.yaml dello Scaffold
Quando uno scaffold viene generato a partire da un Recipe, la sezione dataset viene sostituita con un blocco datamix:
```yaml
# config.yaml dello scaffold — sezione dataset generata da Recipe
datamix:
  format: rl                    # formato che indica il tipo di train conf, anche se abbiamo schema_template a dircelo implicitamente, fai in modo che sia solo un metadato informativo
  split_train: train
  split_eval: test
  prepare:
    cache_dir: ./data_cache
    num_proc: 4

  sources:
    - uri: /nfs/mapped-data/velvet_v1/allenai/ai2_arc/ARC-Challenge/downsampled__0.7__en
      replica: 1
      samples: 1603
      dist_name: Downsampled__0.70__mapped__ARC-Challenge/en
      chat_type: simple_chat_cycle2
      system_prompt:
        - p1 content
      system_prompt_name: 
        - p1
      dist_id: UUID
      dist_uri: ...
      schema_template: ...
  

    - uri: /nfs/mapped-data/velvet_v1/openai/gsm8k/main/en
      replica: 3
      samples: 7473
      dist_name: GSM8K/main/en
      chat_type: simple_chat_cycle2
      system_prompt:
        - p2 content
      system_prompt_name: 
        - p2
      dist_id: UUID
      dist_uri: ...
      schema_temnplate: ...
```
Semantica di replica: il dataset viene campionato replica volte nel mix. Un dataset con replica: 3 contribuisce al triplo dei sample rispetto a uno con replica: 1.

Il DatamixLoader normalizza i pesi prima di costruire il dataset finale.
La vecchia struttura dataset.train_uri / dataset.subset rimane valida come fallback per scaffold generati senza Recipe (dataset singolo), mantenendo compatibilità con gli scaffold esistenti.

#### DatamixLoader — Adattamento del Dataloader
Il prepare.py dello scaffold deve essere aggiornato per gestire entrambe le strutture. Il loader rileva automaticamente la chiave datamix vs dataset e instrada di conseguenza:
python# prepare.py — logica di caricamento adattiva
```python
def load_dataset_from_config(config: dict) -> Dataset:
    if "datamix" in config:
        return _load_datamix(config["datamix"])
    elif "dataset" in config:
        return _load_single(config["dataset"])
    else:
        raise ValueError("config.yaml deve contenere 'datamix' o 'dataset'")


def _load_datamix(cfg: dict) -> Dataset:
    """
    Carica e concatena N dataset sorgente applicando le repliche come pesi.

    Per ogni source in cfg["sources"]:
      1. Carica il dataset dall'URI locale o HuggingFace Hub.
      2. Applica replica come oversampling intero
         (repeat dataset replica volte prima di concatenare).
      3. Applica max_samples proporzionale se specificato globalmente.

    Ritorna un Dataset HuggingFace concatenato e shufflato.
    """
    from datasets import load_from_disk, load_dataset, concatenate_datasets

    shards = []
    for source in cfg["sources"]:
        uri = source["uri"]
        replica = source.get("replica", 1)

        # Carica da filesystem locale (NFS, worker path) o Hub
        if uri.startswith("/") or uri.startswith("./"):
            ds = load_from_disk(uri)
        else:
            ds = load_dataset(uri, split=cfg.get("split_train", "train"))

        # Applica replica come ripetizione esatta del shard
        shards.extend([ds] * replica)

    combined = concatenate_datasets(shards).shuffle(seed=42)

    # max_samples globale opzionale
    if "max_samples" in cfg:
        combined = combined.select(range(min(cfg["max_samples"], len(combined))))

    return combined


def _load_single(cfg: dict) -> Dataset:
    """Comportamento originale — dataset singolo da URI o Hub."""
    from datasets import load_dataset
    ds = load_dataset(cfg["train_uri"], name=cfg.get("subset"), split=cfg.get("split_train", "train"))
    if "max_samples" in cfg:
        ds = ds.select(range(min(cfg["max_samples"], len(ds))))
    return ds
```
ricerca in docs/config.md per adattarklo se serve, forse troppe classi sono state definite,, il prepare.py alla fine è un file che deve essere modificato a mano, con configuraizonei standardpotrebbe non adattarsi.

### 9.1 Step 16: `inject_worker_middleware()`

Aggiunto alla pipeline di `setup_generator.py` come ultimo step:

```python
def inject_worker_middleware(scaffold_dir: Path, envelope_dir: Path) -> None:
    """
    Copia envelope/middleware/worker/ → setup_*/worker/
    Copia envelope/middleware/shared/ → setup_*/shared/
    Crea setup_*/lineage/.gitkeep (placeholder)
    Aggiunge a requirements.txt: watchdog, httpx, paramiko
    """
```

### 9.2 Modifiche al Template `run.sh.j2`

```bash
#!/bin/bash
set -euo pipefail
source .venv/bin/activate 2>/dev/null || true

# --- LINEAGE DAEMON ---
MASTER_URL="${MASTER_URL:-http://localhost:8000}"
CONNECTION_TYPE="${CONNECTION_TYPE:-http}"

python worker/daemon.py \
    --scaffold-dir "$(pwd)" \
    --master-url "$MASTER_URL" \
    --connection-type "$CONNECTION_TYPE" &
DAEMON_PID=$!

# Attendi handshake (max 30s)
TIMEOUT=30; ELAPSED=0
while [ ! -f "lineage/.handshake_done" ] && [ $ELAPSED -lt $TIMEOUT ]; do
    sleep 1; ELAPSED=$((ELAPSED+1))
done

if [ ! -f "lineage/.handshake_done" ]; then
    echo "LINEAGE_WARNING: Handshake timeout. Training proceeds WITHOUT lineage tracking."
    kill $DAEMON_PID 2>/dev/null || true
fi

# --- TRAINING ---
{{ launch_command }}
TRAIN_EXIT=$?

# Segnala fine al daemon
touch lineage/.training_done

# Attendi flush del daemon (max 120s)
wait $DAEMON_PID || true

exit $TRAIN_EXIT
```

### 9.3 Scaffold per Merge

Generato da `technique: merge` (tecnica speciale no-GPU nella capability matrix):

```
setup_merge_{name}/
├── merge.py          # one-shot: carica ckp → mergekit → salva → push lineage
├── config.yaml       # Lista URI ckp sorgente + metodo merge (slerp, ties, dare...)
├── requirements.txt  # mergekit + deps worker
├── worker/           # Copiato come per tutti gli scaffold
├── shared/
└── lineage/
```

**Flusso `merge.py`**:

1. Legge `config.yaml` con URI dei checkpoint sorgente e metodo merge.
2. Esegue `mergekit` con la configurazione specificata.
3. Se OK: crea `lineage/to_transfer/{new_ckp_id}/` con metadati del checkpoint merged.
4. Chiama `daemon.py --one-shot` (nessun watcher, solo push e exit).
5. Il daemon crea il nodo `Checkpoint` con `MERGED_FROM` verso i sorgenti.

---

## 10. Osservabilità — OpenTelemetry e Phoenix

### 10.1 Obiettivo

Monitorare in tempo reale i messaggi scambiati tra Master e Worker: handshake, push checkpoint, sync eventi, trasferimento file. Phoenix funge da collector OTEL e fornisce una UI per visualizzare trace e span.

### 10.2 Struttura dei File

```
master/
├── observability/
│   ├── __init__.py
│   └── tracing.py       ← setup_tracing() + get_tracer() (vedi §10.3)
```

Il modulo `tracing.py` viene importato una sola volta in `master/api/app.py` alla startup:

```python
# master/api/app.py
from master.observability.tracing import setup_tracing

app = FastAPI()

@app.on_event("startup")
async def startup():
    setup_tracing()   # idempotente, legge env vars
```

### 10.3 `master/observability/tracing.py`

```python
"""Centralized Phoenix tracing setup.

Bootstraps OpenTelemetry tracing with Arize Phoenix as the collector.
Call setup_tracing() once at application startup (in app.py).

Environment variables:
    PHOENIX_COLLECTOR_ENDPOINT  Default "http://localhost:4317"  (OTLP gRPC)
    PHOENIX_PROJECT_NAME        Default "lineage-master"
    PHOENIX_TRACING_ENABLED     Default "true". Set "false" to disable.
"""
from __future__ import annotations
import logging
import os

logger = logging.getLogger(__name__)
_INITIALISED = False


def setup_tracing(
    project_name: str | None = None,
    endpoint: str | None = None,
    enabled: bool | None = None,
) -> bool:
    """Inizializza Phoenix OTEL tracing (idempotente).

    Returns True se il tracing è stato inizializzato, False altrimenti.
    Non solleva eccezioni: fallisce silenziosamente per non bloccare il Master.
    """
    global _INITIALISED
    if _INITIALISED:
        return True

    if enabled is None:
        enabled = os.getenv("PHOENIX_TRACING_ENABLED", "true").lower() in ("true", "1", "yes")
    if not enabled:
        logger.info("Phoenix tracing disabled via configuration")
        return False

    if project_name is None:
        project_name = os.getenv("PHOENIX_PROJECT_NAME", "lineage-master")
    if endpoint is None:
        endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:4317")

    try:
        from phoenix.otel import register
        register(
            project_name=project_name,
            endpoint=endpoint,
            auto_instrument=True,
            batch=True,
        )
        _INITIALISED = True
        logger.info("Phoenix tracing initialised (project=%s, endpoint=%s)", project_name, endpoint)
        return True
    except Exception:
        logger.warning("Phoenix tracing setup failed — continuing without tracing", exc_info=True)
        return False


def get_tracer(name: str = "lineage-master"):
    """Ritorna un tracer OTEL per span manuali.

    Ritorna un no-op tracer se OTEL non è installato o il tracing è disabilitato.
    Uso tipico: strumentare manualmente gli endpoint critici (handshake, ckp push).
    """
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        from contextlib import contextmanager

        class _NoOpSpan:
            def set_attribute(self, key, value): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass

        class _NoOpTracer:
            @contextmanager
            def start_as_current_span(self, name, **kwargs):
                yield _NoOpSpan()

        return _NoOpTracer()
```

### 10.4 Span Manuali negli Endpoint Critici

Gli endpoint più rilevanti per il monitoring del flusso Master ↔ Worker vengono strumentati con span manuali, in aggiunta all'auto-instrumentation FastAPI:

```python
# Esempio in master/api/routes.py
from master.observability.tracing import get_tracer

tracer = get_tracer("lineage.routes")

@router.post("/handshake")
async def handshake(req: HandshakeRequest):
    with tracer.start_as_current_span("handshake") as span:
        span.set_attribute("worker.scaffold_path", req.scaffold_path)
        span.set_attribute("worker.config_hash", req.config_hash)
        span.set_attribute("worker.base_exp_id", req.base_exp_id or "none")
        response = controller.process_handshake(req)
        span.set_attribute("lineage.strategy", response.strategy)
        span.set_attribute("lineage.exp_id", response.exp_id)
        return response

@router.post("/experiments/{exp_id}/checkpoints")
async def push_checkpoint(exp_id: str, ckp: CheckpointPush):
    with tracer.start_as_current_span("checkpoint_push") as span:
        span.set_attribute("exp_id", exp_id)
        span.set_attribute("ckp.epoch", ckp.epoch)
        span.set_attribute("ckp.is_usable", ckp.is_usable)
        span.set_attribute("ckp.uri_null", ckp.uri is None)
        return repo.upsert_checkpoint(ckp)
```

**Span raccomandati da strumentare**:

| Span name | Endpoint | Attributi chiave |
|-----------|----------|------------------|
| `handshake` | `POST /handshake` | `config_hash`, `strategy`, `exp_id`, `base_exp_id` |
| `checkpoint_push` | `POST /experiments/{id}/checkpoints` | `epoch`, `is_usable`, `uri_null` |
| `status_update` | `PATCH /experiments/{id}/status` | `status`, `exit_status` |
| `checkpoint_merge` | `POST /checkpoints/merge` | `source_count`, `new_ckp_id` |
| `sync_event` | `POST /experiments/{id}/events` | `event_type`, `worker_ts` |

### 10.5 Integrazione Docker

Phoenix viene aggiunto come servizio nel `docker-compose.yml`:

```yaml
services:
  phoenix:
    image: arizephoenix/phoenix:latest
    ports:
      - "6006:6006"    # Phoenix UI
      - "4317:4317"    # OTLP gRPC collector
      - "4318:4318"    # OTLP HTTP collector
    environment:
      - PHOENIX_WORKING_DIR=/phoenix_data
    volumes:
      - phoenix_data:/phoenix_data

  master-api:
    build: .
    depends_on: [neo4j, phoenix]
    environment:
      PHOENIX_COLLECTOR_ENDPOINT: "http://phoenix:4317"
      PHOENIX_PROJECT_NAME: "lineage-master"
      PHOENIX_TRACING_ENABLED: "true"
    # ...

volumes:
  phoenix_data:
```

### 10.6 Dipendenze

Aggiungere al `master/requirements.txt` e all'extra `[master]` in `pyproject.toml`:

```
arize-phoenix-otel>=0.6
opentelemetry-sdk>=1.24
opentelemetry-exporter-otlp-proto-grpc>=1.24
openinference-instrumentation-fastapi>=0.1  # auto-instrument FastAPI
```

> **⚠️ Agent Note**: `auto_instrument=True` in `phoenix.otel.register()` strumenta automaticamente FastAPI e httpx. Non aggiungere manualmente `FastAPIInstrumentor` — causerebbe double-instrumentation. Se il servizio Phoenix non è raggiungibile all'avvio, `setup_tracing()` fallisce silenziosamente e il Master continua senza tracing: questo comportamento è intenzionale e va preservato.

---

## 11. Infrastruttura e Deployment

### 11.1 `master/docker-compose.yml`

```yaml
services:
  neo4j:
    image: neo4j:5.x
    environment:
      NEO4J_PLUGINS: '["apoc"]'
      NEO4J_apoc_trigger_enabled: "true"
      NEO4J_apoc_uuid_enabled: "true"
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
    volumes:
      - neo4j_data:/data
      - ./neo4j/init:/var/lib/neo4j/import
    ports:
      - "7474:7474"
      - "7687:7687"

  phoenix:
    image: arizephoenix/phoenix:latest
    ports:
      - "6006:6006"    # Phoenix UI
      - "4317:4317"    # OTLP gRPC collector
      - "4318:4318"    # OTLP HTTP collector
    environment:
      - PHOENIX_WORKING_DIR=/phoenix_data
    volumes:
      - phoenix_data:/phoenix_data

  master-api:
    build: .
    depends_on: [neo4j, phoenix]
    env_file: .env
    ports:
      - "8000:8000"
    volumes:
      - master_storage:/app/storage
    environment:
      PHOENIX_COLLECTOR_ENDPOINT: "http://phoenix:4317"
      PHOENIX_PROJECT_NAME: "lineage-master"
      PHOENIX_TRACING_ENABLED: "true"

volumes:
  neo4j_data:
  master_storage:
  phoenix_data:
```

**Script di init Neo4j**: file in `neo4j/init/` eseguiti in ordine alfabetico al primo avvio:
- `01_schema.cypher` — constraints e indici
- `02_triggers.cypher` — APOC triggers

### 11.2 Makefile — Nuovi Target

```makefile
master-up:           # docker-compose up -d (Neo4j + Phoenix + Master API)
master-down:         # docker-compose down
master-logs:         # docker-compose logs -f master-api
master-logs-phoenix: # docker-compose logs -f phoenix
master-init-db:      # applica schema + APOC triggers (idempotente)
master-phoenix:      # apre Phoenix UI su http://localhost:6006
test-lineage:        # pytest tests/lineage/ con Neo4j reale
```

### 11.3 `pyproject.toml` — Extra Opzionale

```toml
[project.optional-dependencies]
master = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "neo4j>=5.0",
    "pydantic>=2.0",
    "arize-phoenix-otel>=0.6",
    "opentelemetry-sdk>=1.24",
    "opentelemetry-exporter-otlp-proto-grpc>=1.24",
    "openinference-instrumentation-fastapi>=0.1",
]
```

---

## 12. Testing e Simulazione

### 12.1 Struttura `tests/lineage/`

```
tests/lineage/
├── conftest.py              # Fixtures: Neo4j Docker, FastAPI TestClient
├── simulate_worker.py       # Simula training completo end-to-end
├── simulate_master.py       # Avvia master in subprocess (uvicorn)
├── test_handshake.py        # Tutti i casi: NEW, RESUME, BRANCH, RETRY
├── test_checkpoint_sync.py  # Push ckp, idempotenza, uri=NULL
├── test_config_change.py    # Modifica config → rilevamento branch
└── test_daemon_lifecycle.py # Avvio/stop/crash recovery daemon
```

### 12.2 `simulate_worker.py` — Flusso

1. Crea scaffold temporaneo in `tmp/`.
2. Avvia `daemon.py` come subprocess.
3. Emette eventi fake: `EXPERIMENT_STATUS:STARTED`, checkpoint ogni N secondi, `EXPERIMENT_STATUS:COMPLETED`.
4. Verifica che `lineage/worker_state.json` sia aggiornato correttamente.
5. Verifica che i metadati arrivino al Master tramite `GET /experiments/{exp_id}/lineage`.

### 12.3 Simulazione Branching

1. Primo handshake → `strategy: NEW`.
2. Modifica `config.yaml` nello scaffold temporaneo.
3. Secondo handshake (stesso daemon, nuova esecuzione) → `strategy: BRANCH`.
4. Verifica nel grafo: `(exp2)-[:DERIVED_FROM]->(exp1)`.

### 12.4 Cleanup dei Nodi di Test

I nodi di test vengono creati con la label aggiuntiva `_TEST` tramite header `X-Test-Run: true` nelle richieste. Cleanup:

```cypher
MATCH (n:_TEST) DETACH DELETE n;
```

---

## 13. Criticità e Soluzioni Architetturali

### 13.1 Checkpoint Eliminati (`uri = NULL`)

**Problema**: Checkpoint scartato per risparmio spazio (solo metriche preservate).

**Soluzione**:
- Il Worker invia il metadato al Master con `uri = NULL`.
- Il nodo `Checkpoint` esiste nel grafo (coerenza storica del lineage).
- La UI disabilita "Resume" e "Download" per nodi con `uri = NULL`.
- Le metriche sono comunque accessibili in `to_transfer/{exp_id}/checkpoints/results/{ckp_id}/`.

### 13.2 Sincronizzazione degli Orologi

**Problema**: Worker e Master hanno clock potenzialmente diversi.

**Soluzione**:
- Il Master usa il `timestamp_worker` (da `SyncEvent`) per l'analisi delle performance.
- Il Master usa il proprio timestamp di ricezione come riferimento di sistema.
- Entrambi vengono salvati nei nodi Neo4j (`created_at` = ricezione Master, `worker_ts` = timestamp Worker).

### 13.3 Inconsistenza dei Path URI

**Problema**: Lo stesso file ha path diversi su Worker, Master e NFS.

**Soluzione**: `URIResolver` + variabili d'ambiente. Ogni macchina ha un mapping `prefisso → path_base` nella propria `.env`. I path sono mai hardcodati nel codice.

### 13.4 Checkpoint Orfani

**Problema**: Un `Checkpoint` creato senza la relazione `PRODUCED` dal suo `Experiment`.

**Soluzione**: APOC trigger `validateCheckpointHasExperiment` (fase `before`) rifiuta la transazione se il constraint è violato. Eccezione: i checkpoint prodotti da `MERGED_FROM` non hanno necessariamente un `PRODUCED` diretto da un Experiment attivo — il trigger deve gestire questo caso.

> **⚠️ Agent Note**: Il trigger di validazione deve avere un'eccezione per i checkpoint con `is_merging = true`. Aggiustare il Cypher di conseguenza.

### 13.5 Relazioni Circolari nel Grafo

**Problema**: Un `Experiment` potrebbe accidentalmente derivare da sé stesso.

**Soluzione**: `ConsistencyGuard` nel Master valida che `source_exp_id != target_exp_id` in `DERIVED_FROM` e `RETRY_OF`. Aggiungere anche un check di profondità massima (es. max 50 livelli di derivazione) per prevenire query ricorsive illimitate.

### 13.6 Assenza di Trigger Nativi Neo4j

Neo4j non ha trigger nativi come SQL. APOC Procedures sono il meccanismo standard. Richiedono:
- `neo4j-apoc-core` nella configurazione plugins.
- `apoc.trigger.enabled=true` nella configurazione del database.
- Neo4j 5.x (alcune API APOC sono cambiate tra versioni).

---

## 14. Ordine di Implementazione Consigliato

L'ordine seguente rispetta le dipendenze tra i moduli e permette di validare ogni layer prima di costruire il successivo.

### Fase 1 — Fondamenta (Shared Layer)

```
1. envelope/middleware/shared/dataclasses.py    ← contratto dati (ExperimentNode aggiornato)
2. envelope/middleware/shared/hashing.py        ← ConfigHasher + ConfigSnapshot + DiffEngine
```

**Validazione**: unit test su hashing deterministico, serializzazione Pydantic, diff git-style su file di esempio.

### Fase 2 — Database Layer (Master Neo4j)

```
3. master/neo4j/schema.cypher                  ← constraints + indici
4. master/neo4j/triggers.cypher                ← APOC timestamp + validation
5. master/neo4j/client.py                      ← driver singleton
6. master/neo4j/repository.py                  ← query Cypher atomiche
```

**Validazione**: test con Neo4j Docker, verificare CRUD e idempotenza `upsert_checkpoint`. Verificare che i campi `config`, `train`, `rewards`, `requirements` siano salvati correttamente come property Neo4j.

### Fase 3 — Osservabilità (Phoenix)

```
7. master/observability/__init__.py
8. master/observability/tracing.py             ← setup_tracing() + get_tracer()
```

**Validazione**: `make master-up`, verificare che Phoenix UI sia accessibile su `localhost:6006`. Testare `setup_tracing()` con Phoenix down → deve fallire silenziosamente.

### Fase 4 — Master API

```
9.  master/api/lineage_controller.py           ← logica RESUME/BRANCH/RETRY/NEW
10. master/api/routes.py                       ← endpoint FastAPI + span manuali
11. master/api/app.py                          ← factory + middleware auth + startup tracing
12. master/docker-compose.yml + Dockerfile     ← infrastruttura (include Phoenix service)
```

**Validazione**: `make master-up`, test tutti gli endpoint con `httpx`. Verificare che le trace appaiano in Phoenix UI.

### Fase 5 — Storage Layer

```
13. master/storage/base.py                     ← ABC
14. master/storage/local.py                    ← LocalStorageWriter
15. master/storage/resolver.py                 ← URIResolver
16. master/storage/stubs/s3.py + nfs.py        ← stub futuri
```

### Fase 6 — Worker Layer

```
17. worker/connection/base.py                  ← ABC BaseConnection
18. worker/connection/http.py                  ← HTTPConnection
19. worker/connection/ssh.py                   ← SSHConnection
20. worker/local_persistence.py                ← WorkerState + atomic write
21. worker/fs_watcher.py                       ← watchdog (trigger: config.yaml, train.py, rewards/*)
22. worker/pusher.py                           ← coda asincrona
23. worker/daemon.py                           ← entry point + lettura testi file per HandshakeRequest
```

**Validazione**: `simulate_worker.py` contro Master locale. Verificare che le trace handshake e checkpoint push appaiano in Phoenix.

### Fase 7 — Integrazione Generator

```
24. envelope/generators/setup_generator.py     ← step 16: inject_worker_middleware()
25. envelope/generators/templates/run.sh.j2    ← daemon lifecycle
26. envelope/generators/templates/requirements.txt.j2
27. envelope/frameworks/capability_matrix.py   ← aggiunge 'merge'
28. envelope/generators/templates/merge.py.j2  ← template scaffold merge
```

**Validazione**: generare uno scaffold di test, verificare la struttura `lineage/` e il funzionamento di `run.sh`.

### Fase 8 — Test End-to-End

```
29. tests/lineage/conftest.py
30. tests/lineage/simulate_master.py
31. tests/lineage/simulate_worker.py
32. tests/lineage/test_handshake.py             ← include verifica diff_patch git-style
33. tests/lineage/test_checkpoint_sync.py
34. tests/lineage/test_config_change.py         ← verifica trigger hash (config/train/rewards)
35. tests/lineage/test_daemon_lifecycle.py
```

### Fase 9 — Bonus: Scaffold Merge

```
36. Scaffold setup_merge_{name}/ con daemon --one-shot
```

---

### Riepilogo Dipendenze tra Fasi

```
Fase 1 (Shared)
    └─▶ Fase 2 (DB)
            └─▶ Fase 3 (Phoenix)
                    └─▶ Fase 4 (Master API)
                                └─▶ Fase 5 (Storage)
Fase 1 (Shared)
    └─▶ Fase 6 (Worker)
                    └─▶ Fase 7 (Generator)
Fase 4 + Fase 6
    └─▶ Fase 8 (Test E2E)
Fase 6 + Fase 7
    └─▶ Fase 9 (Merge)
```

> **💡 Agent Workflow Tip**: Prima di avviare l'implementazione, verificare che `envelope/middleware/` non esista già (per evitare sovrascritture) e che `master/` non sia in conflitto con namespace Python esistenti nel progetto. Eseguire `find . -name "middleware" -type d` e `find . -name "master" -type d` come prime operazioni. Verificare anche che la porta `4317` (OTLP gRPC) non sia già in uso sulla macchina host prima di avviare il docker-compose.

## 15.  Update Documentation

Update with changes: 
- workflow.md
- README.md
- docs/*.md aggiungendo docs per nuovi moduli e iniettndo in quelli esistenti eventuali modifiche