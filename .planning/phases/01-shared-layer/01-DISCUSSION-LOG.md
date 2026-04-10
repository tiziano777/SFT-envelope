# Phase 1: Shared Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-10
**Phase:** 1-Shared Layer
**Areas discussed:** Module layout, Model base pattern, Hash determinism, Serialization format

---

## Module Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Split per dominio | nodes.py, relations.py, envelopes.py, config_hasher.py, diff_engine.py — file piccoli e focalizzati | ✓ |
| File consolidati | Un unico models.py + utils.py — simile a config/models.py esistente | |
| You decide | Lascia decidere a Claude | |

**User's choice:** Split per dominio (Recommended)
**Notes:** None

---

## Model Base Pattern

| Option | Description | Selected |
|--------|-------------|----------|
| BaseNode condiviso | BaseNode(BaseModel) con id, created_at, updated_at. I 5 nodi ereditano da essa. | ✓ |
| Plain BaseModel separati | Ogni nodo definisce i propri campi indipendentemente | |
| You decide | Lascia decidere a Claude | |

**User's choice:** BaseNode condiviso (Recommended)
**Notes:** None

---

## Hash Determinism

| Option | Description | Selected |
|--------|-------------|----------|
| Raw file bytes ordinati | Legge file binari, ordina per nome, concatena e hash | |
| Parse + normalize | YAML: parse + json.dumps(sorted). Python: normalizza line endings, strip trailing whitespace | ✓ |
| You decide | Lascia decidere a Claude | |

**User's choice:** Parse + normalize (Recommended)
**Notes:** None

---

## Serialization Format

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic nativo | .model_dump_json() / .model_validate_json() nativo, FastAPI out-of-the-box | ✓ |
| Envelope protocol custom | Protocollo custom con header type/version + payload JSON | |
| You decide | Lascia decidere a Claude | |

**User's choice:** Pydantic nativo con estensibilita' — aggiungere `headers: dict[str, str]` su tutti gli envelope per metadata futuri
**Notes:** L'utente ha chiesto esplicitamente di rendere il formato gia' flessibile con un campo headers dict per simulare estensioni future (routing, versioning, custom metadata)

---

## Claude's Discretion

- Exact field types and names per node/relation (follow architecture doc)
- DiffEngine algorithm internals
- `__init__.py` re-export structure
- Whether to add a BaseRelation model

## Deferred Ideas

None
