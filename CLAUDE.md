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
- Neo4j for tracking storage

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

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
|------|----------|
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.

## Best Practices

- TDD development
- Ask Questions about choices, especially when a tradeoff emerging
- Start from a object oriented style, from abstarction to implementations
- Ensure always the maximum modularity and extendability
- we have a .venv in the project to run tests and other commands
- You do not assume anithing, if some context is missing, ask for a deep explanation
- After every User story or stage, you have to test and update documentation of the project application, test the User story and checking for a refactoring
- Updating documentation requires to modify only the relevat documents between README.md, workflow.md and files in docs/*