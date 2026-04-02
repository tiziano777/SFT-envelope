# CLAUDE.md -- FineTuning-Envelope

## Architettura

Sistema di generazione setup per esperimenti di fine-tuning LLM riproducibili. Legge un file YAML e genera una cartella `setup_{name}/` autocontenuta con tutto il necessario per lanciare un training.

Le directory `setup_*` sono **immutabili** una volta generate. Gli iperparametri possono essere sovrascritti a runtime tramite variabili d'ambiente `HPARAM_*`.

## Standard codice

- Python 3.10+ (`X | Y` union syntax, non `Union[X, Y]`)
- Pydantic v2 per tutti i data model
- Type hints su tutte le funzioni pubbliche
- Click per CLI
- Rich per output formattato
- Jinja2 per template

## Convenzioni

- Ogni tecnica di training e' un plugin registrato via `@registry.register("name")`
- Ogni framework adapter implementa `BaseFrameworkAdapter` (ABC)
- Test con pytest, linting con ruff
- Configurazione via YAML, i default sono in `envelope/config/defaults.py`

## Comandi principali

```bash
envelope setup --name NAME --config CONFIG.yaml
envelope validate --config CONFIG.yaml
envelope techniques
envelope compatible TECHNIQUE
```

## File critici

| Path | Descrizione |
|------|-------------|
| `envelope/config/models.py` | Schema Pydantic (EnvelopeConfig) |
| `envelope/config/defaults.py` | Default iperparametri e per tecnica |
| `envelope/config/loader.py` | YAML loading + merge defaults |
| `envelope/config/validators.py` | Validazione cross-field |
| `envelope/generators/setup_generator.py` | Orchestratore generazione setup |
| `envelope/frameworks/capability_matrix.py` | Matrice tecnica x framework x infrastruttura |
