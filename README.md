# FineTuning-Envelope

Sistema di generazione setup per esperimenti di fine-tuning LLM riproducibili. Legge un file YAML di configurazione e genera una cartella autocontenuta con tutto il necessario per lanciare un training.

```
YAML config ──> [envelope] ──> setup_myexp/
                                    ├── prepare.py
                                    ├── train.py
                                    ├── run.sh
                                    ├── config.yaml
                                    └── requirements.txt
```

## Architettura

Legge un file YAML e genera una cartella `setup_{name}/` autocontenuta con tutto il necessario per lanciare un training. Ogni setup include `prepare.py` (preparazione dataset con caching idempotente) e `train.py` (loop di training). Supporta 19 tecniche di training, 8 framework backend, PEFT (LoRA/QLoRA/DoRA/RSLoRA), quantizzazione (NF4/INT8/GPTQ/AWQ/FP8), hardware-aware optimization e un'architettura a plugin estensibile.

## Tecniche supportate

| Stage | Tecnica | Descrizione |
|-------|---------|-------------|
| SFT | `sft` | Supervised Fine-Tuning |
| Preference | `dpo` | Direct Preference Optimization |
| Preference | `simpo` | Simple Preference Optimization (reference-free) |
| Preference | `kto` | Kahneman-Tversky Optimization |
| Preference | `orpo` | Odds Ratio Preference Optimization (reference-free) |
| Preference | `reward_modeling` | Reward Model Training |
| RL | `ppo` | Proximal Policy Optimization |
| RL | `grpo` | Group Relative Policy Optimization |
| RL | `dapo` | Decoupled Alignment via Policy Optimization |
| RL | `vapo` | Value-Augmented Policy Optimization |
| RL | `rloo` | REINFORCE Leave-One-Out |
| RL | `reinforce_pp` | REINFORCE++ |
| RL | `dr_grpo` | Dr. GRPO (bias-corrected) |
| RL | `flowrl` | FlowRL (distribution matching) |
| RL | `prime` | PRIME (process implicit rewards) |
| Distillation | `gkd` | Generalized Knowledge Distillation |
| Distillation | `sdft` | Self-Distilled Fine-Tuning |
| Distillation | `sdpo` | Self-Distilled Preference Optimization |
| Distillation | `gold` | Generalized Online Distillation |

## Framework backend

| Framework | Tipo | Tecniche supportate |
|-----------|------|---------------------|
| TRL | Single-node | sft, dpo, simpo, kto, orpo, grpo, ppo, rloo, gkd, sdft, sdpo, gold, reward_modeling |
| Unsloth | Single-node | sft, dpo, simpo, orpo, grpo |
| Axolotl | Single-node | sft, dpo |
| Torchtune | Single-node | sft, dpo |
| **From Scratch** | **PyTorch raw** | **tutte le 19 tecniche** |
| veRL | Multi-node | grpo, ppo, dapo, vapo, reinforce_pp, dr_grpo, flowrl, prime |
| OpenRLHF | Multi-node | sft, dpo, grpo, ppo, rloo, reinforce_pp |
| LlamaFactory | Multi-node | sft, dpo, kto, orpo |

> **From Scratch** (`from_scratch`): genera training loop in PyTorch puro con classi ABC estendibili e supporto opzionale per Triton kernels. E' l'unico backend con copertura completa su tutte le tecniche. Vedi [`docs/from-scratch.md`](docs/from-scratch.md).

## Matrice infrastruttura

Ogni framework supporta diversi livelli di integrazione con i tre pilastri di ottimizzazione:

| Framework | Triton (Single GPU) | FSDP (Cluster GPU) | SkyPilot (Cloud) |
|-----------|--------------------|--------------------|------------------|
| TRL | Partial (via FlashAttn) | **Full** (via Accelerate) | Full |
| Unsloth | **Native** (core) | None (single GPU) | Full |
| Axolotl | Partial (via FlashAttn 2) | **Full** (via Accelerate) | Full |
| Torchtune | **Native** (via torchao) | Internal (FSDP2 nativo) | Full |
| From Scratch | **Native** (TritonOp) | **Full** (BaseFromScratchTrainer) | Full |
| veRL | Partial (via vLLM) | Internal (via Ray) | Partial |
| OpenRLHF | Partial (via vLLM) | None (usa DeepSpeed) | Full |
| LlamaFactory | Partial (via FlashAttn) | **Full** (via Accelerate) | Full |

> Per la documentazione completa su FSDP vedi [`docs/fsdp.md`](docs/fsdp.md).

## Quick Start

### Installazione

```bash
# Crea un virtual environment
uv venv --python 3.10 .venv
source .venv/bin/activate

# Installa il progetto
uv pip install -e ".[dev]"
```

### Primo setup

1. Scrivi (o modifica) un file YAML di configurazione:

```yaml
# configs/examples/grpo_qlora_qwen.yaml
experiment:
  name: "grpo-qlora-qwen-math"
  description: "GRPO with QLoRA on Qwen2.5-7B"
  tags: ["grpo", "qlora", "math"]

model:
  name_or_path: "Qwen/Qwen2.5-7B-Instruct"
  trust_remote_code: true
  max_seq_length: 2048

training:
  technique: "grpo"
  peft:
    method: "qlora"
    r: 32
    lora_alpha: 64
    target_modules: ["q_proj", "k_proj", "v_proj", "o_proj"]
  precision:
    compute_dtype: "bf16"
    quantization: "nf4"
  technique_args:
    num_generations: 16
    max_completion_length: 512
    epsilon: 0.2
    beta: 0.04

dataset:
  train_uri: "argilla/magpie-ultra-v1.0"
  format: "rl"

reward:
  type: "verifiable"
  functions:
    - name: "math_correctness"
      module_path: "rewards.math_verify"
      weight: 1.0

hardware:
  gpu_type: "A100-80GB"
  gpu_count: 1

framework:
  backend: "trl"
```

2. Genera il setup:

```bash
make setup NAME=grpo-math-v1 CONFIG=configs/examples/grpo_qlora_qwen.yaml
```

oppure:

```bash
envelope setup --name grpo-math-v1 --config configs/examples/grpo_qlora_qwen.yaml
```

3. Prepara i dati ed esegui il training:

```bash
cd setups/setup_grpo-math-v1
pip install -r requirements.txt
python prepare.py    # Scarica e cachea il dataset in ./data_cache/
bash run.sh          # train.py importa da prepare.py, non ri-scarica i dati
```

### Comandi CLI

```bash
# Valida un config senza generare file
envelope validate --config configs/examples/grpo_qlora_qwen.yaml

# Lista tutte le tecniche registrate
envelope techniques

# Lista tutti i framework registrati
envelope frameworks

# Mostra i framework compatibili con una tecnica
envelope compatible grpo
```

### Comandi Make

```bash
make setup NAME=my-exp CONFIG=path/to/config.yaml    # Genera setup
make validate CONFIG=path/to/config.yaml               # Valida config
make techniques                                        # Lista tecniche
make frameworks                                        # Lista framework
make compatible TECHNIQUE=grpo                         # Compatibilita'
make test                                              # Esegui test
make lint                                              # Linting
make format                                            # Formattazione
```

## Integrazione esterna

I setup generati espongono un protocollo standard che consente a tool esterni (sweep engine, coding agent, script custom) di sovrascrivere iperparametri e leggere i risultati.

**Override iperparametri**: `train.py` legge variabili d'ambiente `HPARAM_*` a runtime. Qualunque iperparametro nel config puo' essere sovrascritto:

```bash
HPARAM_LEARNING_RATE=3e-5 HPARAM_PER_DEVICE_TRAIN_BATCH_SIZE=4 bash run.sh
```

**Risultati strutturati**: `train.py` emette metriche su stdout in formato parsabile:

```
EXPERIMENT_RESULT:{"reward_mean": 0.72, "loss": 1.23, "accuracy": 0.85}
```

Questo permette a qualsiasi orchestratore di lanciare esperimenti parametrizzati e raccogliere i risultati in modo programmatico, senza modificare i file del setup.

## Struttura del progetto

```
FineTuning-Envelope/
├── envelope/                    # Setup ecosystem
│   ├── cli.py                   # Click CLI
│   ├── config/                  # Pydantic v2 schema, loader, validators
│   │   ├── models.py            # Tutti i modelli (ExperimentConfig, ModelConfig, PrepareConfig, ...)
│   │   ├── defaults.py          # Default per tecnica e iperparametri
│   │   ├── loader.py            # YAML loading + merge defaults
│   │   └── validators.py        # Cross-field validation
│   ├── registry/                # Plugin system
│   │   ├── base.py              # Registry[T] generico
│   │   └── __init__.py          # Istanze singleton + discover_plugins()
│   ├── techniques/              # Plugin per tecnica di training
│   │   ├── base.py              # ABC BaseTechnique
│   │   ├── sft/                 # SFT
│   │   ├── preference/          # DPO, SimPO, KTO, ORPO, Reward Modeling
│   │   ├── rl/                  # GRPO, PPO, DAPO, VAPO, RLOO, REINFORCE++, Dr.GRPO
│   │   ├── flow/                # FlowRL, PRIME
│   │   └── distillation/        # GKD, SDFT, SDPO, GOLD
│   ├── frameworks/              # Adapter per framework di training
│   │   ├── base.py              # ABC BaseFrameworkAdapter
│   │   ├── capability_matrix.py # Matrice tecnica x framework
│   │   ├── single_node/         # TRL, Unsloth, Axolotl, Torchtune
│   │   ├── multi_node/          # veRL, OpenRLHF, LlamaFactory
│   │   └── from_scratch/        # PyTorch raw + ABC ontology + Triton kernels
│   ├── generators/              # Generazione setup directory
│   │   ├── setup_generator.py   # Orchestratore principale
│   │   └── templates/           # Template Jinja2 (prepare.py, train.py, run.sh, requirements.txt)
│   ├── diagnostics/             # Diagnostica runtime (copiata nei setup)
│   └── hardware/                # GPU specs + auto-optimizer
│       ├── gpu_specs.py         # Database GPU (A100, H100, H200, L40S, ...)
│       └── auto_optimizer.py    # Suggerimenti automatici
│
├── configs/
│   └── examples/                # Configurazioni di esempio
│
├── tests/                       # 765 test (pytest)
│   ├── unit/                    # Test per ogni modulo
│   └── integration/             # Test end-to-end
│
├── docs/                        # Documentazione approfondita
├── Makefile                     # Comandi principali
└── pyproject.toml               # Build config (hatchling)
```

## Estensibilita'

### Aggiungere una nuova tecnica

1. Crea un file in `envelope/techniques/<stage>/`:

```python
from envelope.registry import technique_registry
from envelope.techniques.base import BaseTechnique

@technique_registry.register("my_technique")
class MyTechnique(BaseTechnique):
    @property
    def name(self) -> str:
        return "my_technique"

    @property
    def stage(self) -> Stage:
        return Stage.RL

    @property
    def display_name(self) -> str:
        return "My Custom Technique"

    def default_technique_args(self):
        return {"my_param": 0.5}

    def validate_technique_args(self, args):
        errors = []
        if args.get("my_param", 0) < 0:
            errors.append("my_param must be >= 0")
        return errors

    def required_dataset_fields(self):
        return ["prompt"]
```

2. Aggiungi l'import nel `__init__.py` della sotto-cartella
3. Aggiungi l'entry nella `TECHNIQUE_STAGE_MAP` in `models.py`
4. Aggiungi le combinazioni nella `capability_matrix.py`
5. Aggiungi i default in `defaults.py`

### Aggiungere un nuovo framework

1. Crea un adapter in `envelope/frameworks/<scope>/`:

```python
from envelope.registry import framework_registry
from envelope.frameworks.base import BaseFrameworkAdapter

@framework_registry.register("my_framework")
class MyFrameworkAdapter(BaseFrameworkAdapter):
    # ... implementa template_name, requirements, template_context, etc.
```

2. Aggiungi l'import nel `__init__.py`
3. Aggiungi le combinazioni nella `capability_matrix.py`
4. Crea i template Jinja2 in `envelope/generators/templates/`

## Test

```bash
# Tutti i test
make test

# Test con coverage
pytest tests/ -v --cov=envelope

# Solo unit test
pytest tests/unit/ -v

# Solo integration
pytest tests/integration/ -v
```

## Documentazione

La documentazione approfondita di ogni modulo si trova in [`docs/`](docs/):

- [`docs/architecture.md`](docs/architecture.md) -- Panoramica architetturale
- [`docs/config.md`](docs/config.md) -- Sistema di configurazione (modelli, loader, validatori)
- [`docs/registry.md`](docs/registry.md) -- Pattern Registry e sistema plugin
- [`docs/techniques.md`](docs/techniques.md) -- Tecniche di training
- [`docs/frameworks.md`](docs/frameworks.md) -- Framework adapter e matrice di compatibilita'
- [`docs/from-scratch.md`](docs/from-scratch.md) -- Backend From Scratch: PyTorch raw, ontologia ABC, Triton kernels, FSDP distribuito
- [`docs/fsdp.md`](docs/fsdp.md) -- FSDP: configurazione, strategie, framework supportati, troubleshooting
- [`docs/hardware.md`](docs/hardware.md) -- Hardware specs e auto-optimizer
- [`docs/generator.md`](docs/generator.md) -- Generatore di setup e template Jinja2
- [`docs/diagnostics.md`](docs/diagnostics.md) -- Runtime diagnostics: regole, integrazione, estensibilita'
- [`docs/distillation.md`](docs/distillation.md) -- Tecniche di distillazione (GKD, SDFT, SDPO, GOLD)

## Licenza

TODO
