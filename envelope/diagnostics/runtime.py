"""Runtime diagnostics for training monitoring.

Self-contained module copied into each generated setup directory as diagnostics.py.
Provides structured actionable warnings during training to detect common issues early.

Two integration points:
- TRLDiagnosticCallback: transformers.TrainerCallback for TRL-based setups
- run_diagnostics(): callable for from_scratch hook integration
"""

from __future__ import annotations

import sys
from collections import deque
from dataclasses import dataclass

# ─── Diagnostic Warning ───


@dataclass
class DiagnosticWarning:
    rule: str
    message: str
    suggestion: str

    def format(self) -> str:
        return f"[ENVELOPE DIAGNOSTIC] {self.rule}: {self.message} {self.suggestion}"


# ─── Diagnostic Rules ───

RL_TECHNIQUES = {
    "grpo", "ppo", "dapo", "vapo", "rloo", "reinforce_pp", "dr_grpo",
    "flowrl", "prime", "sdpo",
}


class DiagnosticState:
    """Tracks training metrics history for stateful diagnostics."""

    def __init__(self) -> None:
        self.initial_loss: float | None = None
        self.low_reward_std_streak: int = 0
        self.throughput_history: deque[float] = deque(maxlen=20)
        self.peak_throughput: float = 0.0
        self._last_warning_step: dict[str, int] = {}
        self._cooldown_steps: int = 50

    def should_warn(self, rule: str, step: int) -> bool:
        """Rate-limit warnings: at most once per cooldown period per rule."""
        last = self._last_warning_step.get(rule, -self._cooldown_steps - 1)
        if step - last >= self._cooldown_steps:
            self._last_warning_step[rule] = step
            return True
        return False


_state = DiagnosticState()


def check_loss_divergence(step: int, metrics: dict, **_kwargs: object) -> DiagnosticWarning | None:
    """Detect loss diverging beyond 10x initial value."""
    loss = metrics.get("loss")
    if loss is None:
        return None

    if _state.initial_loss is None:
        _state.initial_loss = loss
        return None

    if _state.initial_loss > 0 and loss > 10 * _state.initial_loss:
        if _state.should_warn("loss_divergence", step):
            return DiagnosticWarning(
                rule="loss_divergence",
                message=f"Loss diverging: {loss:.4f} (initial: {_state.initial_loss:.4f}).",
                suggestion="Ridurre learning_rate o verificare il dataset.",
            )
    return None


def check_gradient_explosion(step: int, metrics: dict, **_kwargs: object) -> DiagnosticWarning | None:
    """Detect gradient norm exceeding 10x configured max_grad_norm."""
    grad_norm = metrics.get("grad_norm")
    max_grad_norm = metrics.get("max_grad_norm", 1.0)
    if grad_norm is None:
        return None

    if grad_norm > 10 * max_grad_norm:
        if _state.should_warn("gradient_explosion", step):
            return DiagnosticWarning(
                rule="gradient_explosion",
                message=f"Gradient norm {grad_norm:.2f} >> max_grad_norm {max_grad_norm}.",
                suggestion="Ridurre learning_rate o attivare gradient clipping.",
            )
    return None


def check_reward_collapse(step: int, metrics: dict, technique: str = "", **_kwargs: object) -> DiagnosticWarning | None:
    """Detect reward function producing near-zero variance (RL only)."""
    if technique not in RL_TECHNIQUES:
        return None

    reward_std = metrics.get("reward_std") or metrics.get("rewards/std")
    if reward_std is None:
        return None

    if reward_std < 0.01:
        _state.low_reward_std_streak += 1
    else:
        _state.low_reward_std_streak = 0

    if _state.low_reward_std_streak >= 10:
        if _state.should_warn("reward_collapse", step):
            return DiagnosticWarning(
                rule="reward_collapse",
                message=f"Reward std {reward_std:.4f} near zero per {_state.low_reward_std_streak} step.",
                suggestion="Advantage signal collapsed -- verificare la reward function.",
            )
    return None


def check_clip_ratio(step: int, metrics: dict, technique: str = "", **_kwargs: object) -> DiagnosticWarning | None:
    """Detect excessive clipping in PPO-family techniques."""
    if technique not in RL_TECHNIQUES:
        return None

    clip_frac = metrics.get("clip_fraction") or metrics.get("policy/clip_fraction")
    if clip_frac is None:
        return None

    if clip_frac > 0.3:
        if _state.should_warn("clip_ratio", step):
            return DiagnosticWarning(
                rule="clip_ratio",
                message=f"Clip fraction {clip_frac:.0%} troppo alto.",
                suggestion="Ridurre learning_rate per stabilizzare il training.",
            )
    return None


def check_kl_divergence(step: int, metrics: dict, technique: str = "", **_kwargs: object) -> DiagnosticWarning | None:
    """Detect excessive KL divergence from reference policy."""
    if technique not in RL_TECHNIQUES:
        return None

    kl = metrics.get("kl") or metrics.get("kl_divergence") or metrics.get("objective/kl")
    if kl is None:
        return None

    if kl > 10.0:
        if _state.should_warn("kl_divergence", step):
            return DiagnosticWarning(
                rule="kl_divergence",
                message=f"KL divergence {kl:.2f} troppo alta.",
                suggestion="Policy drift eccessivo -- ridurre lr o aumentare beta/kl_coeff.",
            )
    return None


def check_throughput_degradation(
    step: int, metrics: dict, **_kwargs: object,
) -> DiagnosticWarning | None:
    """Detect >50% throughput drop from peak, suggesting I/O or memory pressure."""
    samples_per_sec = metrics.get("train_samples_per_second") or metrics.get("samples_per_second")
    if samples_per_sec is None:
        return None

    _state.throughput_history.append(samples_per_sec)
    _state.peak_throughput = max(_state.peak_throughput, samples_per_sec)

    if len(_state.throughput_history) >= 5 and _state.peak_throughput > 0:
        current_avg = sum(list(_state.throughput_history)[-5:]) / 5
        if current_avg < 0.5 * _state.peak_throughput:
            if _state.should_warn("throughput_degradation", step):
                return DiagnosticWarning(
                    rule="throughput_degradation",
                    message=f"Throughput {current_avg:.1f} smp/s (peak: {_state.peak_throughput:.1f}).",
                    suggestion="Possibile bottleneck I/O o memory pressure.",
                )
    return None


ALL_RULES = [
    check_loss_divergence,
    check_gradient_explosion,
    check_reward_collapse,
    check_clip_ratio,
    check_kl_divergence,
    check_throughput_degradation,
]


# ─── Public API ───


def run_diagnostics(step: int, metrics: dict, technique: str = "") -> list[DiagnosticWarning]:
    """Run all diagnostic rules and print any warnings. Returns emitted warnings."""
    warnings = []
    for rule_fn in ALL_RULES:
        w = rule_fn(step, metrics, technique=technique)
        if w is not None:
            warnings.append(w)
            print(w.format(), file=sys.stderr, flush=True)
    return warnings


def reset_state() -> None:
    """Reset diagnostic state (useful for testing)."""
    global _state
    _state = DiagnosticState()


# ─── TRL Integration (TrainerCallback) ───

try:
    from transformers import TrainerCallback, TrainerControl, TrainerState, TrainingArguments

    class TRLDiagnosticCallback(TrainerCallback):
        """Transformers callback that runs envelope diagnostics on each log step."""

        def __init__(self, technique: str = "") -> None:
            self.technique = technique

        def on_log(
            self,
            args: TrainingArguments,
            state: TrainerState,
            control: TrainerControl,
            logs: dict | None = None,
            **kwargs: object,
        ) -> None:
            if logs is not None:
                run_diagnostics(
                    step=state.global_step,
                    metrics=logs,
                    technique=self.technique,
                )

except ImportError:
    # transformers not installed — TRL callback not available, from_scratch uses run_diagnostics directly
    pass
