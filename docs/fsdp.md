# FSDP — Fully Sharded Data Parallel

Integrazione PyTorch FSDP per ottimizzazione cluster multi-GPU nell'envelope di fine-tuning.

## Cos'e' FSDP

FSDP (Fully Sharded Data Parallel) e' il framework nativo PyTorch per il training distribuito su cluster di GPU. Sharda parametri, gradienti e stati ottimizzatore tra le GPU, riducendo drasticamente il consumo di memoria per-GPU e permettendo di addestrare modelli che non entrerebbero su una singola GPU.

**FSDP2** (il modello corrente, via `torch.distributed.fsdp`) e' production-ready: Meta lo usa per il training di Llama 3.1 (8B, 70B, 405B) su fino a 512 GPU.

## Posizione nell'infrastruttura

L'envelope gestisce tre livelli di ottimizzazione complementari:

```
Livello 1: Triton Kernels   →  Ottimizzazione single-GPU (kernel-level)
Livello 2: FSDP             →  Ottimizzazione cluster multi-GPU (sharding)
Livello 3: SkyPilot          →  Orchestrazione cloud (provisioning + scheduling)
```

FSDP opera tra Triton (che ottimizza le operazioni su singola GPU) e SkyPilot (che gestisce il provisioning delle macchine). Non c'e' conflitto: Triton ottimizza il compute locale, FSDP distribuisce il lavoro tra GPU, SkyPilot lancia il tutto nel cloud.

## Configurazione YAML

```yaml
optimization:
  fsdp:
    enabled: true                          # Abilita FSDP
    sharding_strategy: "full_shard"        # full_shard | shard_grad_op | no_shard | hybrid_shard
    auto_wrap_policy: "transformer_based"  # transformer_based | size_based
    min_num_params: 1000000                # Solo per size_based
    cpu_offload: false                     # Offload parametri su CPU (lento ma risparmia VRAM)
    mixed_precision: "bf16"                # none | bf16 | fp16 (auto-set da compute_dtype)
    forward_prefetch: true                 # Pre-fetch del prossimo all-gather
    backward_prefetch: "backward_pre"      # backward_pre | backward_post
    sync_module_states: true               # Sincronizza pesi tra rank all'init
    use_orig_params: true                  # Necessario per torch.compile e QLoRA
    limit_all_gathers: true                # Limita all-gathers concorrenti
    activation_checkpointing: false        # Checkpointing attivazioni via FSDP
```

## Riferimento campi

| Campo | Tipo | Default | Descrizione |
|-------|------|---------|-------------|
| `enabled` | bool | `false` | Abilita/disabilita FSDP |
| `sharding_strategy` | enum | `full_shard` | Strategia di sharding (vedi tabella sotto) |
| `auto_wrap_policy` | enum | `transformer_based` | Come wrappare i moduli per FSDP |
| `min_num_params` | int | `1000000` | Soglia per `size_based` policy |
| `cpu_offload` | bool | `false` | Sposta parametri shardati su CPU |
| `mixed_precision` | enum | `none` | Precisione mista FSDP (auto-set da `compute_dtype`) |
| `forward_prefetch` | bool | `true` | Pre-fetch all-gather durante forward |
| `backward_prefetch` | enum | `backward_pre` | Prefetch durante backward pass |
| `sync_module_states` | bool | `true` | Broadcast pesi da rank 0 all'init |
| `use_orig_params` | bool | `true` | Mantieni parametri originali (necessario per compile/QLoRA) |
| `limit_all_gathers` | bool | `true` | Limita operazioni all-gather concorrenti |
| `activation_checkpointing` | bool | `false` | Ricomputa attivazioni durante backward |

## Strategie di sharding

| Strategia | Equivalente DeepSpeed | Cosa sharda | Quando usarla |
|-----------|----------------------|-------------|---------------|
| `full_shard` | ZeRO-3 | Param + Grad + Optimizer | Modelli grandi, massimo risparmio memoria |
| `shard_grad_op` | ZeRO-2 | Grad + Optimizer | Migliore throughput quando il modello entra in VRAM |
| `no_shard` | DDP | Nulla | Debug e baseline |
| `hybrid_shard` | ZeRO++ | Full intra-nodo, replica inter-nodo | Multi-nodo con NVLink intra-nodo |

## Framework supportati

| Framework | Supporto FSDP | Come funziona |
|-----------|---------------|---------------|
| **TRL** | Full | Genera `accelerate_config.yaml` con settings FSDP |
| **Axolotl** | Full | Genera `accelerate_config.yaml` con settings FSDP |
| **LlamaFactory** | Full | Genera `accelerate_config.yaml` con settings FSDP |
| **From Scratch** | Full | FSDP wrapping nativo in `BaseFromScratchTrainer` |
| **Torchtune** | Internal | FSDP2 gestito internamente nelle ricette `_distributed` |
| **veRL** | Internal | FSDP gestito internamente via Ray workers |
| **OpenRLHF** | N/A | Usa DeepSpeed (non FSDP) |
| **Unsloth** | N/A | Single-GPU only |

> **Nota**: per Torchtune e veRL, NON abilitare `optimization.fsdp.enabled`. Questi framework gestiscono FSDP internamente e il validatore rifiutera' la configurazione.

## FSDP vs DeepSpeed

| Criterio | FSDP | DeepSpeed |
|----------|------|-----------|
| Dipendenza | Nessuna (PyTorch nativo) | `deepspeed>=0.14` |
| `torch.compile` | Supportato | Limitato |
| CPU offloading | All-or-nothing | Granulare (param/optimizer/NVME) |
| Configurazione | Python API / Accelerate YAML | JSON file separato |
| Ecosistema | Meta / torchtitan / torchtune | Microsoft / HuggingFace legacy |

**Raccomandazione**: usare FSDP per TRL, Axolotl, LlamaFactory, From Scratch. Usare DeepSpeed solo per OpenRLHF.

## QLoRA + FSDP

QLoRA e' compatibile con FSDP a patto che `use_orig_params: true` (default). Richiede:

```yaml
training:
  peft:
    method: "qlora"
  precision:
    quantization: "nf4"
optimization:
  fsdp:
    enabled: true
    use_orig_params: true   # Obbligatorio per QLoRA
```

> **Gotcha**: `paged_adamw_8bit` causa errori con FSDP + QLoRA. Usare `adamw_torch`.

## Compatibilita' con Triton kernels

I Triton kernels del backend `from_scratch` sono compatibili con FSDP grazie al sistema dual-dispatch:

- **`forward_triton()`**: opera sui shard locali di ogni rank (i tensori sono gia' locali dopo l'all-gather)
- **`forward_torch()`**: usa operazioni PyTorch standard che gestiscono DTensor nativamente

Non serve `torch.library.triton_op` per i nostri kernels perche' il fallback torch gestisce automaticamente i tensor subclass di FSDP.

## Troubleshooting

| Problema | Causa | Soluzione |
|----------|-------|-----------|
| OOM durante checkpoint save | `FullStateDictConfig` raccoglie tutti i parametri su rank 0 | Usare modelli piu' piccoli o CPU offload |
| NCCL timeout | All-reduce bloccato, tipicamente durante save | Ridurre frequenza checkpoint |
| `RuntimeError: DTensor` | Triton kernel non compone con DTensor | Verificare che il fallback torch sia funzionante |
| `FSDP + Unsloth` | Incompatibile | Usare TRL o from_scratch |
| `FSDP + DeepSpeed` | Mutualmente esclusivi | Scegliere uno dei due |

## Matrice infrastruttura completa

| Framework | Triton | FSDP | SkyPilot |
|-----------|--------|------|----------|
| TRL | Partial (via FlashAttn) | Full (via Accelerate) | Full |
| Unsloth | Native (core) | None (single GPU) | Full |
| Axolotl | Partial (via FlashAttn 2) | Full (via Accelerate) | Full |
| Torchtune | Native (via torchao) | Internal (FSDP2 nativo) | Full |
| From Scratch | Native (TritonOp) | Full (BaseFromScratchTrainer) | Full |
| veRL | Partial (via vLLM/FlashAttn) | Internal (via Ray) | Partial (Ray complexity) |
| OpenRLHF | Partial (via vLLM/FlashAttn) | None (usa DeepSpeed) | Full |
| LlamaFactory | Partial (via FlashAttn) | Full (via Accelerate) | Full |
