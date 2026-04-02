"""Unit tests for envelope/diagnostics/runtime.py -- runtime diagnostic checks."""

from __future__ import annotations

import pytest

from envelope.diagnostics.runtime import (
    check_loss_divergence,
    check_gradient_explosion,
    check_reward_collapse,
    check_clip_ratio,
    check_kl_divergence,
    check_throughput_degradation,
    run_diagnostics,
    reset_state,
    DiagnosticState,
    DiagnosticWarning,
)


# ---------------------------------------------------------------------------
# Autouse fixture to reset state before each test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_diagnostic_state():
    """Reset diagnostic state before each test for isolation."""
    reset_state()
    yield
    reset_state()


# ---------------------------------------------------------------------------
# DiagnosticWarning
# ---------------------------------------------------------------------------


class TestDiagnosticWarning:
    def test_format_contains_rule(self):
        w = DiagnosticWarning(rule="test_rule", message="msg", suggestion="sug")
        formatted = w.format()
        assert "test_rule" in formatted

    def test_format_contains_message(self):
        w = DiagnosticWarning(rule="r", message="the message", suggestion="s")
        assert "the message" in w.format()

    def test_format_contains_suggestion(self):
        w = DiagnosticWarning(rule="r", message="m", suggestion="the suggestion")
        assert "the suggestion" in w.format()

    def test_format_contains_prefix(self):
        w = DiagnosticWarning(rule="r", message="m", suggestion="s")
        assert "[ENVELOPE DIAGNOSTIC]" in w.format()


# ---------------------------------------------------------------------------
# check_loss_divergence
# ---------------------------------------------------------------------------


class TestLossDivergence:
    def test_first_call_returns_none(self):
        """First call sets initial loss and returns None."""
        result = check_loss_divergence(step=1, metrics={"loss": 2.0})
        assert result is None

    def test_loss_within_threshold_returns_none(self):
        """Loss within 10x initial should not trigger a warning."""
        check_loss_divergence(step=1, metrics={"loss": 1.0})
        result = check_loss_divergence(step=2, metrics={"loss": 9.0})
        assert result is None

    def test_loss_exceeds_threshold_returns_warning(self):
        """Loss > 10x initial should return a warning."""
        check_loss_divergence(step=1, metrics={"loss": 1.0})
        result = check_loss_divergence(step=2, metrics={"loss": 15.0})
        assert result is not None
        assert isinstance(result, DiagnosticWarning)
        assert result.rule == "loss_divergence"

    def test_no_loss_in_metrics_returns_none(self):
        result = check_loss_divergence(step=1, metrics={})
        assert result is None

    def test_reset_clears_initial_loss(self):
        """After reset, the next call should set a new initial loss."""
        check_loss_divergence(step=1, metrics={"loss": 1.0})
        reset_state()
        # Now 100.0 becomes the new initial; no divergence
        check_loss_divergence(step=2, metrics={"loss": 100.0})
        result = check_loss_divergence(step=3, metrics={"loss": 500.0})
        assert result is None  # 500 < 10 * 100


# ---------------------------------------------------------------------------
# check_gradient_explosion
# ---------------------------------------------------------------------------


class TestGradientExplosion:
    def test_within_threshold_returns_none(self):
        result = check_gradient_explosion(step=1, metrics={"grad_norm": 5.0, "max_grad_norm": 1.0})
        assert result is None

    def test_exceeds_threshold_returns_warning(self):
        result = check_gradient_explosion(step=1, metrics={"grad_norm": 15.0, "max_grad_norm": 1.0})
        assert result is not None
        assert isinstance(result, DiagnosticWarning)
        assert result.rule == "gradient_explosion"

    def test_missing_grad_norm_returns_none(self):
        result = check_gradient_explosion(step=1, metrics={"max_grad_norm": 1.0})
        assert result is None

    def test_default_max_grad_norm(self):
        """When max_grad_norm is not in metrics, default (1.0) is used."""
        result = check_gradient_explosion(step=1, metrics={"grad_norm": 15.0})
        assert result is not None


# ---------------------------------------------------------------------------
# check_reward_collapse
# ---------------------------------------------------------------------------


class TestRewardCollapse:
    def test_non_rl_technique_returns_none(self):
        result = check_reward_collapse(step=1, metrics={"reward_std": 0.001}, technique="sft")
        assert result is None

    def test_rl_technique_high_std_returns_none(self):
        result = check_reward_collapse(step=1, metrics={"reward_std": 0.5}, technique="grpo")
        assert result is None

    def test_rl_technique_low_std_under_threshold_steps(self):
        """Low reward_std for fewer than 10 steps should not trigger."""
        for i in range(9):
            result = check_reward_collapse(step=i, metrics={"reward_std": 0.001}, technique="grpo")
        assert result is None

    def test_rl_technique_low_std_at_threshold_steps(self):
        """Low reward_std for >= 10 consecutive steps should trigger."""
        result = None
        for i in range(10):
            result = check_reward_collapse(step=i, metrics={"reward_std": 0.001}, technique="grpo")
        assert result is not None
        assert isinstance(result, DiagnosticWarning)
        assert result.rule == "reward_collapse"

    def test_streak_resets_on_high_std(self):
        """A high reward_std reading should reset the low-std streak."""
        for i in range(8):
            check_reward_collapse(step=i, metrics={"reward_std": 0.001}, technique="grpo")
        # Break the streak
        check_reward_collapse(step=8, metrics={"reward_std": 0.5}, technique="grpo")
        # Start over -- need another 10 consecutive
        for i in range(9, 18):
            result = check_reward_collapse(step=i, metrics={"reward_std": 0.001}, technique="grpo")
        assert result is None  # Only 9 consecutive after reset


# ---------------------------------------------------------------------------
# check_clip_ratio
# ---------------------------------------------------------------------------


class TestClipRatio:
    def test_non_rl_technique_returns_none(self):
        result = check_clip_ratio(step=1, metrics={"clip_fraction": 0.9}, technique="sft")
        assert result is None

    def test_clip_fraction_below_threshold(self):
        result = check_clip_ratio(step=1, metrics={"clip_fraction": 0.2}, technique="grpo")
        assert result is None

    def test_clip_fraction_at_threshold(self):
        result = check_clip_ratio(step=1, metrics={"clip_fraction": 0.3}, technique="grpo")
        assert result is None

    def test_clip_fraction_above_threshold(self):
        result = check_clip_ratio(step=1, metrics={"clip_fraction": 0.5}, technique="grpo")
        assert result is not None
        assert isinstance(result, DiagnosticWarning)
        assert result.rule == "clip_ratio"


# ---------------------------------------------------------------------------
# check_kl_divergence
# ---------------------------------------------------------------------------


class TestKLDivergence:
    def test_non_rl_technique_returns_none(self):
        result = check_kl_divergence(step=1, metrics={"kl": 50.0}, technique="sft")
        assert result is None

    def test_kl_below_threshold(self):
        result = check_kl_divergence(step=1, metrics={"kl": 5.0}, technique="grpo")
        assert result is None

    def test_kl_at_threshold(self):
        result = check_kl_divergence(step=1, metrics={"kl": 10.0}, technique="grpo")
        assert result is None

    def test_kl_above_threshold(self):
        result = check_kl_divergence(step=1, metrics={"kl": 15.0}, technique="grpo")
        assert result is not None
        assert isinstance(result, DiagnosticWarning)
        assert result.rule == "kl_divergence"


# ---------------------------------------------------------------------------
# check_throughput_degradation
# ---------------------------------------------------------------------------


class TestThroughputDegradation:
    def test_fewer_than_five_data_points_returns_none(self):
        """Not enough history to compare -- should return None."""
        for i in range(4):
            result = check_throughput_degradation(step=i, metrics={"train_samples_per_second": 100.0})
        assert result is None

    def test_current_above_half_peak_returns_none(self):
        """Throughput above 50% of peak should not trigger."""
        for i in range(5):
            check_throughput_degradation(step=i, metrics={"train_samples_per_second": 100.0})
        result = check_throughput_degradation(step=5, metrics={"train_samples_per_second": 60.0})
        assert result is None

    def test_current_below_half_peak_returns_warning(self):
        """Throughput below 50% of peak should trigger a warning."""
        # Build up peak at 100
        for i in range(5):
            check_throughput_degradation(step=i, metrics={"train_samples_per_second": 100.0})
        # Drop to well below 50% -- collect all results to find the first warning
        results = []
        for i in range(5):
            r = check_throughput_degradation(step=100 + i, metrics={"train_samples_per_second": 10.0})
            if r is not None:
                results.append(r)
        assert len(results) > 0
        assert isinstance(results[0], DiagnosticWarning)
        assert results[0].rule == "throughput_degradation"

    def test_no_metric_returns_none(self):
        result = check_throughput_degradation(step=1, metrics={})
        assert result is None


# ---------------------------------------------------------------------------
# run_diagnostics
# ---------------------------------------------------------------------------


class TestRunDiagnostics:
    def test_empty_metrics_no_warnings(self):
        warnings = run_diagnostics(step=1, metrics={})
        assert warnings == []

    def test_multiple_triggering_metrics(self):
        """Multiple rules should fire in a single call."""
        # First, set initial loss
        run_diagnostics(step=1, metrics={"loss": 1.0})
        # Now trigger loss_divergence + gradient_explosion
        warnings = run_diagnostics(
            step=2,
            metrics={
                "loss": 100.0,
                "grad_norm": 50.0,
                "max_grad_norm": 1.0,
            },
        )
        rules = {w.rule for w in warnings}
        assert "loss_divergence" in rules
        assert "gradient_explosion" in rules

    def test_prints_to_stderr(self, capsys):
        """Warnings should be printed to stderr."""
        run_diagnostics(step=1, metrics={"loss": 1.0})
        run_diagnostics(step=2, metrics={"loss": 100.0})
        captured = capsys.readouterr()
        assert "[ENVELOPE DIAGNOSTIC]" in captured.err


# ---------------------------------------------------------------------------
# DiagnosticState
# ---------------------------------------------------------------------------


class TestDiagnosticState:
    def test_should_warn_first_call(self):
        state = DiagnosticState()
        assert state.should_warn("test_rule", step=0) is True

    def test_should_warn_within_cooldown(self):
        state = DiagnosticState()
        state.should_warn("test_rule", step=0)
        assert state.should_warn("test_rule", step=10) is False

    def test_should_warn_after_cooldown(self):
        state = DiagnosticState()
        state.should_warn("test_rule", step=0)
        # Default cooldown is 50 steps
        assert state.should_warn("test_rule", step=50) is True

    def test_different_rules_independent(self):
        state = DiagnosticState()
        state.should_warn("rule_a", step=0)
        # Different rule should be independent
        assert state.should_warn("rule_b", step=0) is True


# ---------------------------------------------------------------------------
# reset_state
# ---------------------------------------------------------------------------


class TestResetState:
    def test_clears_loss_divergence(self):
        """After triggering a warning, reset should clear everything."""
        check_loss_divergence(step=1, metrics={"loss": 1.0})
        result = check_loss_divergence(step=2, metrics={"loss": 100.0})
        assert result is not None  # triggered

        reset_state()

        # After reset, 100.0 becomes new initial -- no divergence
        check_loss_divergence(step=3, metrics={"loss": 100.0})
        result = check_loss_divergence(step=4, metrics={"loss": 500.0})
        assert result is None  # 500 < 10 * 100

    def test_clears_reward_streak(self):
        """reset_state should clear the low_reward_std_streak."""
        for i in range(9):
            check_reward_collapse(step=i, metrics={"reward_std": 0.001}, technique="grpo")
        reset_state()
        # After reset, streak starts at 0 -- 1 step is not enough
        result = check_reward_collapse(step=10, metrics={"reward_std": 0.001}, technique="grpo")
        assert result is None

    def test_clears_throughput_history(self):
        """reset_state should clear throughput history and peak."""
        for i in range(5):
            check_throughput_degradation(step=i, metrics={"train_samples_per_second": 100.0})
        reset_state()
        # After reset, not enough history
        result = check_throughput_degradation(step=6, metrics={"train_samples_per_second": 1.0})
        assert result is None

    def test_clears_cooldown(self):
        """reset_state should clear warning cooldowns."""
        # Trigger a warning that sets cooldown
        check_loss_divergence(step=1, metrics={"loss": 1.0})
        check_loss_divergence(step=2, metrics={"loss": 100.0})

        reset_state()

        # After reset, first call sets initial, second should trigger immediately
        check_loss_divergence(step=3, metrics={"loss": 1.0})
        result = check_loss_divergence(step=4, metrics={"loss": 100.0})
        assert result is not None
