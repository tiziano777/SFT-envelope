# Frameworks -- Adapter e matrice di compatibilita'

> `envelope/frameworks/`

Ogni framework di training e' implementato come adapter che traduce un `EnvelopeConfig` in file specifici per quel framework: template Jinja2, requisiti pip, e comandi di lancio.

## File

| File | Responsabilita' |
|------|----------------|
| `base.py` | ABC `BaseFrameworkAdapter` |
| `capability_matrix.py` | Matrice tecnica x framework |
| `single_node/trl_adapter.py` | HuggingFace TRL |
| `single_node/unsloth_adapter.py` | Unsloth |
| `single_node/axolotl_adapter.py` | Axolotl |
| `single_node/torchtune_adapter.py` | Torchtune |
| `multi_node/verl_adapter.py` | veRL |
| `multi_node/openrlhf_adapter.py` | OpenRLHF |
| `multi_node/llamafactory_adapter.py` | LlamaFactory |
| `from_scratch/fromscratch_adapter.py` | From Scratch (PyTorch raw) -- vedi [`docs/from-scratch.md`](from-scratch.md) |

## ABC: `BaseFrameworkAdapter`

```python
class BaseFrameworkAdapter(ABC):
    # Proprieta' (abstract)
    name: str                          # Identificatore (es. "trl")
    display_name: str                  # Nome leggibile (es. "HuggingFace TRL")

    # Metodi (abstract)
    template_name(technique) -> str           # Nome template Jinja2
    requirements(config) -> list[str]         # Dipendenze pip
    template_context(config) -> dict          # Contesto per template

    # Metodi (con default)
    launch_command(config) -> str             # Comando shell (default: "python train.py")
    validate_config(config) -> list[str]      # Validazione framework-specifica
    extra_setup_files(config, output_dir)     # Copia file extra nel setup (default: no-op)
```

## Dettaglio per framework

### Single-node

#### TRL (`trl`)

La reference implementation. Supporta il maggior numero di tecniche.

| Campo | Valore |
|-------|--------|
| **Template pattern** | `train_{technique}_trl.py.j2` |
| **Launch command** | `python train.py` (1 GPU), `accelerate launch --num_processes {n} train.py` (multi-GPU) |
| **Tecniche** | sft, dpo, simpo, kto, orpo, grpo, ppo, rloo, gkd, sdft, sdpo, gold, reward_modeling |
| **Dipendenze base** | `torch>=2.1`, `trl>=1.0.0`, `transformers>=4.40`, `datasets>=2.18`, `accelerate>=0.30` |
| **Dipendenze condizionali** | `peft>=0.11` (se PEFT), `bitsandbytes>=0.43` (se NF4/INT8), `flash-attn>=2.5` (se flash attention), `wandb>=0.16` (se report_to=wandb), `vllm>=0.6` (se vllm_rollout) |

#### Unsloth (`unsloth`)

Ottimizzato per speed su singola GPU con kernel custom.

| Campo | Valore |
|-------|--------|
| **Template pattern** | `train_{technique}_unsloth.py.j2` |
| **Launch command** | `python train.py` |
| **Tecniche** | sft, dpo, simpo, orpo, grpo |
| **Dipendenze** | `torch>=2.1`, `unsloth>=2024.8`, `trl>=0.9` |
| **Limitazioni** | Non supporta PPO, RLOO, REINFORCE++, Dr.GRPO. Solo singola GPU. |

#### Axolotl (`axolotl`)

Framework basato su config YAML.

| Campo | Valore |
|-------|--------|
| **Template pattern** | `train_{technique}_axolotl.yaml.j2` (genera YAML, non Python) |
| **Launch command** | `accelerate launch -m axolotl.cli.train config.yaml` |
| **Tecniche** | sft, dpo |
| **Dipendenze** | `torch>=2.1`, `axolotl>=0.4`, `transformers>=4.40`, `datasets>=2.18`, `accelerate>=0.30` |

#### Torchtune (`torchtune`)

Framework PyTorch-nativo di Meta.

| Campo | Valore |
|-------|--------|
| **Template pattern** | `train_{technique}_torchtune.py.j2` |
| **Launch command** | `tune run lora_finetune_single_device --config config.yaml` (1 GPU), `tune run --nproc_per_node {n} lora_finetune_distributed --config config.yaml` (multi-GPU) |
| **Tecniche** | sft, dpo |
| **Dipendenze** | `torch>=2.1`, `torchtune>=0.2`, `torchao>=0.1` |

### Multi-node

#### veRL (`verl`)

Framework specializzato per RL training su larga scala. Unico framework che supporta DAPO, VAPO, FlowRL, PRIME.

| Campo | Valore |
|-------|--------|
| **Template pattern** | `train_{technique}_verl.py.j2` |
| **Launch command** | `python train.py` (1 GPU), `torchrun --nproc_per_node {n} train.py` (multi-GPU), `torchrun --nproc_per_node {n_per_node} --nnodes {nodes} train.py` (multi-node) |
| **Tecniche** | grpo, ppo, dapo, vapo, reinforce_pp, dr_grpo, flowrl, prime |
| **Dipendenze** | `torch>=2.1`, `verl>=0.2`, `vllm>=0.6`, `transformers>=4.40` |
| **Limitazioni** | Non supporta SFT (usa TRL per SFT). |
| **Validazione** | Verifica che il `technique` sia RL. |

#### OpenRLHF (`openrlhf`)

Framework RL open-source con buon supporto multi-nodo.

| Campo | Valore |
|-------|--------|
| **Template pattern** | `train_{technique}_openrlhf.py.j2` |
| **Launch command** | `python train.py` (1 GPU), `deepspeed --num_gpus {n} train.py` (multi-GPU con DeepSpeed) |
| **Tecniche** | sft, dpo, grpo, ppo, rloo, reinforce_pp |
| **Dipendenze** | `torch>=2.1`, `openrlhf>=0.4`, `deepspeed>=0.14`, `transformers>=4.40` |

#### LlamaFactory (`llamafactory`)

Interfaccia unificata per 100+ LLM.

| Campo | Valore |
|-------|--------|
| **Template pattern** | `train_{technique}_llamafactory.yaml.j2` (genera config YAML) |
| **Launch command** | `llamafactory-cli train config.yaml` |
| **Tecniche** | sft, dpo, kto, orpo |
| **Dipendenze** | `torch>=2.1`, `llamafactory>=0.8`, `transformers>=4.40`, `datasets>=2.18` |

### From Scratch

#### From Scratch (`from_scratch`)

Training PyTorch raw con ontologia ABC estendibile. L'unico backend con copertura completa su tutte le 19 tecniche. Documentazione completa in [`docs/from-scratch.md`](from-scratch.md).

| Campo | Valore |
|-------|--------|
| **Template pattern** | `train_fromscratch.py.j2` (singolo template parametrico) |
| **Launch command** | `python train.py` (1 GPU), `torchrun --nproc_per_node {n} train.py` (multi-GPU) |
| **Tecniche** | **tutte le 19** (sft, dpo, simpo, kto, orpo, grpo, ppo, dapo, vapo, rloo, reinforce_pp, dr_grpo, flowrl, prime, gkd, sdft, sdpo, gold, reward_modeling) |
| **Dipendenze base** | `torch>=2.1`, `transformers>=4.40`, `datasets>=2.18`, `accelerate>=0.30` |
| **Dipendenze condizionali** | `peft>=0.11` (se PEFT), `triton>=3.0` (se triton_kernels), `flash-attn>=2.5` (se flash attention), `bitsandbytes>=0.43` (se quantizzazione) |
| **Extra** | Copia `lib/` nel setup come package locale `fromscratch/` (training loop + ABC + Triton kernels) |

## Capability Matrix -- `capability_matrix.py`

Matrice booleana `(technique, framework) -> bool` che definisce quali combinazioni sono supportate.

### Matrice completa

```
              trl  unsloth  axolotl  torchtune  verl  openrlhf  llamafactory  nemo  from_scratch
sft            x      x       x         x        -       x          x          x        x
dpo            x      x       x         x        -       x          x          x        x
simpo          x      x       -         -        -       -          -          -        x
kto            x      -       -         -        -       -          x          -        x
orpo           x      x       -         -        -       -          x          -        x
grpo           x      x       -         -        x       x          -          -        x
ppo            x      -       -         -        x       x          -          x        x
dapo           -      -       -         -        x       -          -          -        x
vapo           -      -       -         -        x       -          -          -        x
rloo           x      -       -         -        -       x          -          -        x
reinforce_pp   -      -       -         -        x       x          -          -        x
dr_grpo        -      -       -         -        x       -          -          -        x
flowrl         -      -       -         -        x       -          -          -        x
prime          -      -       -         -        x       -          -          -        x
gkd            x      -       -         -        -       -          -          -        -
sdft           x      -       -         -        -       -          -          -        -
sdpo           x      -       -         -        -       -          -          -        -
gold           x      -       -         -        -       -          -          -        -
reward_modeling x     -       -         -        -       -          -          -        -
merge          -      -       -         -        -       -          -          -        x
```

### Merge Technique (CPU-only, Post-processing)

**Nota**: La tecnica `merge` è una operazione di post-processing, non una tecnica di training. Non può essere utilizzata da sola per il training, ma serve a combinare checkpoint da esperimenti già completati.

**Caratteristiche**:
- **Type**: Post-processing operation (not a training technique)
- **Infrastructure**: CPU-only (no GPU required)
- **Use Case**: Combine N source checkpoints into a single merged checkpoint
- **Example**: Merge checkpoints from 2+ experiments (different seeds, techniques, or configurations)
- **Requirements**:
  - Source checkpoints must have the same base model and architecture
  - Lineage relations must be acyclic (no cycles in derived-from graph)
  - Weights must sum to 1.0 (linear combination)

**Supported by**:
- **from_scratch**: Minimal Python script to load and merge weights
- **TRL** (via external merge.py script, not via trainer)

**Configuration example**:
```yaml
experiment:
  name: "merged-experiment"

training:
  technique: "merge"
  merge_method: "linear"  # linear (default), or custom callable

# Merge-specific config
merge:
  source_exp_ids: ["e-001", "e-002", "e-003"]
  weights: [0.2, 0.3, 0.5]  # Must sum to 1.0
  output_uri: "master:///merged/exp_merged_001"
```

**Implementation** (`merge.py.j2`):
Quando `technique: "merge"` è configurato, il generatore crea uno script `merge.py` che:
1. Legge i checkpoint sorgente dalle loro URIs
2. Carica i modelli (verifica compatibilità architettura)
3. Estrae i pesi da ogni checkpoint
4. Combina linearmente con i pesi specificati: `merged_weights = sum(w_i * weights[i] for i in sources)`
5. Salva il checkpoint merged con output_uri
6. Comunica con il Master API per registrare la relazione MERGED_FROM

**Lineage Integration**:
Il merge triggera l'API `/merge` del Master che:
1. Valida che i source checkpoint abbiano lo stesso base model
2. Controlla che non ci siano cicli nel lineage
3. Crea un nuovo :Checkpoint node con relazioni MERGED_FROM verso i source checkpoints
4. Traccia completamente l'operazione di merge nel grafo Neo4j

Per dettagli su Neo4j schema e MERGED_FROM relation, vedi [`docs/lineage/schema.md`](lineage/schema.md).

### API

```python
is_compatible("grpo", "trl")          # True
is_compatible("dapo", "trl")          # False

get_compatible_frameworks("grpo")     # ["from_scratch", "openrlhf", "trl", "unsloth", "verl"]
get_compatible_techniques("verl")     # ["dapo", "dr_grpo", "flowrl", "grpo", "ppo", ...]

check_or_raise("grpo", "trl")        # ok
check_or_raise("dapo", "trl")        # raises ValueError
```

## Organizzazione directory

```
frameworks/
├── __init__.py              # importa single_node/, multi_node/, from_scratch/
├── base.py                  # ABC BaseFrameworkAdapter
├── capability_matrix.py     # Matrice (technique, framework) -> bool
├── single_node/
│   ├── __init__.py          # importa trl, unsloth, axolotl, torchtune
│   ├── trl_adapter.py
│   ├── unsloth_adapter.py
│   ├── axolotl_adapter.py
│   └── torchtune_adapter.py
├── multi_node/
│   ├── __init__.py          # importa verl, openrlhf, llamafactory
│   ├── verl_adapter.py
│   ├── openrlhf_adapter.py
│   └── llamafactory_adapter.py
└── from_scratch/            # Documentazione: docs/from-scratch.md
    ├── __init__.py          # importa fromscratch_adapter
    ├── fromscratch_adapter.py
    └── lib/                 # Copiata nei setup come fromscratch/
        ├── base_trainer.py
        ├── sft_trainer.py
        ├── preference_trainer.py
        ├── rl_trainer.py
        ├── techniques/      # 11 implementazioni concrete
        └── kernels/         # Triton + PyTorch fallback
```
