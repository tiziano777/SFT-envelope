🗺️ Struttura Completa del Progetto (esistente + nuovo)
FineTuning-Envelope/
│
├── envelope/                              # [ESISTENTE] Core del generatore
│   ├── cli.py                             # [ESISTENTE] Click CLI
│   ├── config/                            # [ESISTENTE] Pydantic v2 schema
│   │   ├── models.py
│   │   ├── defaults.py
│   │   ├── loader.py
│   │   └── validators.py
│   ├── registry/                          # [ESISTENTE] Plugin system
│   │   ├── base.py
│   │   └── __init__.py
│   ├── techniques/                        # [ESISTENTE] 19 plugin tecnica
│   │   ├── base.py
│   │   ├── sft/
│   │   ├── preference/
│   │   ├── rl/
│   │   ├── flow/
│   │   └── distillation/
│   ├── frameworks/                        # [ESISTENTE] 8 adapter framework
│   │   ├── base.py
│   │   ├── capability_matrix.py           # [MODIFICATO] aggiunge 'merge'
│   │   ├── single_node/
│   │   ├── multi_node/
│   │   └── from_scratch/
│   ├── generators/                        # [ESISTENTE + MODIFICATO]
│   │   ├── setup_generator.py             # [MODIFICATO] step 16: inject_worker_middleware()
│   │   └── templates/                     # [ESISTENTE + NUOVO]
│   │       ├── prepare.py.j2              # [ESISTENTE]
│   │       ├── train_grpo_trl.py.j2       # [ESISTENTE]
│   │       ├── train_sft_trl.py.j2        # [ESISTENTE]
│   │       ├── train_dpo_trl.py.j2        # [ESISTENTE]
│   │       ├── train_gkd_trl.py.j2        # [ESISTENTE]
│   │       ├── train_sdft_trl.py.j2       # [ESISTENTE]
│   │       ├── train_sdpo_trl.py.j2       # [ESISTENTE]
│   │       ├── train_gold_trl.py.j2       # [ESISTENTE]
│   │       ├── train_reward_modeling_trl.py.j2  # [ESISTENTE]
│   │       ├── run.sh.j2                  # [MODIFICATO] aggiunge daemon lifecycle
│   │       ├── requirements.txt.j2        # [MODIFICATO] aggiunge watchdog, httpx, paramiko
│   │       └── merge.py.j2                # [NUOVO] template per scaffold merge
│   ├── diagnostics/                       # [ESISTENTE]
│   ├── hardware/                          # [ESISTENTE]
│   │   ├── gpu_specs.py
│   │   └── auto_optimizer.py
│   │
│   └── middleware/                        # [NUOVO] moduli statici copiati negli scaffold
│       ├── shared/                        # [NUOVO] condiviso Worker ↔ Master
│       │   ├── __init__.py
│       │   ├── dataclasses.py             # Pydantic: tutti i nodi + relazioni + envelope
│       │   └── hashing.py                 # ConfigHasher + ConfigSnapshot
│       └── worker/                        # [NUOVO] copiato in ogni scaffold
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
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── app.py                         # FastAPI app factory
│   │   ├── routes.py                      # Tutti gli endpoint REST
│   │   ├── lineage_controller.py          # Logica RESUME/BRANCH/RETRY/NEW
│   │   └── middleware.py                  # API key auth (X-API-Key header)
│   ├── neo4j/
│   │   ├── __init__.py
│   │   ├── client.py                      # Driver Neo4j (singleton)
│   │   ├── repository.py                  # Tutte le query Cypher atomiche
│   │   ├── schema.cypher                  # Constraints + indici
│   │   └── triggers.cypher                # APOC triggers (created_at, updated_at, validation)
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── base.py                        # ABC BaseStorageWriter
│   │   ├── local.py                       # LocalStorageWriter (file:///)
│   │   ├── resolver.py                    # URIResolver: prefisso → writer
│   │   └── stubs/
│   │       ├── s3.py                      # Stub S3StorageWriter
│   │       └── nfs.py                     # Stub NFSStorageWriter
│   ├── docker-compose.yml                 # Neo4j + APOC + master-api
│   ├── Dockerfile                         # Image master-api
│   ├── .env.example                       # Template credenziali
│   └── requirements.txt                   # FastAPI, uvicorn, neo4j driver, pydantic
│
├── configs/                               # [ESISTENTE]
│   └── examples/
│
├── setups/                                # [GENERATO a runtime]
│   └── setup_{name}/                      # Output del generatore
│       ├── prepare.py                     # [ESISTENTE] generato da template
│       ├── train.py                       # [ESISTENTE] generato da template
│       ├── run.sh                         # [MODIFICATO] lancia daemon + train
│       ├── config.yaml                    # [ESISTENTE] frozen al momento generazione
│       ├── requirements.txt               # [MODIFICATO] include deps worker
│       ├── diagnostics.py                 # [ESISTENTE] copiato da envelope/diagnostics/
│       ├── rewards/                       # [ESISTENTE] solo per RL
│       │   ├── __init__.py
│       │   └── *.py
│       ├── worker/                        # [NUOVO] copiato da envelope/middleware/worker/
│       │   ├── __init__.py
│       │   ├── daemon.py
│       │   ├── local_persistence.py
│       │   ├── fs_watcher.py
│       │   ├── pusher.py
│       │   └── connection/
│       │       ├── __init__.py
│       │       ├── base.py
│       │       ├── http.py
│       │       └── ssh.py
│       ├── shared/                        # [NUOVO] copiato da envelope/middleware/shared/
│       │   ├── __init__.py
│       │   ├── dataclasses.py
│       │   └── hashing.py
│       └── lineage/                       # [NUOVO] creato a runtime dal daemon
│           ├── worker_state.json          # Stato persistente Worker (t → t+1)
│           ├── transfer_log.jsonl         # Audit trail append-only
│           ├── .handshake_done            # Flag: handshake OK → train.py può procedere
│           ├── .training_done             # Flag: train.py finito → daemon può fare flush+exit
│           ├── .exp_id                    # Una riga: exp_id corrente
│           ├── snapshots/                 # Freeze config ad ogni run
│           │   └── {snapshot_id}/
│           │       ├── config.yaml
│           │       ├── requirements.txt
│           │       └── manifest.json      # {file: sha256} + aggregated_hash
│           └── to_transfer/               # Staging area sync verso Master
│               └── {exp_id}/
│                   ├── config/
│                   ├── sw_requirements/
│                   ├── hw_requirements/
│                   ├── hw_metrics/
│                   ├── training_metrics/
│                   ├── rewards/
│                   └── checkpoints/
│                       ├── {ckp_id}/      # Pesi fisici
│                       └── results/
│                           └── {ckp_id}/ # Solo metriche, senza pesi
│
├── tests/                                 # [ESISTENTE + NUOVO]
│   ├── unit/                              # [ESISTENTE] 765 test
│   ├── integration/                       # [ESISTENTE]
│   └── lineage/                           # [NUOVO] test Master-Worker
│       ├── conftest.py                    # Fixtures: Neo4j Docker, FastAPI TestClient
│       ├── simulate_worker.py             # Simula training completo end-to-end
│       ├── simulate_master.py             # Avvia master in subprocess
│       ├── test_handshake.py              # NEW / RESUME / BRANCH / RETRY
│       ├── test_checkpoint_sync.py        # Push ckp, idempotenza, uri=NULL
│       ├── test_config_change.py          # Modifica config → branch detection
│       └── test_daemon_lifecycle.py       # Avvio/stop/crash recovery daemon
│
├── docs/                                  # [ESISTENTE + NUOVO]
│   ├── architecture.md                    # [ESISTENTE]
│   ├── config.md                          # [ESISTENTE]
│   ├── registry.md                        # [ESISTENTE]
│   ├── techniques.md                      # [ESISTENTE]
│   ├── frameworks.md                      # [ESISTENTE]
│   ├── from-scratch.md                    # [ESISTENTE]
│   ├── fsdp.md                            # [ESISTENTE]
│   ├── hardware.md                        # [ESISTENTE]
│   ├── generator.md                       # [ESISTENTE]
│   ├── diagnostics.md                     # [ESISTENTE]
│   ├── distillation.md                    # [ESISTENTE]
│   └── lineage.md                         # [NUOVO] Master-Worker architecture doc
│
├── Makefile                               # [MODIFICATO] aggiunge target master-*
└── pyproject.toml                         # [MODIFICATO] aggiunge dipendenze opzionali master

Modifiche chirurgiche ai file esistenti
Solo questi file esistenti vengono toccati, tutto il resto è addizione pura:
File Tipo modifica Cosa cambia 

envelope/generators/setup_generator.py Addizione Step 16: inject_worker_middleware() copia middleware/worker/ e middleware/shared/ nello scaffold

envelope/generators/templates/run.sh.j2 Modifica Aggiunge blocco daemon lifecycle prima e dopo {{ launch_command }}

envelope/generators/templates/requirements.txt.j2 Modifica Aggiunge watchdog, httpx, paramiko alla lista requirements

envelope/frameworks/capability_matrix.py Addizione Aggiunge entry merge come tecnica speciale no-GPU

Makefile Addizione Target master-up, master-down, master-logs, master-init-db, test-lineage

pyproject.toml Addizione Extra opzionale [master]: fastapi, uvicorn, neo4j driver