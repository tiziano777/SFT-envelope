# From Scratch -- Training PyTorch raw con ontologia ABC

> `envelope/frameworks/from_scratch/`

Il backend `from_scratch` genera setup di training basati su **PyTorch puro**, senza dipendenze da framework di terze parti (TRL, veRL, Unsloth, ecc.). Invece di delegare a un Trainer opaco, produce un training loop leggibile, concreto e completamente personalizzabile, costruito su una gerarchia di classi astratte (ABC) che l'utente puo' estendere liberamente.

## Motivazione

I framework di alto livello (TRL, veRL, ecc.) coprono il 90% dei casi d'uso standard. Il restante 10% -- loss custom, reward shaping sperimentale, architetture non standard, ottimizzazioni GPU specifiche -- richiede spesso di combattere contro le astrazioni del framework. `from_scratch` risolve il problema alla radice: genera codice PyTorch diretto che l'utente possiede completamente.

```
Framework di alto livello               From Scratch
─────────────────────────               ─────────────
YAML → template → Trainer API           YAML → template → training loop concreto
                                                          + classi ABC estendibili
                                                          + Triton kernels opzionali
```

## Quick Start

### 1. Configurazione YAML

L'unica differenza rispetto a un setup standard e' `framework.backend: "from_scratch"`:

```yaml
experiment:
  name: "grpo-fromscratch-qwen-math"
  seed: 42

model:
  name_or_path: "Qwen/Qwen2.5-7B-Instruct"
  trust_remote_code: true
  max_seq_length: 2048

training:
  technique: "grpo"
  peft:
    method: "lora"
    r: 16
    lora_alpha: 32
  precision:
    compute_dtype: "bf16"
  technique_args:
    num_generations: 16
    max_completion_length: 512
    epsilon: 0.2
    beta: 0.04
    temperature: 1.0

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
  backend: "from_scratch"              # <── questo attiva il backend
  triton_kernels: ["cross_entropy"]    # opzionale: kernel Triton da abilitare
```

### 2. Generazione setup

```bash
envelope setup --name grpo-scratch --config configs/examples/grpo_fromscratch.yaml
```

### 3. Output generato

```
setups/setup_grpo-scratch/
├── train.py                # Entry-point generato (thin wrapper)
├── run.sh                  # Launcher
├── config.yaml             # Config congelata
├── requirements.txt        # torch, transformers, datasets, (triton)
├── rewards/                # Reward functions (come qualsiasi setup)
│   ├── __init__.py
│   └── math_correctness.py
└── fromscratch/            # Libreria locale (copiata da lib/)
    ├── base_trainer.py     # Training loop completo + TrainerConfig
    ├── sft_trainer.py      # SFT trainer concreto
    ├── preference_trainer.py   # Base preference (ABC)
    ├── rl_trainer.py       # Base RL (ABC)
    ├── techniques/         # Implementazioni per tecnica
    │   ├── grpo.py         ← usato in questo setup
    │   ├── dpo.py
    │   └── ...
    └── kernels/            # Triton + fallback PyTorch
        ├── registry.py
        ├── cross_entropy.py
        └── ...
```

### 4. Esecuzione

```bash
cd setups/setup_grpo-scratch
pip install -r requirements.txt
bash run.sh
```

Il setup e' autocontenuto. Puo' essere copiato (`scp`) o inviato a qualsiasi macchina senza bisogno di installare `finetuning-envelope`.

---

## Ontologia delle classi

L'architettura rispecchia la gerarchia naturale delle tecniche di training: una base concreta per il loop, tre livelli astratti per stage, e implementazioni concrete per ogni tecnica.

```
BaseFromScratchTrainer (ABC)
│
│   Training loop concreto: optimizer, scheduler, gradient accumulation,
│   mixed precision, checkpointing, emit() per output strutturato.
│   Metodo astratto: compute_loss(batch) → Tensor
│
├── SFTTrainer (concreto)
│   Cross-entropy loss + collate con tokenization.
│   Funzionante out-of-the-box. Override per custom data formatting.
│
├── PreferenceTrainer (ABC)
│   │   Gestisce ref_model, calcola log-probs chosen/rejected.
│   │   Metodo astratto: preference_loss() → Tensor
│   │
│   ├── DPOTrainer          -log σ(β · (π_diff - ref_diff))
│   ├── SimPOTrainer         Length-normalized + γ margin (reference-free)
│   ├── KTOTrainer           Loss asimmetrica desirable/undesirable
│   └── ORPOTrainer          SFT loss + odds ratio penalty
│
└── RLTrainer (ABC)
    │   Gestisce generation loop, reward scoring, KL penalty.
    │   Metodi astratti: compute_advantages(), policy_loss()
    │
    ├── GRPOTrainer          Group-normalized advantages + clipped surrogate
    ├── PPOTrainer           GAE + value head + clipped surrogate + value loss
    ├── DAPOTrainer          Dual-clip + dynamic sampling
    ├── VAPOTrainer          Value-aware clipping + critic
    ├── RLOOTrainer          Leave-one-out baseline + REINFORCE loss
    ├── ReinforcePPTrainer   EMA baseline + clipped REINFORCE
    ├── DrGRPOTrainer        Bessel correction + length normalization
    ├── FlowRLTrainer        Flow-weighted policy gradient
    └── PRIMETrainer         Process reward-informed + group normalization
```

### ABC radice: `BaseFromScratchTrainer`

> `fromscratch/base_trainer.py`

| Componente | Tipo | Descrizione |
|---|---|---|
| `TrainerConfig` | Dataclass | Tutti gli iperparametri: lr, batch_size, warmup, scheduler, precision, seed, technique_args |
| `compute_loss(batch)` | **Astratto** | L'unico metodo obbligatorio da implementare |
| `collate_fn(examples)` | **Astratto** | Converte esempi raw del dataset in batch tensore |
| `train()` | Concreto | Loop completo: DataLoader, optimizer (AdamW con weight decay differenziato), LR scheduler (cosine/linear con warmup), `torch.amp` (bf16/fp16), gradient accumulation, gradient clipping, checkpointing, emit() per output strutturato |
| `on_train_begin/end()` | Hook | Override per logica custom a inizio/fine training |
| `on_step_end(step, loss)` | Hook | Override per logging, early stopping, ecc. |
| `on_epoch_end(epoch, metrics)` | Hook | Override per valutazione a fine epoch |
| `on_save(step)` | Hook | Override per logica post-salvataggio |
| `save_model()` | Concreto | Salvataggio finale (PEFT-aware) |

### Stage trainers

#### `SFTTrainer` — `fromscratch/sft_trainer.py`

Completamente funzionante as-is. Il `compute_loss` delega al forward del modello (causal LM con label shifting). Il `collate_fn` gestisce sia testo piano che chat format (applicando `tokenizer.apply_chat_template`).

#### `PreferenceTrainer` — `fromscratch/preference_trainer.py`

Aggiunge:
- Gestione del `ref_model` (freeze, device placement)
- `_compute_logprobs(model, input_ids, mask, labels)` — log-prob per-token aggregato per esempio
- `compute_loss` concreto che calcola logprobs chosen/rejected per policy e ref, poi delega a `preference_loss()`
- `collate_fn` per coppie chosen/rejected con tokenization
- Metodo astratto: `preference_loss(policy_chosen, policy_rejected, ref_chosen, ref_rejected) -> Tensor`

#### `RLTrainer` — `fromscratch/rl_trainer.py`

Aggiunge:
- Gestione di `reward_fns` e `ref_model`
- `_generate_with_logprobs(prompts, num_generations, ...)` — generazione con score collection
- `_score_completions(prompts, completions, ...)` — scoring multi-reward
- `_recompute_logprobs(prompts, completions)` — ricalcolo log-prob under current policy
- `_compute_kl_penalty(logprobs, ref_logprobs)` — KL divergence
- `compute_loss` concreto: generate → score → `compute_advantages()` → `policy_loss()`
- Metodi astratti: `compute_advantages(rewards) -> Tensor`, `policy_loss(logprobs, old_logprobs, advantages) -> Tensor`

---

## Tecniche implementate

| Tecnica | Classe | Stage | Loss | File |
|----|---|---|---|---|
| SFT | `SFTTrainer` | SFT | Cross-entropy causal LM | `sft_trainer.py` |
| DPO | `DPOTrainer` | Preference | `-log σ(β·(π_diff − ref_diff))` | `techniques/dpo.py` |
| SimPO | `SimPOTrainer` | Preference | `-log σ(β·(chosen − rejected − γ))` length-norm | `techniques/simpo.py` |
| KTO | `KTOTrainer` | Preference | Loss asimmetrica prospect-theory | `techniques/kto.py` |
| ORPO | `ORPOTrainer` | Preference | SFT + λ · odds ratio penalty | `techniques/orpo.py` |
| GRPO | `GRPOTrainer` | RL | Group-norm advantages + clipped surrogate | `techniques/grpo.py` |
| PPO | `PPOTrainer` | RL | GAE + value head + clipped surrogate + value loss | `techniques/ppo.py` |
| DAPO | `DAPOTrainer` | RL | Dual-clip (upper + lower bound) + group advantages | `techniques/dapo.py` |
| VAPO | `VAPOTrainer` | RL | Value-aware clipping + critic loss | `techniques/vapo.py` |
| RLOO | `RLOOTrainer` | RL | Leave-one-out baseline + REINFORCE | `techniques/rloo.py` |
| REINFORCE++ | `ReinforcePPTrainer` | RL | EMA baseline + clipped REINFORCE | `techniques/reinforce_pp.py` |
| Dr. GRPO | `DrGRPOTrainer` | RL | Bessel-corrected std + clipped surrogate | `techniques/dr_grpo.py` |
| FlowRL | `FlowRLTrainer` | RL | Blend clipped surrogate + direct gradient | `techniques/flowrl.py` |
| PRIME | `PRIMETrainer` | RL | Process reward + group-norm + clipped surrogate | `techniques/prime.py` |

Tutte le 14 tecniche supportate dall'envelope sono disponibili in `from_scratch`. Questo e' l'unico backend con copertura completa.

---

## Come estendere

### Livello 1: Override di un hook (zero subclassing)

Per aggiungere comportamento a un trainer esistente senza subclassare, basta modificare il `train.py` generato:

```python
# train.py (generato) — aggiungere logging a WandB
trainer = GRPOTrainer(model=model, tokenizer=tokenizer, config=trainer_config, ...)

# Override dell'hook direttamente sull'istanza
original_on_step = trainer.on_step_end

def custom_on_step(step, loss):
    original_on_step(step, loss)
    if step % 50 == 0:
        wandb.log({"step": step, "loss": loss})

trainer.on_step_end = custom_on_step
metrics = trainer.train()
```

### Livello 2: Subclassing nel train.py

Per modificare il comportamento di un trainer, crea una sottoclasse direttamente nel `train.py` generato:

```python
# train.py — custom reward shaping per GRPO
from fromscratch.techniques.grpo import GRPOTrainer

class MyGRPOTrainer(GRPOTrainer):
    """GRPO con reward shaping custom."""

    def compute_advantages(self, rewards, **kwargs):
        # Reward shaping: bonus per risposte concise
        length_penalty = torch.tensor(
            [len(c) / 1000.0 for c in self._last_completions],
            device=rewards.device
        )
        shaped_rewards = rewards - 0.1 * length_penalty
        return super().compute_advantages(shaped_rewards, **kwargs)

trainer = MyGRPOTrainer(model=model, tokenizer=tokenizer, ...)
```

### Livello 3: Nuova tecnica da zero

Per implementare una tecnica completamente nuova, crea una sottoclasse di uno degli stage trainer nel package `fromscratch/`:

```python
# fromscratch/techniques/my_technique.py

import torch
from ..rl_trainer import RLTrainer

class MyTechniqueTrainer(RLTrainer):
    """Tecnica RL custom con advantage estimation personalizzata."""

    def compute_advantages(self, rewards, **kwargs):
        # Implementazione custom: per esempio, ranked advantages
        ranked = rewards.argsort().argsort().float()
        return (ranked / ranked.max()) * 2.0 - 1.0  # [-1, 1]

    def policy_loss(self, logprobs, old_logprobs, advantages):
        # Loss custom: per esempio, weighted REINFORCE senza clipping
        return -(logprobs * advantages.detach()).mean()
```

Poi nel `train.py`:

```python
from fromscratch.techniques.my_technique import MyTechniqueTrainer

trainer = MyTechniqueTrainer(model=model, tokenizer=tokenizer, config=config, ...)
```

### Livello 4: Override completo del training loop

Per un controllo totale, override `train()` stesso:

```python
from fromscratch.base_trainer import BaseFromScratchTrainer

class FullyCustomTrainer(BaseFromScratchTrainer):
    def compute_loss(self, batch):
        # ...

    def collate_fn(self, examples):
        # ...

    def train(self):
        """Training loop completamente custom."""
        optimizer = self._create_optimizer()
        dataloader = DataLoader(self.train_dataset, ...)

        for epoch in range(self.config.num_train_epochs):
            for batch in dataloader:
                loss = self.compute_loss(batch)
                loss.backward()
                # ... logica custom: multi-phase, curriculum, ecc.
                optimizer.step()
                optimizer.zero_grad()

        return {"custom_metric": 42.0}
```

---

## Triton Kernels

Il sistema include un supporto opzionale per kernel Triton con fallback automatico a PyTorch. Questo permette di ottimizzare operazioni computazionalmente intensive senza sacrificare la portabilita'.

### Architettura dual-dispatch

```
fromscratch/kernels/
├── registry.py        KernelRegistry + TritonOp ABC
├── ops.py             Re-export per import puliti
├── cross_entropy.py   Fused softmax + NLL (evita materializzare tensori intermedi)
├── rms_norm.py        Fused RMS normalization (single-pass su dati)
└── softmax.py         Online stable softmax (single-pass)
```

Ogni kernel e' una classe `TritonOp` con due implementazioni:

```python
class TritonOp(ABC):
    @abstractmethod
    def forward_triton(self, *args, **kwargs): ...    # Triton kernel (fast path)

    @abstractmethod
    def forward_torch(self, *args, **kwargs): ...     # PyTorch fallback (sempre funziona)

    def __call__(self, *args, **kwargs):
        if triton_available:
            return self.forward_triton(...)
        return self.forward_torch(...)              # Auto-fallback
```

### Kernel disponibili

| Kernel | Operazione | Beneficio |
|---|---|---|
| `cross_entropy` | Fused softmax + NLL loss | ~2x meno memoria (evita tensori intermedi) |
| `rms_norm` | Fused RMS normalization | Single-pass, evita materializzazione di x^2 |
| `softmax` | Online stable softmax | Single-pass, numericamente stabile |

### Configurazione

Nel YAML, elencare i kernel da attivare:

```yaml
framework:
  backend: "from_scratch"
  triton_kernels: ["cross_entropy", "rms_norm"]    # Aggiunge triton>=3.0 ai requirements
```

Se `triton_kernels` e' vuoto o assente, i kernel non vengono richiesti come dipendenza. Le implementazioni PyTorch fallback funzionano sempre, anche senza Triton installato.

### Uso nei trainer

```python
from fromscratch.kernels import kernel_registry

# Ottiene il kernel (Triton se disponibile, PyTorch altrimenti)
fused_ce = kernel_registry.get("cross_entropy")

# Uso identico all'equivalente PyTorch
loss = fused_ce(logits, labels)
```

### Aggiungere un kernel custom

```python
# fromscratch/kernels/my_kernel.py

import torch
from . import kernel_registry
from .registry import TritonOp, _triton_available

@kernel_registry.register("my_op")
class FusedMyOp(TritonOp):
    def forward_torch(self, x, **kwargs):
        return torch.sigmoid(x) * x  # SiLU

    def forward_triton(self, x, **kwargs):
        if not _triton_available():
            return self.forward_torch(x)

        import triton
        import triton.language as tl
        # ... implementazione Triton kernel
```

Poi registrare il kernel in `fromscratch/kernels/__init__.py`:

```python
from . import my_kernel as _mk  # noqa: F401
```

---

## Protocollo di output strutturato

Il backend `from_scratch` rispetta integralmente il protocollo di output strutturato. Il `train.py` generato include:

- **`HYPERPARAM_DEFAULTS`**: dizionario di default sovrascrivibili
- **`resolve_hyperparams()`**: risoluzione `HPARAM_*` env vars con type casting
- **`emit()`**: output strutturato (`EXPERIMENT_STATUS`, `EXPERIMENT_RESULT`, ecc.)

I setup `from_scratch` sono indistinguibili da quelli TRL/veRL dal punto di vista del consumatore. Vengono trattati come black-box identiche.

```bash
# Override di iperparametri via env vars (identico a qualsiasi altro backend)
HPARAM_LEARNING_RATE=3e-5 HPARAM_PER_DEVICE_TRAIN_BATCH_SIZE=4 bash run.sh
```

---

## Compatibilita'

`from_scratch` e' l'unico backend con copertura completa: supporta **tutte le 14 tecniche** registrate nell'envelope.

```
              trl  unsloth  axolotl  torchtune  verl  openrlhf  llamafactory  from_scratch
sft            x      x       x         x        -       x          x              x
dpo            x      x       x         x        -       x          x              x
simpo          x      x       -         -        -       -          -              x
kto            x      -       -         -        -       -          x              x
orpo           x      x       -         -        -       -          x              x
grpo           x      x       -         -        x       x          -              x
ppo            x      -       -         -        x       x          -              x
dapo           -      -       -         -        x       -          -              x
vapo           -      -       -         -        x       -          -              x
rloo           x      -       -         -        -       x          -              x
reinforce_pp   -      -       -         -        x       x          -              x
dr_grpo        -      -       -         -        x       -          -              x
flowrl         -      -       -         -        x       -          -              x
prime          -      -       -         -        x       -          -              x
```

Verificare da CLI:

```bash
envelope compatible grpo
# Output: from_scratch, openrlhf, trl, unsloth, verl

envelope compatible dapo
# Output: from_scratch, verl
```

---

## Differenze rispetto ai framework di alto livello

| Aspetto | TRL / veRL / Unsloth | `from_scratch` |
|---|---|---|
| Training loop | Opaco (dentro il Trainer) | Trasparente (`train()` leggibile) |
| Personalizzazione loss | Callback limitati | Override di `compute_loss()` |
| Nuove tecniche | Fork del framework | Subclassing ABC |
| GPU optimization | Dipende dal framework | Triton kernels custom |
| Overhead dipendenze | Framework completo | Solo PyTorch + transformers |
| Multi-GPU | Framework-specific | `torchrun` nativo |
| Maturita' | Produzione | Sperimentale (vedi sotto) |

---

## Stato di maturita'

> **Status: alpha/sperimentale**

Il backend `from_scratch` e' funzionalmente completo a livello di **definizione ad alto livello**: l'ontologia delle classi, la gerarchia ABC, il sistema di kernel dispatch, e l'integrazione con il generatore sono tutti implementati e testati. Lo stato di maturita' per componente:

### Adapter e integrazione

| Componente | Stato | Note |
|---|---|---|
| `FromScratchAdapter` | Stabile | Registrato nel registry, capability matrix completa |
| Template Jinja2 | Stabile | Singolo template parametrico per tutte le tecniche |
| Copia `lib/` nel setup | Stabile | `shutil.copytree` con `dirs_exist_ok=True` |
| Protocollo output | Stabile | HPARAM_*, emit(), identico agli altri backend |
| Config YAML | Stabile | Campo `triton_kernels` opzionale su `FrameworkConfig` |

### Core trainers

| Componente | Stato | Note |
|---|---|---|
| `BaseFromScratchTrainer` | Stabile | Loop completo con tutte le feature standard |
| `TrainerConfig` | Stabile | Copre tutti gli iperparametri overridable via env vars |
| `SFTTrainer` | Stabile | Funzionante out-of-the-box, testabile senza GPU (CPU) |
| `PreferenceTrainer` | Beta | Logica log-prob e collate preference validata, da testare end-to-end |
| `RLTrainer` | Beta | Generation loop funzionale, da ottimizzare per batch generation |

### Tecniche

| Componente | Stato | Note |
|---|---|---|
| GRPO, DPO, SFT | Beta | Implementazioni matematicamente corrette, validate in unit test |
| SimPO, KTO, ORPO | Beta | Loss formule implementate, da validare end-to-end |
| PPO, RLOO, REINFORCE++ | Beta | Implementazioni semplificate (vedi nota sotto) |
| DAPO, VAPO, Dr.GRPO | Alpha | Implementazioni delle varianti paper-specific |
| FlowRL, PRIME | Alpha | Placeholder funzionali, da raffinare |

> **Nota su PPO**: l'implementazione PPO usa un value head semplificato (Linear head) e un'approssimazione di GAE. Per PPO production-ready con GAE completo e critic separato, usare veRL.

### Triton kernels

| Componente | Stato | Note |
|---|---|---|
| `KernelRegistry` + `TritonOp` | Stabile | Pattern dual-dispatch, fallback garantito |
| `cross_entropy` | Beta | Kernel JIT + fallback, da benchmarkare |
| `rms_norm` | Beta | Kernel JIT + fallback, da benchmarkare |
| `softmax` | Beta | Kernel JIT + fallback, da benchmarkare |

### Non implementato

- **Evaluation loop**: nessun `evaluate()` e' implementato. L'utente puo' aggiungere valutazione nell'hook `on_epoch_end()`.
- **Gradient scaler per bf16**: `GradScaler` e' abilitato solo per fp16. bf16 non ne ha bisogno su Ampere+.
- **Batch generation per RL**: il loop di generazione in `RLTrainer` processa un prompt alla volta. Per throughput elevato, integrare vLLM o batch generation.
- **DeepSpeed**: nessuna integrazione. Usare OpenRLHF per training distribuito con DeepSpeed.

---

## FSDP — Training distribuito multi-GPU

Il `BaseFromScratchTrainer` integra PyTorch FSDP (Fully Sharded Data Parallel) per il training distribuito su cluster di GPU. L'integrazione e' nativa: non richiede Accelerate ne' configurazioni esterne.

### Configurazione YAML

```yaml
framework:
  backend: "from_scratch"

hardware:
  gpu_type: "A100-80GB"
  gpu_count: 4               # Multi-GPU

optimization:
  fsdp:
    enabled: true
    sharding_strategy: "full_shard"
    auto_wrap_policy: "transformer_based"
    mixed_precision: "bf16"
    activation_checkpointing: false
    cpu_offload: false
    use_orig_params: true     # Necessario per QLoRA
```

### Come funziona

Quando `fsdp.enabled: true` e `WORLD_SIZE > 1`:

1. **Init**: `BaseFromScratchTrainer.__init__()` chiama `init_process_group("nccl")` e configura `local_rank`
2. **FSDP wrap**: `_wrap_with_fsdp()` avvolge il modello con le policy selezionate (transformer-based o size-based auto-wrap, mixed precision, CPU offload)
3. **Training**: `train()` usa `DistributedSampler` per shardare i dati tra rank, con `sampler.set_epoch()` per shuffling corretto
4. **Checkpoint**: `_save_checkpoint()` usa `FullStateDictConfig(offload_to_cpu=True, rank0_only=True)` — solo rank 0 salva su disco
5. **Logging**: solo rank 0 emette log e metriche (guard `_should_log()`)
6. **Cleanup**: `_cleanup_distributed()` distrugge il process group alla fine

### Lancio multi-GPU

Il `run.sh` generato usa `torchrun`:

```bash
# Single-node, 4 GPU
torchrun --nproc_per_node=4 train.py

# Multi-node (2 nodi, 4 GPU ciascuno)
torchrun --nproc_per_node=4 --nnodes=2 \
         --rdzv_backend=c10d --rdzv_endpoint=$MASTER_ADDR:$MASTER_PORT \
         train.py
```

### Compatibilita' Triton + FSDP

I Triton kernels sono compatibili con FSDP grazie al dual-dispatch: `forward_triton()` opera sui shard locali (i tensori sono gia' locali dopo l'all-gather), mentre `forward_torch()` gestisce DTensor nativamente come fallback.

### Note importanti

- FSDP richiede almeno 2 GPU (`gpu_count >= 2` o `num_nodes >= 2`)
- FSDP + Unsloth e' incompatibile (Unsloth e' esclusivamente single-GPU)
- FSDP + DeepSpeed sono mutualmente esclusivi
- QLoRA + FSDP richiede `use_orig_params: true` (default)
- Se FSDP gestisce la mixed precision, il `GradScaler` viene disabilitato automaticamente

Per la documentazione completa FSDP (tutti i framework, strategie di sharding, troubleshooting) vedi [`docs/fsdp.md`](fsdp.md).

---

## Struttura dei file sorgente

```
envelope/frameworks/from_scratch/
├── __init__.py                         Registra FromScratchAdapter
├── fromscratch_adapter.py              Plugin adapter (registry, template, requirements)
└── lib/                                Copiata nei setup come fromscratch/
    ├── __init__.py
    ├── base_trainer.py                 329 righe — ABC radice + loop concreto
    ├── sft_trainer.py                   73 righe — SFT funzionante
    ├── preference_trainer.py           165 righe — Base preference + log-prob utilities
    ├── rl_trainer.py                   243 righe — Base RL + generation + scoring
    ├── techniques/
    │   ├── __init__.py
    │   ├── dpo.py                       32 righe — DPO loss
    │   ├── simpo.py                     33 righe — SimPO loss
    │   ├── kto.py                       46 righe — KTO loss asimmetrica
    │   ├── orpo.py                      37 righe — ORPO loss
    │   ├── grpo.py                      58 righe — GRPO con group-norm
    │   ├── ppo.py                       55 righe — PPO con value head
    │   ├── dapo.py                      59 righe — DAPO dual-clip
    │   ├── vapo.py                      45 righe — VAPO value-aware
    │   ├── rloo.py                      46 righe — RLOO leave-one-out
    │   ├── reinforce_pp.py              50 righe — REINFORCE++ con EMA
    │   ├── dr_grpo.py                   56 righe — Dr. GRPO con Bessel
    │   ├── flowrl.py                    51 righe — FlowRL
    │   └── prime.py                     57 righe — PRIME
    └── kernels/
        ├── __init__.py                  Registry singleton + auto-import
        ├── registry.py                  65 righe — KernelRegistry + TritonOp ABC
        ├── ops.py                       Re-export di convenience
        ├── cross_entropy.py             99 righe — Fused CE (Triton + fallback)
        ├── rms_norm.py                  90 righe — Fused RMSNorm (Triton + fallback)
        └── softmax.py                   73 righe — Fused softmax (Triton + fallback)
```

Totale: ~1.950 righe di codice Python distribuito su 28 file.

---

## Nota su JAX e SkyPilot

Il backend `from_scratch` e' esclusivamente PyTorch. JAX e' escluso per incompatibilita' con l'ecosistema:

- `transformers.AutoModelForCausalLM` ritorna moduli PyTorch
- PEFT (`peft.LoraConfig`, `get_peft_model`) opera su `torch.nn.Module`
- `bitsandbytes` (NF4/INT8) e' PyTorch-only
- SkyPilot (orchestrazione cluster) e' indipendente dal compute backend — gestisce provisioning e scheduling, non il training

Le ottimizzazioni GPU compute-level sono delegate a **Triton kernels**, che compilano per GPU NVIDIA indipendentemente dal framework Python. Questo approccio offre il meglio dei due mondi: flessibilita' di PyTorch per il training loop, performance di kernel custom per le operazioni critiche.
