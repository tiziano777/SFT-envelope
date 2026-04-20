# CLAUDE.md -- FineTuning-Envelope

## Project SCENARIO

### Architettura

Sistema di generazione setup per esperimenti di fine-tuning LLM riproducibili. Legge un file YAML e genera una cartella `setup_{name}/` autocontenuta con tutto il necessario per lanciare un training.

### Standard codice

- Python 3.10+ 
- Pydantic v2 per tutti i data model
- Type hints su tutte le funzioni pubbliche
- Click per CLI
- Rich per output formattato
- Jinja2 per template

### Conventions

- Ogni tecnica di training e' un plugin registrato via `@registry.register("name")`
- Ogni framework adapter implementa `BaseFrameworkAdapter` (ABC)
- Test con pytest, linting con ruff
- Configurazione via YAML, i default sono in `envelope/config/defaults.py`

### Comandi principali

```bash
envelope setup --name NAME --config CONFIG.yaml
envelope validate --config CONFIG.yaml
envelope techniques
envelope compatible TECHNIQUE
```

### File critici

| Path | Descrizione |
|------|-------------|
| `envelope/config/models.py` | Schema Pydantic (EnvelopeConfig) |
| `envelope/config/defaults.py` | Default iperparametri e per tecnica |
| `envelope/config/loader.py` | YAML loading + merge defaults |
| `envelope/config/validators.py` | Validazione cross-field |
| `envelope/generators/setup_generator.py` | Orchestratore generazione setup |
| `envelope/frameworks/capability_matrix.py` | Matrice tecnica x framework x infrastruttura |

### Project-Specific Guidelines

- TDD development
- Every imported package class or decorator can exists, not invent anything 
- Ask Questions about choices, especially when a tradeoff emerging
- Start from a object oriented style, from abstarction to implementations
- Ensure always the maximum modularity and extendability
- we have a .venv in the project to run tests and other commands
- You do not assume anithing, if some context is missing, ask for a deep explanation
- After every User story or stage, you have to test and update documentation of the project application, test the User story and checking for a refactoring
- Updating documentation requires to modify only the relevat documents between README.md, workflow.md and files in docs/*

# CLAUDE.md General Guidelines

Behavioral guidelines to reduce common LLM coding mistakes.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

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

