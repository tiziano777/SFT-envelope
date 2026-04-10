# Requirements: FineTuning-Envelope Lineage System

**Defined:** 2026-04-10
**Core Value:** Ogni esperimento e' tracciabile, riproducibile e collegato ai suoi predecessori senza azioni manuali.

## v1 Requirements

Requirements for the lineage system milestone. Each maps to roadmap phases.

### Shared Layer

- [x] **SHRD-01**: Pydantic dataclass per tutti i nodi Neo4j (RecipeNode, ModelNode, ExperimentNode, CheckpointNode, ComponentNode)
- [x] **SHRD-02**: Enum RelationType per tutte le 8 relazioni del grafo
- [x] **SHRD-03**: DerivedFromRel model con diff_patch strutturato
- [x] **SHRD-04**: Envelope operativi Worker→Master (HandshakeRequest, HandshakeResponse, CheckpointPush, SyncEvent)
- [x] **SHRD-05**: Strategy enum (NEW, RESUME, BRANCH, RETRY)
- [x] **SHRD-06**: ConfigHasher calcola SHA256 deterministico su file trigger (config.yaml, train.py, rewards/*)
- [x] **SHRD-07**: ConfigSnapshot serializzabile con aggregated_hash
- [x] **SHRD-08**: DiffEngine produce diff git-style (line, type, content) tra snapshot
- [x] **SHRD-09**: requirements.txt incluso nel diff testuale ma escluso dal trigger hash

### Database Layer

- [ ] **DB-01**: Schema Neo4j con constraints UNIQUE su recipe_id, exp_id, ckp_id, model_name, component composite
- [ ] **DB-02**: APOC trigger per timestamp automatico (created_at, updated_at) su tutti i nodi
- [ ] **DB-03**: APOC trigger per validazione checkpoint orfani (eccezione is_merging=true)
- [ ] **DB-04**: Driver Neo4j singleton con connection pooling
- [ ] **DB-05**: ExperimentRepository con query Cypher atomiche (create, derived, retry, upsert checkpoint)
- [ ] **DB-06**: find_experiment_by_hashes idempotente per handshake
- [ ] **DB-07**: get_latest_checkpoint per logica RESUME
- [ ] **DB-08**: create_merged_checkpoint con N relazioni MERGED_FROM

### Observability

- [ ] **OBSV-01**: Phoenix tracing setup idempotente (setup_tracing() con fallback silenzioso)
- [ ] **OBSV-02**: get_tracer() con no-op fallback se OTEL non installato
- [ ] **OBSV-03**: Phoenix come servizio Docker nel docker-compose.yml
- [ ] **OBSV-04**: Span manuali su endpoint critici (handshake, checkpoint_push, status_update, merge, sync_event)
- [ ] **OBSV-05**: auto_instrument=True per FastAPI (no double-instrumentation)

### Master API

- [ ] **MAPI-01**: POST /handshake — handshake bloccante con LineageController
- [ ] **MAPI-02**: POST /experiments/{exp_id}/checkpoints — upsert checkpoint idempotente
- [ ] **MAPI-03**: PATCH /experiments/{exp_id}/status — aggiorna stato esperimento
- [ ] **MAPI-04**: POST /experiments/{exp_id}/events — log evento generico
- [ ] **MAPI-05**: POST /checkpoints/merge — merge N checkpoint
- [ ] **MAPI-06**: GET /experiments/{exp_id}/lineage — grafo completo esperimento
- [ ] **MAPI-07**: GET /health — status check Neo4j + storage
- [ ] **MAPI-08**: X-API-Key middleware per autenticazione
- [ ] **MAPI-09**: LineageController implementa matrice decisionale handshake (4 strategie)
- [ ] **MAPI-10**: ConsistencyGuard previene relazioni circolari (source != target, max depth 50)

### Storage Layer

- [ ] **STOR-01**: BaseStorageWriter ABC (write, read, exists)
- [ ] **STOR-02**: LocalStorageWriter per schema file:///
- [ ] **STOR-03**: URIResolver dispatcha ai writer per prefisso (file://, s3://, nfs://, worker://, master://)
- [ ] **STOR-04**: Stub S3StorageWriter e NFSStorageWriter
- [ ] **STOR-05**: URI prefix mapping da .env (non hardcodato)

### Worker Layer

- [ ] **WRKR-01**: BaseConnection ABC (connect, send_metadata, transfer_file, disconnect, is_alive)
- [ ] **WRKR-02**: HTTPConnection con httpx sync
- [ ] **WRKR-03**: SSHConnection con paramiko
- [ ] **WRKR-04**: WorkerState JSON persistente con atomic write (tmp + rename)
- [ ] **WRKR-05**: transfer_log.jsonl append-only audit trail
- [ ] **WRKR-06**: Filesystem watcher (watchdog) su lineage/to_transfer/, training_metrics/, config/rewards
- [ ] **WRKR-07**: AsyncPusher con coda thread-safe, retry esponenziale, idempotenza event_id
- [ ] **WRKR-08**: Daemon entry point con handshake bloccante + .handshake_done + .exp_id
- [ ] **WRKR-09**: Daemon monitora .training_done poi flush_and_stop()
- [ ] **WRKR-10**: Timeout handshake configurabile (default 30s) con degraded mode

### Generator Integration

- [ ] **GENR-01**: inject_worker_middleware() copia worker/ e shared/ nello scaffold
- [ ] **GENR-02**: run.sh.j2 esteso con daemon lifecycle (avvio, handshake wait, training_done, flush)
- [ ] **GENR-03**: requirements.txt.j2 aggiunge watchdog, httpx, paramiko
- [ ] **GENR-04**: merge.py.j2 template per scaffold merge con daemon --one-shot
- [ ] **GENR-05**: capability_matrix aggiunge 'merge' come tecnica speciale no-GPU

### Datamix

- [ ] **DMIX-01**: Sezione datamix multi-source nel config.yaml (sources con uri, replica, samples, dist_name, chat_type)
- [ ] **DMIX-02**: DatamixLoader adattivo in prepare.py (rileva datamix vs dataset)
- [ ] **DMIX-03**: Replica come oversampling intero (repeat dataset N volte)
- [ ] **DMIX-04**: Backward compatibility con struttura dataset singola

### Infrastructure

- [ ] **INFR-01**: Dockerfile per master-api
- [ ] **INFR-02**: docker-compose.yml con Neo4j + Phoenix + master-api
- [ ] **INFR-03**: .env.example con tutte le variabili
- [ ] **INFR-04**: Makefile target master-up, master-down, master-logs, master-logs-phoenix, master-init-db, test-lineage
- [ ] **INFR-05**: pyproject.toml extra [master] con FastAPI, uvicorn, neo4j, phoenix deps

### Testing

- [ ] **TEST-01**: conftest.py con fixture Neo4j Docker e FastAPI TestClient
- [ ] **TEST-02**: simulate_worker.py — simula training completo E2E
- [ ] **TEST-03**: simulate_master.py — avvia master in subprocess
- [ ] **TEST-04**: test_handshake.py — tutti i casi (NEW, RESUME, BRANCH, RETRY) con verifica diff_patch
- [ ] **TEST-05**: test_checkpoint_sync.py — push ckp, idempotenza, uri=NULL
- [ ] **TEST-06**: test_config_change.py — modifica config → rilevamento branch, trigger hash (config/train/rewards)
- [ ] **TEST-07**: test_daemon_lifecycle.py — avvio/stop/crash recovery
- [ ] **TEST-08**: Nodi test con label _TEST, cleanup via DETACH DELETE

### Documentation

- [ ] **DOCS-01**: Aggiornare workflow.md con fasi lineage
- [ ] **DOCS-02**: Aggiornare README.md con sezione lineage system
- [ ] **DOCS-03**: Aggiornare docs/ esistenti con modifiche ai moduli (generator, frameworks)
- [ ] **DOCS-04**: Nuovo doc per moduli lineage (middleware, master)

## v2 Requirements

### Advanced Storage

- **STOR-V2-01**: S3StorageWriter concreto con boto3
- **STOR-V2-02**: NFSStorageWriter concreto
- **STOR-V2-03**: Transfer policy configurabile per checkpoint (ALL, BEST_ONLY, SKIP)

### UI & Visualization

- **UI-V2-01**: Dashboard web per navigazione grafo lineage
- **UI-V2-02**: Visualizzazione diff tra esperimenti
- **UI-V2-03**: Timeline view degli esperimenti

### Advanced Features

- **ADV-V2-01**: Multi-tenancy con namespace isolati
- **ADV-V2-02**: OAuth/JWT autenticazione avanzata
- **ADV-V2-03**: Webhook notifications per stato esperimenti
- **ADV-V2-04**: CI/CD pipeline per deploy automatico master

## Out of Scope

| Feature | Reason |
|---------|--------|
| S3/NFS writer concreti | Alta complessita' infra, stub sufficienti per v1 |
| UI/dashboard custom | Phoenix UI copre observability base |
| Multi-tenancy | Singolo team/progetto per deployment |
| OAuth/JWT auth | X-API-Key sufficiente per rete interna |
| Real-time streaming eventi | Fire-and-forget con retry copre il caso d'uso |
| JAX support | Ecosistema incompatibile (transformers, PEFT, bitsandbytes sono PyTorch-only) |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SHRD-01..09 | Phase 1 | Pending |
| DB-01..08 | Phase 2 | Pending |
| OBSV-01..05 | Phase 3 | Pending |
| MAPI-01..10 | Phase 4 | Pending |
| INFR-01..05 | Phase 4 | Pending |
| STOR-01..05 | Phase 5 | Pending |
| WRKR-01..10 | Phase 6 | Pending |
| GENR-01..05 | Phase 7 | Pending |
| DMIX-01..04 | Phase 8 | Pending |
| TEST-01..08 | Phase 9 | Pending |
| DOCS-01..04 | Phase 10 | Pending |

**Coverage:**
- v1 requirements: 73 total
- Mapped to phases: 73
- Unmapped: 0

---
*Requirements defined: 2026-04-10*
*Last updated: 2026-04-10 after roadmap phase mapping*
