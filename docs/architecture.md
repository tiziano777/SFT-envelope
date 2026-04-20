# Architettura

## Panoramica

FineTuning-Envelope e' un sistema di generazione setup per il fine-tuning di modelli, guidato da configurazione YAML.

```
                           ┌─────────────────────────────────────────┐
                           │           YAML Config (.yaml)           │
                           └────────────────┬────────────────────────┘
                                            │
                                            ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                              envelope/                                    │
│                                                                           │
│  ┌──────────┐   ┌──────────┐   ┌───────────┐   ┌────────────────────┐     │
│  │  config/ │──>│ registry/│──>│generators/│──>│  setup_{name}/     │     │
│  │          │   │          │   │           │   │  ├── prepare.py    │     │
│  │ models   │   │ technique│   │ templates │   │  ├── train.py      │     │
│  │ loader   │   │ framework│   │ (Jinja2)  │   │  ├── run.sh        │     │
│  │ defaults │   │          │   │           │   │  ├── config.yaml   │     │
│  │ validate │   └──────────┘   └───────────┘   │  └── requirements  │     │
│  └──────────┘         │                        └────────────────────┘     │
│                       │   ┌──────────┐   ┌──────────┐                     │
│                       ├──>│techniques│   │ hardware/│                     │
│                       │   │ 19 plugin│   │ gpu_specs│                     │
│                       │   └──────────┘   │ auto_opt │                     │
│                       │   ┌──────────┐   └──────────┘                     │
│                       └──>│frameworks│                                    │
│                           │ 8 adapter│                                    │
│                           └──────────┘                                    │
└───────────────────────────────────────────────────────────────────────────┘
```

### Punti di integrazione esterna

I setup generati supportano un protocollo standard per l'integrazione con tool esterni (orchestratori, script di automazione, pipeline CI/CD):

- **Input -- variabili d'ambiente `HPARAM_*`**: qualsiasi tool esterno puo' iniettare override di iperparametri a runtime settando variabili d'ambiente con prefisso `HPARAM_`. Il `train.py` generato le legge e sovrascrive i valori di default.
- **Output -- `EXPERIMENT_RESULT:{json}` su stdout**: al termine del training, lo script emette una riga strutturata con le metriche dell'esperimento. Qualsiasi tool di orchestrazione puo' parsare questa riga per raccogliere risultati.

Questo protocollo rende i setup generati interoperabili con qualsiasi sistema di hyperparameter search, senza dipendenze aggiuntive.

## Principi di design

### D1: YAML-first

Ogni aspetto dell'esperimento e' definito in un unico file YAML. Non ci sono parametri hardcoded nel codice di generazione. La configurazione e' tipizzata con Pydantic v2, con validazione automatica e default intelligenti.

### D2: Plugin architecture

Tecniche e framework sono plugin registrati tramite un decoratore `@registry.register("name")`. Aggiungere una nuova tecnica o un nuovo framework richiede solo un file Python + una riga nell'`__init__.py`. Nessuna modifica al core.

### D3: Protocollo HPARAM per tool esterni

I setup generati espongono un'interfaccia standard basata su variabili d'ambiente (`HPARAM_*`) e output strutturato (`EXPERIMENT_RESULT:{json}`). Questo permette di interagire con i setup senza conoscere i dettagli interni del training script.

### D4: Immutabilita' dei setup

Una volta generata, la cartella `setup_*` e' immutabile. Gli override di iperparametri avvengono solo a runtime tramite env vars. L'unica eccezione e' `data_cache/`, creata a runtime da `prepare.py` per il caching idempotente dei dataset.

### D5: Riproducibilita'

Ogni setup contiene un `config.yaml` frozen che cattura l'intera configurazione usata per la generazione. Insieme al protocollo `HPARAM_*`, questo garantisce che ogni esperimento sia completamente riproducibile: basta rieseguire lo stesso setup con le stesse variabili d'ambiente.

### D6: Hardware-aware

Il sistema conosce le specifiche tecniche delle GPU (VRAM, compute capability, supporto BF16/FP8) e suggerisce automaticamente ottimizzazioni appropriate: precisione, quantizzazione, gradient checkpointing, flash attention, DeepSpeed.

### D7: Infrastruttura locale-first

L'architettura e' focalizzata su esecuzione locale. I setup generati sono directory autocontenute che possono essere eseguiti su qualsiasi macchina con le dipendenze installate, senza bisogno di servizi esterni o infrastruttura cloud.

### D8: Template-driven

I file di training sono generati tramite template Jinja2 (`train_{technique}_{framework}.py.j2`). Questo permette massima flessibilita': ogni combinazione tecnica x framework puo' avere il suo template ottimizzato.

## Flusso dati completo

### Dalla YAML al setup

```
1. YAML file
   │
2. load_yaml() ─── Parsing YAML
   │
3. merge_technique_defaults() ─── Merge default per tecnica
   │
4. inject_hparam_defaults() ─── Inietta default iperparametri
   │
5. EnvelopeConfig.model_validate() ─── Validazione Pydantic
   │
6. validate_config_or_raise() ─── Validazione cross-field
   │
7. Resolve technique plugin ─── Registry lookup
   │
8. Resolve framework adapter ─── Registry lookup
   │
9. check_or_raise() ─── Verifica compatibilita'
   │
10. suggest_optimizations() ─── Suggerimenti HW
    │
11. Jinja2 render ─── prepare.py, train.py, run.sh, requirements.txt
    │
12. dump_config() ─── config.yaml frozen
    │
13. Copy diagnostics.py ─── Modulo diagnostica runtime
    │
14. setup_{name}/ ─── Directory autocontenuta
```

## Dipendenze

### Runtime
- `pydantic>=2.0` -- Schema validation
- `pyyaml>=6.0` -- YAML parsing
- `jinja2>=3.1` -- Template rendering
- `click>=8.0` -- CLI
- `rich>=13.0` -- Output formatting

### Development
- `pytest>=8.0`
- `pytest-cov>=5.0`
- `ruff>=0.4`
