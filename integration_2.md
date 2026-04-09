AI Experiment Lineage System
Visione d'insieme
FineTuning-Envelope (esistente)
│
├── envelope/                        ← MODIFICATO: aggiunta middleware/
│   └── middleware/                  ← NUOVO: moduli statici copiati negli scaffold
│       ├── worker/                  ← Worker layer
│       └── shared/                  ← Dataclass condivise Worker↔Master
│
├── master/                          ← NUOVO: servizio indipendente deployabile
│   ├── api/                         ← FastAPI
│   ├── neo4j/                       ← Schema, APOC triggers, queries
│   ├── storage/                     ← URI resolver + writer astratto
│   └── docker-compose.yml           ← Neo4j + APOC + Master API
│
└── setups/setup_{name}/             ← MODIFICATO: scaffold arricchito
    ├── train.py                     ← invariato (emette EXPERIMENT_STATUS/RESULT)
    ├── run.sh                       ← MODIFICATO: lancia daemon prima di train
    ├── config.yaml                  ← frozen al momento della generazione
    ├── requirements.txt
    ├── rewards/
    ├── worker/                      ← NUOVO: copiato da envelope/middleware/worker/
    │   ├── __init__.py
    │   ├── daemon.py                ← Sync Daemon (processo separato)
    │   ├── local_persistence.py     ← Manifest + snapshot stato
    │   ├── fs_watcher.py            ← Watchdog sul filesystem
    │   ├── pusher.py                ← Coda asincrona verso Master
    │   └── connection/              ← Layer connessione astratto
    │       ├── base.py              ← ABC BaseConnection
    │       ├── http.py              ← HTTPConnection (per test locali)
    │       └── ssh.py               ← SSHConnection (produzione)
    ├── shared/                      ← NUOVO: copiato da envelope/middleware/shared/
    │   ├── __init__.py
    │   ├── dataclasses.py           ← Pydantic: Experiment, Checkpoint, Recipe...
    │   └── hashing.py               ← Hash config/requirements/hyperparams
    └── lineage/                     ← NUOVO: creato a runtime dal daemon
        ├── worker_state.json        ← Stato persistente del worker
        ├── snapshots/               ← Copia frozen di config+req ad ogni run
        │   └── {snapshot_id}/
        │       ├── config.yaml
        │       ├── requirements.txt
        │       └── manifest.json    ← Hash di tutti i file al momento snapshot
        └── to_transfer/             ← Staging area per sync verso master
            └── {exp_id}/
                ├── config/
                ├── sw_requirements/
                ├── hw_requirements/
                ├── hw_metrics/
                ├── training_metrics/
                ├── rewards/
                └── checkpoints/
                    ├── {ckp_id}/    ← pesi fisici
                    └── results/
                        └── {ckp_id}/ ← solo metriche, senza pesi

FASE 1 — Shared Layer (envelope/middleware/shared/)
Obiettivo: dataclass Pydantic condivise tra Worker e Master. Zero dipendenze esterne oltre a Pydantic.
1.1 dataclasses.py
Nodi Neo4j mappati come Pydantic models:
RecipeNode         → fields da SQL schema + config_yaml (str)
ModelNode          → id, model_name, version, uri, url, architecture_info_ref...
ExperimentNode     → exp_id, model_id, status, exit_status, hash_committed_code,
                     sw_requirements_json, hyperparams_json, config_json,
                     metrics_uri, hw_metrics_uri, usable, manual_save...
CheckpointNode     → ckp_id, epoch, run, metrics_snapshot, uri, is_usable, is_merging
ComponentNode      → technique_code, framework_code, docs_url
Relazioni come enum + dataclass:
RelationType       → USED_FOR, SELECTED_FOR, BASED_ON, PRODUCED,
                     DERIVED_FROM, STARTED_FROM, RETRY_OF, MERGED_FROM
DerivedFromRel     → source_exp_id, target_exp_id, diff_patch (JSON)
Envelope operativi:
HandshakeRequest   → config_hash, hyperparams_hash, req_hash, code_hash,
                     checkpoint_id_to_resume (Optional), scaffold_path
HandshakeResponse  → exp_id, strategy (RESUME|BRANCH|RETRY|NEW),
                     base_checkpoint_uri (Optional)
CheckpointPush     → exp_id, ckp_id, epoch, run, metrics_snapshot,
                     uri, is_usable, transfer_policy
SyncEvent          → event_type, payload, timestamp_worker, exp_id
1.2 hashing.py
pythonclass ConfigHasher:
    @staticmethod
    def hash_file(path: Path) -> str          # SHA256 singolo file
    
    @staticmethod
    def hash_config(scaffold_dir: Path) -> ConfigSnapshot:
        # SHA256 di config.yaml + requirements.txt + ogni file in rewards/
        # Ritorna ConfigSnapshot con hash per file + hash aggregato
    
    @staticmethod  
    def diff_snapshots(old: ConfigSnapshot, new: ConfigSnapshot) -> dict
        # Ritorna {file: (old_hash, new_hash)} per file cambiati
ConfigSnapshot è una Pydantic model serializzabile in JSON — viene salvata in lineage/snapshots/.

FASE 2 — Worker Layer (envelope/middleware/worker/)
2.1 connection/base.py — ABC
pythonclass BaseConnection(ABC):
    @abstractmethod
    def connect(self) -> bool: ...
    
    @abstractmethod
    def send_metadata(self, endpoint: str, payload: dict) -> dict: ...
    
    @abstractmethod
    def transfer_file(
        self, 
        local_path: Path, 
        remote_path: str,
        policy: TransferPolicy = TransferPolicy.ALL  # enum: ALL, BEST_ONLY, SKIP
    ) -> bool: ...
    
    @abstractmethod
    def disconnect(self) -> None: ...
    
    @abstractmethod
    def is_alive(self) -> bool: ...
2.2 connection/http.py e connection/ssh.py
HTTPConnection: usa httpx (sync), endpoint base da env var MASTER_URL.
SSHConnection: usa paramiko, hostname/user/key da env vars MASTER_SSH_*. send_metadata → esegue curl sul master via SSH. transfer_file → scp/rsync via paramiko.SFTPClient.
2.3 local_persistence.py
Gestisce lineage/worker_state.json. Struttura:
json{
  "scaffold_dir": "/path/to/setup_grpo-math-v1",
  "current_exp_id": "uuid-or-null",
  "current_run": 0,
  "strategy": "NEW|RESUME|BRANCH|RETRY",
  "config_snapshot": { ...ConfigSnapshot... },
  "pending_events": [],
  "last_synced_at": "ISO8601",
  "handshake_done": false,
  "transfer_log": []
}
Ogni modifica allo stato:

Aggiorna il dict in memoria
Scrive atomicamente su disco (tmp + rename)
Appende a lineage/transfer_log.jsonl (append-only audit trail)

Metodi chiave:
pythondef load_or_init(scaffold_dir: Path) -> WorkerState
def save(state: WorkerState) -> None           # atomic write
def record_event(state, event: SyncEvent)      # append to pending
def mark_sent(state, event_id: str)            # rimuove da pending
def take_snapshot(state, scaffold_dir) -> str  # snapshot_id
2.4 fs_watcher.py
Usa watchdog. Monitora:

lineage/to_transfer/ → nuovo file = nuovo evento da pushare
training_metrics/ → append su file di log = evento incrementale
config.yaml, requirements.txt, rewards/ → cambiamento = potenziale branch

Emette eventi in una queue.Queue thread-safe consumata dal daemon.
2.5 pusher.py
Coda di invio con retry. Non bloccante per il training.
pythonclass AsyncPusher:
    def __init__(self, connection: BaseConnection, state: WorkerState)
    def enqueue(self, event: SyncEvent) -> None
    def run_forever(self, stop_event: threading.Event) -> None
        # loop: drain queue → send → on failure: requeue con backoff
        # idempotenza: ogni evento ha event_id univoco
        # il Master ignora duplicati (stesso event_id)
    def flush_and_stop(self) -> None
        # attende che la coda si svuoti, poi setta stop_event
2.6 daemon.py — Entry point del processo separato
python# Chiamato da run.sh PRIMA di train.py
# Argomenti: --scaffold-dir PATH --master-url URL --connection-type http|ssh

def main():
    # 1. Carica/inizializza worker_state
    # 2. Calcola ConfigSnapshot corrente
    # 3. Confronta con snapshot precedente (se esiste)
    #    → se diverso: registra diff come pending BRANCH event
    # 4. HANDSHAKE bloccante con Master
    #    → riceve exp_id + strategy
    #    → salva in worker_state
    #    → segnala al train.py via file di coordinamento (lineage/.handshake_done)
    # 5. Avvia fs_watcher
    # 6. Avvia AsyncPusher in thread
    # 7. Loop principale: consuma eventi da fs_watcher → pusher.enqueue()
    # 8. Monitora lineage/.training_done (scritto da train.py alla fine)
    # 9. Quando training_done: flush_and_stop(), disconnect(), exit(0)
File di coordinamento (dentro lineage/):

.handshake_done → scritto dal daemon dopo handshake OK, letto da train.py
.training_done → scritto da train.py alla fine, letto dal daemon per sapere quando terminare
.exp_id → una riga con l'exp_id corrente, letto da train.py per i log


FASE 3 — Master Layer (master/)
3.1 master/neo4j/schema_and_triggers.cypher
Constraints e indici:
cypherCREATE CONSTRAINT recipe_id IF NOT EXISTS FOR (r:Recipe) REQUIRE r.recipe_id IS UNIQUE;
CREATE CONSTRAINT experiment_id IF NOT EXISTS FOR (e:Experiment) REQUIRE e.exp_id IS UNIQUE;
CREATE CONSTRAINT checkpoint_id IF NOT EXISTS FOR (c:Checkpoint) REQUIRE c.ckp_id IS UNIQUE;
CREATE CONSTRAINT model_name IF NOT EXISTS FOR (m:Model) REQUIRE m.model_name IS UNIQUE;
APOC trigger per created_at/updated_at (pattern da community con UNION ALL anti-loop):
cypherCALL apoc.trigger.install('neo4j', 'setNodeCreatedAndUpdated', '
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
APOC validation guard (esempio per ckp orfano):
cypherCALL apoc.trigger.install('neo4j', 'validateCheckpointHasExperiment', '
  UNWIND $createdNodes AS n
  WITH n WHERE "Checkpoint" IN labels(n)
  CALL apoc.util.validate(
    NOT EXISTS { MATCH (e:Experiment)-[:PRODUCED]->(n) },
    "Checkpoint %s must have a PRODUCED relationship from an Experiment",
    [n.ckp_id]
  )
  RETURN n
', {phase: "before"});
3.2 master/neo4j/repository.py
pythonclass ExperimentRepository:
    # Tutte le query Cypher atomiche
    
    def create_experiment(self, exp: ExperimentNode, 
                          recipe_id: str, model_id: str) -> str
    
    def create_derived_experiment(self, base_exp_id: str, 
                                   new_exp: ExperimentNode,
                                   diff_patch: dict,
                                   start_ckp_id: Optional[str]) -> str
    # Crea in una sola transazione:
    # (new_exp)-[:DERIVED_FROM {diff_patch}]->(base_exp)
    # Se start_ckp_id: (new_exp)-[:STARTED_FROM]->(ckp)
    
    def create_retry_experiment(self, base_exp_id: str, 
                                 new_exp: ExperimentNode) -> str
    # (new_exp)-[:RETRY_OF]->(base_exp)
    
    def upsert_checkpoint(self, ckp: CheckpointNode) -> str
    # Idempotente: MERGE su ckp_id, poi SET proprietà
    
    def create_merged_checkpoint(self, source_ckp_ids: list[str],
                                  new_ckp: CheckpointNode) -> str
    # Crea nuovo ckp + N relazioni MERGED_FROM
    
    def find_experiment_by_hashes(self, config_hash: str,
                                   hyperparams_hash: str,
                                   req_hash: str,
                                   code_hash: str) -> Optional[ExperimentNode]
    
    def get_latest_checkpoint(self, exp_id: str) -> Optional[CheckpointNode]
    
    def update_experiment_status(self, exp_id: str, 
                                  status: str, exit_status: Optional[str])
3.3 master/api/lineage_controller.py
Il "cervello" che implementa la logica di branching:
pythonclass LineageController:
    def process_handshake(self, req: HandshakeRequest) -> HandshakeResponse:
        existing = repo.find_experiment_by_hashes(
            req.config_hash, req.hyperparams_hash, 
            req.req_hash, req.code_hash
        )
        
        if existing and req.checkpoint_id_to_resume:
            last_ckp = repo.get_latest_checkpoint(existing.exp_id)
            if last_ckp and last_ckp.ckp_id == req.checkpoint_id_to_resume:
                # RESUME: stesso hash, stesso ultimo ckp
                return HandshakeResponse(exp_id=existing.exp_id, 
                                         strategy=Strategy.RESUME, ...)
        
        if existing and not req.checkpoint_id_to_resume:
            # RETRY: stesso hash, parte da zero
            new_exp = ... # crea ExperimentNode
            exp_id = repo.create_retry_experiment(existing.exp_id, new_exp)
            return HandshakeResponse(exp_id=exp_id, strategy=Strategy.RETRY)
        
        if not existing and req.checkpoint_id_to_resume:
            # BRANCH: hash diverso, parte da un ckp
            new_exp = ...
            diff = compute_diff(req)  # diff_patch JSON
            exp_id = repo.create_derived_experiment(
                req.base_exp_id, new_exp, diff, req.checkpoint_id_to_resume
            )
            return HandshakeResponse(exp_id=exp_id, strategy=Strategy.BRANCH, ...)
        
        # NEW: primo esperimento
        exp_id = repo.create_experiment(new_exp, req.recipe_id, req.model_id)
        return HandshakeResponse(exp_id=exp_id, strategy=Strategy.NEW)
3.4 master/api/routes.py — FastAPI
POST /handshake                → LineageController.process_handshake()
POST /experiments/{exp_id}/checkpoints   → repo.upsert_checkpoint()
PATCH /experiments/{exp_id}/status       → repo.update_experiment_status()
POST /experiments/{exp_id}/events        → log evento generico
POST /checkpoints/merge                  → repo.create_merged_checkpoint()
GET  /experiments/{exp_id}/lineage       → query grafo completa
GET  /health                             → status Neo4j + storage
3.5 master/storage/ — URI resolver + Writer astratto
pythonclass BaseStorageWriter(ABC):
    @abstractmethod
    def write(self, local_path: Path, uri: str) -> str: ...  # ritorna URI finale
    
    @abstractmethod
    def read(self, uri: str) -> bytes: ...
    
    @abstractmethod
    def exists(self, uri: str) -> bool: ...

class LocalStorageWriter(BaseStorageWriter):
    # uri: "file:///abs/path/to/file"
    # copia il file nella directory configurata del master

class URIResolver:
    # Legge prefisso URI e dispatcha al writer corretto
    # file:///  → LocalStorageWriter
    # s3://     → S3StorageWriter (stub per ora)
    # nfs://    → NFSStorageWriter (stub per ora)
3.6 master/docker-compose.yml
yamlservices:
  neo4j:
    image: neo4j:5.x
    environment:
      NEO4J_PLUGINS: '["apoc"]'
      NEO4J_apoc_trigger_enabled: "true"
      NEO4J_apoc_uuid_enabled: "true"
    volumes:
      - neo4j_data:/data
      - ./neo4j/init:/var/lib/neo4j/import  # schema + triggers al primo avvio
  
  master-api:
    build: .
    depends_on: [neo4j]
    env_file: .env
    ports:
      - "8000:8000"

volumes:
  neo4j_data:
Script di init Neo4j (neo4j/init/01_schema.cypher, 02_triggers.cypher) eseguiti al primo avvio tramite entrypoint.

FASE 4 — Integrazione nel Generator
4.1 Modifiche a setup_generator.py
Aggiungere step 16 alla pipeline:
python16. inject_worker_middleware()
    # Copia envelope/middleware/worker/ → setup_*/worker/
    # Copia envelope/middleware/shared/ → setup_*/shared/
    # Crea setup_*/lineage/.gitkeep (placeholder)
    # Aggiunge worker deps a requirements.txt (watchdog, httpx, paramiko)
4.2 Modifiche al template run.sh.j2
bash#!/bin/bash
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
TIMEOUT=30
ELAPSED=0
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
4.3 Scaffold merge (technique: merge)
Genera uno scaffold minimale:
setup_merge_{name}/
├── merge.py          # Script one-shot: carica ckp, esegue mergekit, salva
├── config.yaml       # Lista URI ckp + metodo merge (slerp, ties, dare...)
├── requirements.txt  # mergekit
├── worker/           # Copiato come sempre
├── shared/
└── lineage/
merge.py alla fine esegue il one-shot push: crea lineage/to_transfer/{new_ckp_id}/ con i metadati del checkpoint merged e chiama daemon.py --one-shot (modalità senza watcher, solo push e exit).

FASE 5 — Test Locale con FastAPI
Struttura test
tests/lineage/
├── conftest.py              # Fixtures: Neo4j reale (Docker), Master FastAPI client
├── test_handshake.py        # Tutti i casi: NEW, RESUME, BRANCH, RETRY
├── test_checkpoint_sync.py  # Push ckp, idempotenza, uri=NULL
├── test_config_change.py    # Simula modifica config → rilevamento branch
├── test_daemon_lifecycle.py # Daemon avvio/stop, recovery da crash
├── simulate_worker.py       # Script standalone: simula training completo
└── simulate_master.py       # Avvia Master FastAPI in processo separato
simulate_worker.py: crea uno scaffold temporaneo, avvia daemon, emette eventi fake (EXPERIMENT_STATUS:STARTED, checkpoint ogni N secondi, EXPERIMENT_STATUS:COMPLETED), verifica che il worker_state.json sia aggiornato correttamente e che i metadati arrivino al Master.
simulate_master.py: avvia uvicorn master.api:app in subprocess, espone su localhost:8000.
Il test simula anche il branching: modifica config.yaml nello scaffold temporaneo dopo il primo handshake, rilancia il daemon, verifica che nel grafo esista (exp2)-[:DERIVED_FROM]->(exp1).
Cleanup finale: cancella tutti i nodi con label _TEST da Neo4j (i nodi di test vengono creati con questa label aggiuntiva tramite header X-Test-Run: true nelle richieste).

Makefile — Nuovi comandi
makefilemake master-up        # docker-compose up (Neo4j + Master API)
make master-down      # docker-compose down
make master-logs      # log del master API
make master-init-db   # applica schema + APOC triggers al Neo4j
make test-lineage     # esegui tests/lineage/ con Neo4j reale

Ordine di implementazione
1. shared/dataclasses.py + shared/hashing.py         [fondamenta]
2. master/neo4j/repository.py + schema.cypher        [DB layer]
3. master/api/ (routes + lineage_controller)          [Master API]
4. master/docker-compose.yml + init scripts          [infrastruttura]
5. worker/connection/base.py + http.py + ssh.py      [connessione]
6. worker/local_persistence.py                       [stato locale]
7. worker/fs_watcher.py                              [eventi FS]
8. worker/pusher.py                                  [invio asincrono]
9. worker/daemon.py                                  [entry point]
10. Modifica setup_generator.py + run.sh.j2          [integrazione]
11. tests/lineage/ (simulate_worker + simulate_master)[test locale]
12. Scaffold merge (technique: merge)                [bonus]