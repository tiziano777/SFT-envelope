# FineTuning-Envelope — Lineage System

## What This Is

Un sistema di tracciamento lineage per esperimenti AI che estende FineTuning-Envelope (generatore di scaffold per fine-tuning LLM) con un layer di tracking distribuito. Registra ogni esperimento, checkpoint e relazione di derivazione in un grafo Neo4j, funzionando su macchine separate (GPU worker ↔ DB master) con comunicazione asincrona. Si integra nel generatore esistente senza romperlo: ogni nuovo scaffold include automaticamente il middleware Worker.

## Core Value

Ogni esperimento di fine-tuning e' tracciabile, riproducibile e collegato ai suoi predecessori — senza richiedere azioni manuali dall'utente oltre al lancio del training.

## Requirements

### Validated

- ✓ Setup generator produce scaffold autocontenuti (19 tecniche, 8 framework) — existing
- ✓ Plugin system con registry decorator-based per tecniche e framework — existing
- ✓ Config YAML-first con validazione Pydantic v2 e cross-field validation — existing
- ✓ Hardware-aware optimization suggestions — existing
- ✓ Runtime diagnostics con warning strutturati — existing
- ✓ FSDP multi-GPU support — existing
- ✓ From-scratch backend con Triton kernels — existing
- ✓ HPARAM_* env var override protocol — existing
- ✓ Immutable setup directories — existing

### Active

- [ ] Shared layer: Pydantic dataclass per nodi Neo4j, relazioni, envelope operativi
- [ ] Shared layer: ConfigHasher + ConfigSnapshot + DiffEngine git-style
- [ ] Master: Neo4j schema con constraints, indici e APOC triggers
- [ ] Master: Repository con query Cypher atomiche (CRUD, idempotenza)
- [ ] Master: FastAPI service con handshake protocol e endpoint REST
- [ ] Master: LineageController con logica branching (NEW/RESUME/BRANCH/RETRY)
- [ ] Master: Storage layer astratto con URIResolver (file://, s3://, nfs://, worker://, master://)
- [ ] Master: OpenTelemetry + Phoenix tracing (span manuali su endpoint critici)
- [ ] Master: Docker Compose (Neo4j + Phoenix + Master API)
- [ ] Worker: BaseConnection ABC + HTTPConnection + SSHConnection
- [ ] Worker: Local persistence atomica (WorkerState + transfer_log.jsonl)
- [ ] Worker: Filesystem watcher (watchdog) su config/train/rewards
- [ ] Worker: AsyncPusher con coda, retry esponenziale, idempotenza
- [ ] Worker: Daemon process (handshake bloccante + fire-and-forget sync)
- [ ] Generator: inject_worker_middleware() come step 16
- [ ] Generator: run.sh.j2 con daemon lifecycle (handshake wait + training_done signal)
- [ ] Generator: requirements.txt.j2 con watchdog/httpx/paramiko
- [ ] Generator: merge.py.j2 scaffold per mergekit
- [ ] Generator: capability_matrix entry 'merge' come tecnica no-GPU
- [ ] Datamix: sezione datamix multi-source nel config.yaml
- [ ] Datamix: DatamixLoader adattivo in prepare.py (datamix vs dataset singolo)
- [ ] Testing: suite E2E (simulate_worker, simulate_master, test_handshake, test_branching)
- [ ] Infra: Makefile target master-*, pyproject.toml extra [master]
- [ ] Docs: update workflow.md, README.md, docs/*.md con sezioni lineage

### Out of Scope

- S3/NFS storage writer concreti — solo stub, implementazione completa in futuro
- UI/dashboard per visualizzazione grafo — Phoenix UI copre l'osservabilita' base
- Autenticazione avanzata — solo X-API-Key header per ora
- Multi-tenancy — singolo tenant (un progetto = un deployment)
- CI/CD pipeline — deployment manuale via docker-compose

## Context

### Codebase esistente (brownfield)

FineTuning-Envelope e' un progetto maturo con ~4500 righe Python. Il core e' stabile:
- 19 tecniche di training registrate come plugin
- 8 framework adapter (TRL, Unsloth, Axolotl, Torchtune, veRL, OpenRLHF, LlamaFactory, From Scratch)
- Capability matrix 19x9 che gate le combinazioni valide
- Pipeline setup_generator in 17 step (Load → Validate → Render → Copy)
- Test suite con unit test (8 file) e integration test (1 file)

### Architettura target

Due macchine:
- **Worker (GPU)**: esegue training, emette eventi tramite daemon in background
- **Master (CPU)**: riceve eventi, scrive su Neo4j, serve FastAPI

Il Worker non attende il Master dopo l'handshake: scrive localmente e sincronizza in background. Il protocollo di trasporto e' astratto (SSH produzione, HTTP test locali).

### Documento di architettura

Tutto il design dettagliato e' in `LINEAGE_SYSTEM_ARCHITECTURE.md` (1677 righe). Include:
- Data model Neo4j completo (5 nodi, 8 relazioni, constraints, APOC triggers)
- Protocollo handshake con matrice decisionale 4 strategie
- Worker daemon lifecycle con file di coordinamento
- Master API con 7 endpoint REST
- Storage layer con 5 schemi URI
- OpenTelemetry + Phoenix per osservabilita'
- Docker Compose per deployment
- Ordine di implementazione in 9 fasi con dipendenze

## Constraints

- **Tech stack**: Python 3.10+, Pydantic v2, FastAPI, Neo4j 5.x, APOC plugin — come da architettura
- **Chirurgical modification**: solo 6 file esistenti vengono modificati, tutto il resto e' aggiunta pura
- **Backward compatibility**: scaffold generati senza lineage devono continuare a funzionare
- **Graceful degradation**: se il Master non e' raggiungibile, il training procede senza lineage (warning)
- **No breaking changes**: la struttura dataset singola rimane come fallback per compatibilita'

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Neo4j come graph DB per lineage | Relazioni di derivazione/branching/merge sono naturalmente un grafo | — Pending |
| Architettura a 2 macchine (Worker + Master) | Worker GPU non deve avere Neo4j; Master centralizza il tracking | — Pending |
| Handshake bloccante + sync fire-and-forget | Unica operazione bloccante minimizza impatto sul training time | — Pending |
| APOC triggers per timestamp/validation | Neo4j non ha trigger nativi; APOC e' standard | — Pending |
| Phoenix come OTEL collector | Fornisce UI gratis per trace visualization + auto-instrument FastAPI | — Pending |
| Datamix multi-source con replica | Recipe definisce il data mix, lo scaffold lo consuma | — Pending |
| Transport astratto (HTTP/SSH) | Test locali con HTTP, produzione con SSH | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-10 after initialization*
