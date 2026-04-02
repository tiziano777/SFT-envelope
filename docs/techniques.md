# Techniques -- Tecniche di training

> `envelope/techniques/`

Ogni tecnica di training e' implementata come plugin che estende `BaseTechnique`. I plugin sono organizzati per stage in sotto-cartelle dedicate.

## File

| File | Responsabilita' |
|------|----------------|
| `base.py` | ABC `BaseTechnique` |
| `sft/full_sft.py` | Supervised Fine-Tuning |
| `preference/dpo.py` | Direct Preference Optimization |
| `preference/simpo.py` | Simple Preference Optimization |
| `preference/kto.py` | Kahneman-Tversky Optimization |
| `preference/orpo.py` | Odds Ratio Preference Optimization |
| `preference/reward_modeling.py` | Reward Model Training |
| `rl/grpo.py` | Group Relative Policy Optimization |
| `rl/ppo.py` | Proximal Policy Optimization |
| `rl/dapo.py` | Decoupled Alignment via Policy Optimization |
| `rl/vapo.py` | Value-Augmented Policy Optimization |
| `rl/rloo.py` | REINFORCE Leave-One-Out |
| `rl/reinforce_pp.py` | REINFORCE++ |
| `rl/dr_grpo.py` | Dr. GRPO (bias-corrected) |
| `flow/flowrl.py` | FlowRL (distribution matching) |
| `flow/prime.py` | PRIME (process implicit rewards) |
| `distillation/gkd.py` | Generalized Knowledge Distillation |
| `distillation/sdft.py` | Self-Distilled Fine-Tuning |
| `distillation/sdpo.py` | Self-Distilled Preference Optimization |
| `distillation/gold.py` | Generalized Online Distillation |

## ABC: `BaseTechnique`

```python
class BaseTechnique(ABC):
    # Proprieta' (abstract)
    name: str                    # Identificatore univoco (es. "grpo")
    stage: Stage                 # Stage del pipeline (SFT, PREFERENCE, RL)
    display_name: str            # Nome leggibile (es. "Group Relative Policy Optimization")

    # Metodi (abstract)
    default_technique_args() -> dict[str, Any]        # Default per technique_args
    validate_technique_args(args) -> list[str]         # Validazione specifica
    required_dataset_fields() -> list[str]             # Campi dataset richiesti

    # Proprieta' (con default)
    requires_reference_model: bool = False             # Serve un ref model?
    requires_reward: bool = False                      # Serve una reward function?
    requires_teacher_model: bool = False              # Serve un teacher model? (distillazione)

    # Metodo (con default)
    validate_config(config) -> list[str]               # Validazione sul config intero
```

## Dettaglio per tecnica

### Stage 1: SFT

#### `sft` -- Supervised Fine-Tuning
- **Stage**: SFT
- **Reference model**: No
- **Reward**: No
- **Dataset fields**: `prompt`
- **Technique args**: nessuno
- **Note**: La tecnica piu' semplice. Il modello impara direttamente dagli esempi.

### Stage 2: Preference Optimization

#### `dpo` -- Direct Preference Optimization
- **Stage**: PREFERENCE
- **Reference model**: Si'
- **Reward**: No
- **Dataset fields**: `chosen`, `rejected`
- **Technique args**: `beta` (0.1), `dpo_variant` ("standard")
- **Validazione**: `beta > 0`, `dpo_variant in {standard, robust, ipo}`
- **Note**: Ottimizza direttamente dalle preferenze senza una reward function separata.

#### `simpo` -- Simple Preference Optimization
- **Stage**: PREFERENCE
- **Reference model**: No (reference-free)
- **Reward**: No
- **Dataset fields**: `chosen`, `rejected`
- **Technique args**: `beta` (2.0), `gamma` (1.0)
- **Validazione**: `beta > 0`, `gamma >= 0`
- **Note**: Variante semplificata di DPO che non richiede il modello di riferimento.

#### `kto` -- Kahneman-Tversky Optimization
- **Stage**: PREFERENCE
- **Reference model**: Si'
- **Reward**: No
- **Dataset fields**: `label` (binary good/bad)
- **Technique args**: `lambda_w` (1.0), `lambda_l` (1.33)
- **Validazione**: `lambda_w > 0`, `lambda_l > 0`
- **Note**: Basata sulla Prospect Theory. Usa feedback binario (good/bad) invece di coppie preference.

#### `orpo` -- Odds Ratio Preference Optimization
- **Stage**: PREFERENCE
- **Reference model**: No (reference-free)
- **Reward**: No
- **Dataset fields**: `chosen`, `rejected`
- **Technique args**: `lambda_or` (1.0)
- **Validazione**: `lambda_or > 0`
- **Note**: Combina SFT loss con odds ratio in un'unica funzione obiettivo.

#### `reward_modeling` -- Reward Model Training
- **Stage**: PREFERENCE
- **Reference model**: No
- **Reward**: No
- **Dataset fields**: `chosen`, `rejected`
- **Technique args**: nessuno
- **Note**: Addestra un reward model da dati di preferenza. Il modello risultante puo' essere usato come `reward.reward_model` per tecniche RL.

### Stage 3: Reinforcement Learning

#### `grpo` -- Group Relative Policy Optimization
- **Stage**: RL
- **Reference model**: No
- **Reward**: Si'
- **Dataset fields**: `prompt`
- **Technique args**: `num_generations` (16), `max_completion_length` (512), `epsilon` (0.2), `beta` (0.04), `temperature` (1.0), `num_iterations` (1), `scale_rewards` ("group")
- **Validazione**: `num_generations >= 2` (int), `0 < epsilon < 1`, `beta >= 0`, `temperature > 0`
- **Note**: Genera multiple completamenti per prompt, calcola reward per gruppo, e aggiorna la policy con clipping. La tecnica principale per ReasoningRL (DeepSeek-R1).

#### `ppo` -- Proximal Policy Optimization
- **Stage**: RL
- **Reference model**: Si'
- **Reward**: Si'
- **Dataset fields**: `prompt`
- **Technique args**: `clip_range` (0.2), `gae_lambda` (0.95), `vf_coef` (0.5), `num_generations` (8), `max_completion_length` (256)
- **Validazione**: `0 < clip_range < 1`, `0 < gae_lambda <= 1`, `vf_coef > 0`
- **Note**: Il classico algoritmo PPO con GAE e critic loss. Richiede sia un policy model che un value model.

#### `dapo` -- Decoupled Alignment via Policy Optimization
- **Stage**: RL
- **Reference model**: No
- **Reward**: Si'
- **Dataset fields**: `prompt`
- **Technique args**: `num_generations` (16), `max_completion_length` (512), `epsilon_low` (0.2), `epsilon_high` (0.28), `beta` (0.0), `temperature` (1.0), `dynamic_sampling` (True), `overlong_filtering` (True), `token_level_pg` (True)
- **Validazione**: `epsilon_low < epsilon_high`, entrambi in (0,1)
- **Framework**: Solo veRL
- **Note**: Variante GRPO con clip asimmetrico, sampling dinamico, e policy gradient token-level.

#### `vapo` -- Value-Augmented Policy Optimization
- **Stage**: RL
- **Reference model**: No
- **Reward**: Si'
- **Dataset fields**: `prompt`
- **Technique args**: `num_generations` (16), `max_completion_length` (512), `epsilon` (0.2), `beta` (0.04), `critic_lambda` (0.5), `critic_hidden_size` (256)
- **Validazione**: `0 < epsilon < 1`, `beta >= 0`, `0 <= critic_lambda <= 1`, `critic_hidden_size > 0`
- **Framework**: Solo veRL
- **Note**: GRPO con un critic per migliorare la stima dei vantaggi.

#### `rloo` -- REINFORCE Leave-One-Out
- **Stage**: RL
- **Reference model**: No
- **Reward**: Si'
- **Dataset fields**: `prompt`
- **Technique args**: `num_generations` (8), `max_completion_length` (256)
- **Note**: Usa leave-one-out come baseline per ridurre la varianza.

#### `reinforce_pp` -- REINFORCE++
- **Stage**: RL
- **Reference model**: No
- **Reward**: Si'
- **Dataset fields**: `prompt`
- **Technique args**: `clip_range` (0.2), `beta` (0.01), `max_completion_length` (256)
- **Validazione**: `0 < clip_range < 1`, `beta >= 0`
- **Note**: Variante REINFORCE con clipping e KL penalty.

#### `dr_grpo` -- Dr. GRPO (bias-corrected)
- **Stage**: RL
- **Reference model**: No
- **Reward**: Si'
- **Dataset fields**: `prompt`
- **Technique args**: `num_generations` (16), `max_completion_length` (512), `epsilon` (0.2), `beta` (0.04), `bessel_correction` (True), `length_correction` (True)
- **Validazione**: `0 < epsilon < 1`, `beta >= 0`
- **Note**: GRPO con correzione del bias statistico (Bessel correction) e normalizzazione per lunghezza.

#### `flowrl` -- FlowRL (distribution matching)
- **Stage**: RL
- **Reference model**: No
- **Reward**: Si'
- **Dataset fields**: `prompt`
- **Technique args**: `num_generations` (16), `max_completion_length` (512), `beta_flow` (1.0)
- **Validazione**: `beta_flow > 0`
- **Framework**: Solo veRL
- **Note**: Usa flow matching per allineare la distribuzione della policy alla distribuzione target.

#### `prime` -- PRIME (Process Implicit Rewards)
- **Stage**: RL
- **Reference model**: No
- **Reward**: Si'
- **Dataset fields**: `prompt`
- **Technique args**: `num_generations` (16), `max_completion_length` (512), `epsilon` (0.2), `beta` (0.04), `alpha_process` (0.1)
- **Validazione**: `0 < epsilon < 1`, `beta >= 0`, `0 <= alpha_process <= 1`
- **Note**: Costruisce un PRM implicito dai label di outcome per credit assignment piu' denso.

### Stage 4: Distillation

Per la documentazione completa delle tecniche di distillazione, vedi [`docs/distillation.md`](distillation.md).

| Tecnica | Teacher model | Reward | Note |
|---------|--------------|--------|------|
| `gkd` | Si' | No | Generalized Knowledge Distillation, JSD loss |
| `sdft` | No (self-distilled) | No | Self-Distilled Fine-Tuning, supporta privileged_context |
| `sdpo` | No (self-distilled) | Si' | Self-Distilled Preference Optimization |
| `gold` | Si' | No | Generalized Online Distillation, cross-tokenizer via ULD loss |

#### `gkd` -- Generalized Knowledge Distillation
- **Stage**: DISTILLATION
- **Teacher model**: Si'
- **Reward**: No
- **Dataset fields**: `prompt`
- **Technique args**: `jsd_interpolation` (0.5), `temperature` (2.0), `max_completion_length` (512)
- **Note**: JSD loss con interpolazione configurabile tra forward e reverse KL.

#### `sdft` -- Self-Distilled Fine-Tuning
- **Stage**: DISTILLATION
- **Teacher model**: No (self-distilled)
- **Reward**: No
- **Dataset fields**: `prompt`
- **Technique args**: `privileged_context` (False), `temperature` (1.0), `alpha_sdft` (0.5)
- **Note**: Self-distillation senza teacher esterno. Supporta privileged_context.

#### `sdpo` -- Self-Distilled Preference Optimization
- **Stage**: DISTILLATION
- **Teacher model**: No (self-distilled)
- **Reward**: Si'
- **Dataset fields**: `prompt`
- **Technique args**: `beta` (0.1), `temperature` (1.0), `num_generations` (8), `max_completion_length` (512)
- **Note**: Combina self-distillation con ottimizzazione da preferenze.

#### `gold` -- Generalized Online Distillation
- **Stage**: DISTILLATION
- **Teacher model**: Si'
- **Reward**: No
- **Dataset fields**: `prompt`
- **Technique args**: `temperature` (2.0), `uld_loss` (True), `max_completion_length` (512)
- **Note**: Distillazione online con cross-tokenizer distillation tramite ULD loss.

## Organizzazione directory

```
techniques/
├── __init__.py              # discover_plugins importa le sotto-cartelle
├── base.py                  # ABC BaseTechnique
├── sft/
│   ├── __init__.py          # import full_sft
│   └── full_sft.py          # SFTTechnique
├── preference/
│   ├── __init__.py          # import dpo, simpo, kto, orpo, reward_modeling
│   ├── dpo.py               # DPOTechnique
│   ├── simpo.py             # SimPOTechnique
│   ├── kto.py               # KTOTechnique
│   ├── orpo.py              # ORPOTechnique
│   └── reward_modeling.py   # RewardModelingTechnique
├── rl/
│   ├── __init__.py          # import grpo, ppo, dapo, vapo, rloo, reinforce_pp, dr_grpo
│   ├── grpo.py              # GRPOTechnique
│   ├── ppo.py               # PPOTechnique
│   ├── dapo.py              # DAPOTechnique
│   ├── vapo.py              # VAPOTechnique
│   ├── rloo.py              # RLOOTechnique
│   ├── reinforce_pp.py      # REINFORCEPPTechnique
│   └── dr_grpo.py           # DrGRPOTechnique
├── flow/
│   ├── __init__.py          # import flowrl, prime
│   ├── flowrl.py            # FlowRLTechnique
│   └── prime.py             # PRIMETechnique
└── distillation/
    ├── __init__.py          # import gkd, sdft, sdpo, gold
    ├── gkd.py               # GKDTechnique
    ├── sdft.py              # SDFTTechnique
    ├── sdpo.py              # SDPOTechnique
    └── gold.py              # GOLDTechnique
```
