# Runtime Diagnostics

> `envelope/diagnostics/`

Modulo di diagnostica runtime che monitora il training e emette warning strutturati quando rileva problematiche comuni. Il modulo e' pensato per intercettare pattern noti di degrado del training (loss divergente, gradient explosion, reward collapse, etc.) e fornire suggerimenti operativi immediati.

## Come funziona

Il file `diagnostics.py` viene copiato in ogni directory `setup_{name}/` generata dal sistema. A runtime, viene integrato nel loop di training tramite callback o hook, a seconda del framework in uso.

### Integrazione per framework

| Framework | Meccanismo | Classe/funzione |
|-----------|-----------|-----------------|
| TRL | Callback Trainer | `TRLDiagnosticCallback` (estende `TrainerCallback`) |
| From Scratch | Hook override | `run_diagnostics()` chiamata nel training loop via hook |

- **TRL**: `TRLDiagnosticCallback` si aggancia agli eventi `on_log` del Trainer e ispeziona le metriche ad ogni step di logging.
- **From Scratch**: `run_diagnostics()` e' una funzione pura invocata dal training loop tramite il meccanismo di hook override del `BaseFromScratchTrainer`.

## Regole di diagnostica

Il sistema implementa 6 regole, ciascuna con una condizione di attivazione, un livello di severita', e un suggerimento operativo:

| Regola | Condizione | Severita' | Suggerimento |
|--------|-----------|-----------|-------------|
| `loss_divergence` | `loss > 10.0` o `loss` e' `NaN`/`Inf` | CRITICAL | Ridurre learning rate, verificare dataset, abilitare gradient clipping |
| `gradient_explosion` | `grad_norm > 10.0` | WARNING | Ridurre `max_grad_norm`, verificare learning rate |
| `reward_collapse` | `reward_std < 0.01` per 50+ step | WARNING | Verificare reward function, aumentare `num_generations` |
| `clip_ratio_alert` | `clip_ratio > 0.3` | INFO | Ridurre `epsilon` o learning rate |
| `kl_divergence_alert` | `kl_divergence > 15.0` | WARNING | Aumentare `beta` (KL penalty), ridurre learning rate |
| `throughput_degradation` | throughput cala del 50%+ rispetto alla media iniziale | INFO | Verificare thermal throttling, controllare memory usage |

### Dettaglio regole

Ogni regola e' implementata come funzione pura con la seguente signature:

```python
def check_loss_divergence(
    step: int,
    metrics: dict[str, float],
    technique: str,
) -> DiagnosticWarning | None:
    ...
```

La funzione riceve lo step corrente, il dizionario delle metriche, e il nome della tecnica. Ritorna un `DiagnosticWarning` (con `rule`, `severity`, `message`, `suggestion`) oppure `None` se la regola non e' violata.

## Rate limiting

Per evitare di inondare i log con warning ripetuti, ogni regola ha un **cooldown di 50 step**. Dopo che una regola emette un warning, non puo' emetterne un altro fino a che non sono passati almeno 50 step. Il cooldown e' indipendente per ogni regola.

Il rate limiting e' gestito internamente tramite un dizionario `_last_triggered: dict[str, int]` che traccia l'ultimo step in cui ogni regola e' stata attivata.

## Estensibilita'

Per aggiungere una nuova regola di diagnostica:

1. Crea una funzione pura in `diagnostics.py`:

```python
def check_my_rule(
    step: int,
    metrics: dict[str, float],
    technique: str,
) -> DiagnosticWarning | None:
    if metrics.get("my_metric", 0) > threshold:
        return DiagnosticWarning(
            rule="my_rule",
            severity="WARNING",
            message=f"Step {step}: my_metric={metrics['my_metric']:.4f} supera soglia",
            suggestion="Suggerimento operativo per risolvere il problema",
        )
    return None
```

2. Registra la funzione nella lista `DIAGNOSTIC_RULES`:

```python
DIAGNOSTIC_RULES = [
    check_loss_divergence,
    check_gradient_explosion,
    check_reward_collapse,
    check_clip_ratio_alert,
    check_kl_divergence_alert,
    check_throughput_degradation,
    check_my_rule,  # nuova regola
]
```

Le regole sono funzioni pure che non mantengono stato interno -- il rate limiting e la gestione dello stato sono centralizzati nel runner.

## Testing

La funzione `reset_state()` azzera il dizionario di cooldown e tutte le metriche accumulate (come la baseline del throughput). Questo e' necessario per i test, dove ogni test case deve partire da uno stato pulito:

```python
from diagnostics import reset_state

def test_loss_divergence():
    reset_state()
    # ... test logic ...
```

## Output

I warning diagnostici vengono emessi come log strutturati su stderr:

```
[DIAGNOSTIC] CRITICAL loss_divergence @ step 150: loss=NaN -- Ridurre learning rate, verificare dataset, abilitare gradient clipping
[DIAGNOSTIC] WARNING gradient_explosion @ step 200: grad_norm=15.32 -- Ridurre max_grad_norm, verificare learning rate
```

Il formato e' parsabile da tool esterni tramite il prefisso `[DIAGNOSTIC]`.
