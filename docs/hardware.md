# Hardware -- GPU specs e auto-optimizer

> `envelope/hardware/`

Il modulo hardware contiene un database di specifiche GPU e un ottimizzatore automatico che suggerisce configurazioni ottimali basandosi su GPU disponibili e dimensione del modello.

## File

| File | Responsabilita' |
|------|----------------|
| `gpu_specs.py` | Database GPU con specifiche tecniche |
| `auto_optimizer.py` | Suggerimenti automatici di ottimizzazione |

## GPU Database -- `gpu_specs.py`

### `GPUSpec` dataclass

```python
@dataclass(frozen=True)
class GPUSpec:
    name: str                          # Nome della GPU
    vram_gb: int                       # VRAM in GB
    compute_capability: tuple[int, int] # CC (major, minor)
    fp16_tflops: float                 # TFLOPS in FP16
    bf16_tflops: float                 # TFLOPS in BF16 (0 se non supportato)
    fp8_supported: bool                # Supporto FP8
    memory_bandwidth_gbps: int         # Bandwidth in GB/s
```

### GPU registrate

| GPU | VRAM | CC | FP16 TFLOPS | BF16 | FP8 | Bandwidth |
|-----|------|----|-------------|------|-----|-----------|
| A100-40GB | 40 GB | 8.0 | 312 | 312 | No | 1555 GB/s |
| A100-80GB | 80 GB | 8.0 | 312 | 312 | No | 2039 GB/s |
| H100-80GB | 80 GB | 9.0 | 989 | 989 | Si' | 3350 GB/s |
| H200 | 141 GB | 9.0 | 989 | 989 | Si' | 4800 GB/s |
| L40S | 48 GB | 8.9 | 362 | 362 | Si' | 864 GB/s |
| L4 | 24 GB | 8.9 | 121 | 121 | Si' | 300 GB/s |
| A10G | 24 GB | 8.6 | 125 | 125 | No | 600 GB/s |
| T4 | 16 GB | 7.5 | 65 | 0 | No | 320 GB/s |
| V100-16GB | 16 GB | 7.0 | 125 | 0 | No | 900 GB/s |
| V100-32GB | 32 GB | 7.0 | 125 | 0 | No | 900 GB/s |
| RTX 4090 | 24 GB | 8.9 | 165 | 165 | Si' | 1008 GB/s |
| RTX 3090 | 24 GB | 8.6 | 71 | 71 | No | 936 GB/s |

### Funzioni helper

```python
get_gpu_spec("A100-80GB") -> GPUSpec | None  # Lookup case-insensitive con partial match
supports_bf16("A100-80GB") -> True           # CC >= 8.0
supports_fp8("H100-80GB") -> True            # Solo Hopper
```

Il lookup e' fuzzy: `get_gpu_spec("a100")` matcha `A100-40GB`.

## Auto-Optimizer -- `auto_optimizer.py`

### `estimate_model_memory_gb(model_name)`

Stima la memoria del modello in BF16 dal nome:
- Estrae il numero di miliardi di parametri dal nome (es. "Qwen2.5-7B" -> 7B -> 14 GB)
- Formula: `billions * 2.0` (2 bytes per parametro in BF16)
- Default: 14 GB (7B) se non riesce a estrarre il numero

### `suggest_optimizations(config)`

Data una `EnvelopeConfig`, ritorna un dizionario di suggerimenti (non applicati automaticamente):

#### Logica dei suggerimenti

| Condizione | Suggerimento | Note |
|------------|--------------|------|
| GPU non supporta BF16 (V100, T4) | `compute_dtype = fp16` | CC < 8.0 |
| GPU Hopper + modello > 50% VRAM | `quantization = fp8` | FP8 raddoppia il throughput |
| Modello > 60% VRAM + PEFT attivo | `quantization = nf4` | Entra in VRAM |
| Modello > 30% VRAM | `gradient_checkpointing = True` | Riduce uso memoria |
| GPU Ampere+ (CC >= 8.0) | `flash_attention = v2` | Flash Attention supportata |
| Stage SFT | `sequence_packing = True` | Ottimizza l'utilizzo |
| Multi-GPU + modello > 40% VRAM | `deepspeed_stage = 2` | Sharding dei parametri |

#### Formato output

```python
suggestions = {
    "precision.compute_dtype": "fp16",
    "_reason_dtype": "GPU V100 does not support BF16.",
    "optimization.flash_attention": "v2",
    # chiavi con _ prefisso sono spiegazioni, non override
}
```

Le chiavi con prefisso `_reason_` contengono la spiegazione del suggerimento. La CLI le mostra all'utente come context.

### Integrazione

1. **CLI `validate`**: Mostra i suggerimenti dopo la validazione
2. **Generator**: Calcola i suggerimenti e li passa ai template come `{{ suggestions }}`
3. **Flag `--apply-suggestions`**: Se attivo, il generatore applica i suggerimenti automaticamente
