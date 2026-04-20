# Registry -- Sistema plugin

> `envelope/registry/`

Il modulo registry implementa il pattern plugin tramite un `Registry[T]` generico. Tecniche e framework si auto-registrano tramite decoratore, permettendo estensibilita' senza modificare il core.

## File

| File | Responsabilita' |
|------|----------------|
| `base.py` | Classe `Registry[T]` generica |
| `__init__.py` | Istanze singleton (`technique_registry`, `framework_registry`) e `discover_plugins()` |

## `Registry[T]` -- `base.py`

Classe generica parametrizzata che mappa stringhe a classi:

```python
class Registry(Generic[T]):
    def __init__(self, name: str): ...
    def register(self, key: str) -> Callable: ...  # decoratore
    def get(self, key: str) -> type[T]: ...         # lookup
    def create(self, key: str, **kwargs) -> T: ...  # istanzia
    def keys(self) -> list[str]: ...                # tutti i nomi
    def __contains__(self, key: str) -> bool: ...
    def __len__(self) -> int: ...
```

### Registrazione tramite decoratore

```python
@technique_registry.register("grpo")
class GRPOTechnique(BaseTechnique):
    ...
```

Il decoratore aggiunge la classe al registro interno. Se la chiave esiste gia', lancia `ValueError` per evitare collisioni.

### Lookup

```python
cls = technique_registry.get("grpo")    # type[BaseTechnique]
instance = technique_registry.create("grpo")  # BaseTechnique
```

`get()` ritorna la **classe**, `create()` la **istanzia**. Se la chiave non esiste, `KeyError` con messaggio che elenca le chiavi disponibili.

## Istanze singleton -- `__init__.py`

Due registri globali:

```python
from envelope.registry.base import Registry
from envelope.techniques.base import BaseTechnique
from envelope.frameworks.base import BaseFrameworkAdapter

technique_registry: Registry[BaseTechnique] = Registry("techniques")
framework_registry: Registry[BaseFrameworkAdapter] = Registry("frameworks")
```

### `discover_plugins()`

Importa tutti i sotto-moduli di `techniques/` e `frameworks/` per attivare i decoratori `@register`:

```python
def discover_plugins() -> None:
    import envelope.techniques.sft
    import envelope.techniques.preference
    import envelope.techniques.rl
    import envelope.techniques.flow
    import envelope.techniques.distillation
    import envelope.frameworks.single_node
    import envelope.frameworks.multi_node
```

Questa funzione e' idempotente: puo' essere chiamata piu' volte senza effetti collaterali. E' invocata automaticamente dal generatore e dalla CLI.

## Come aggiungere un plugin

1. **Crea la classe** in un file sotto `techniques/<stage>/` o `frameworks/<scope>/`
2. **Decora** con `@technique_registry.register("nome")` o `@framework_registry.register("nome")`
3. **Importa** nel `__init__.py` della sotto-cartella:
   ```python
   import envelope.techniques.rl.my_technique  # noqa: F401
   ```

Il `# noqa: F401` silenzia l'avviso di import inutilizzato -- l'import serve solo ad attivare il decoratore.

## Stato attuale

```
technique_registry (19 entries):
  dapo, dpo, dr_grpo, flowrl, gkd, gold, grpo, kto, orpo, ppo,
  prime, reinforce_pp, reward_modeling, rloo, sdft, sdpo, sft, simpo, vapo

framework_registry (7 entries):
  axolotl, llamafactory, openrlhf, torchtune, trl, unsloth, verl
```
