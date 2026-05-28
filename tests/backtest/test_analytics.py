"""Unit tests for backtest.analytics (AC1, AC2, AC3 computation logic)."""

from __future__ import annotations

import pytest

from backtest.analytics import (
    compute_drawdown_envelope,
    compute_edge_estimate,
    compute_sensitivity_analysis,
)
from backtest.artifact import BacktestEvent, DrawdownEnvelope


def _event(
    action: str,
    price: float,
    confidence: float = 0.75,
    idx: int = 0,
) -> BacktestEvent:
    return BacktestEvent(
        decision_id=f"dec_test_{idx:03d}",
        candle_timestamp=f"2026-01-{idx + 1:02d}T00:00:00+00:00",
        action=action,
        confidence=confidence,
        current_price=price,
        metadata={},
    )


# ---------------------------------------------------------------------------
# edge_estimate
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_edge_estimate_empty_events() -> None:
    est = compute_edge_estimate([])
    assert est.trade_count == 0
    assert est.win_rate == 0.0
    assert est.expected_pnl == 0.0
    assert est.sharpe_ratio == 0.0


@pytest.mark.unit
def test_edge_estimate_single_winning_trade() -> None:
    events = [_event("buy", 100.0, idx=0), _event("sell", 110.0, idx=1)]
    est = compute_edge_estimate(events)
    assert est.trade_count == 1
    assert est.win_rate == 1.0
    assert abs(est.expected_pnl - 0.10) < 1e-5  # (110 - 100) / 100


@pytest.mark.unit
def test_edge_estimate_single_losing_trade() -> None:
    events = [_event("buy", 100.0, idx=0), _event("sell", 90.0, idx=1)]
    est = compute_edge_estimate(events)
    assert est.trade_count == 1
    assert est.win_rate == 0.0
    assert abs(est.expected_pnl - (-0.10)) < 1e-5


@pytest.mark.unit
def test_edge_estimate_two_trades_mixed() -> None:
    # Trade 1: +10%, Trade 2: -5%
    events = [
        _event("buy", 100.0, idx=0),
        _event("sell", 110.0, idx=1),
        _event("buy", 110.0, idx=2),
        _event("close", 104.5, idx=3),
    ]
    est = compute_edge_estimate(events)
    assert est.trade_count == 2
    assert est.win_rate == 0.5
    # mean((0.10, -0.05)) = 0.025
    assert abs(est.expected_pnl - 0.025) < 1e-4


@pytest.mark.unit
def test_edge_estimate_unpaired_buy_ignored() -> None:
    # Only one buy with no matching sell → 0 trades
    events = [_event("buy", 100.0, idx=0)]
    est = compute_edge_estimate(events)
    assert est.trade_count == 0


@pytest.mark.unit
def test_edge_estimate_hold_events_skipped() -> None:
    events = [
        _event("buy", 100.0, idx=0),
        _event("hold", 105.0, idx=1),  # should be ignored
        _event("sell", 110.0, idx=2),
    ]
    est = compute_edge_estimate(events)
    assert est.trade_count == 1
    assert abs(est.expected_pnl - 0.10) < 1e-5


# ---------------------------------------------------------------------------
# drawdown_envelope
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_drawdown_envelope_empty() -> None:
    dd = compute_drawdown_envelope([])
    assert dd.p50 == 0.0
    assert dd.p100 == 0.0


@pytest.mark.unit
def test_drawdown_envelope_no_drawdown() -> None:
    # Two winning trades — equity only goes up
    events = [
        _event("buy", 100.0, idx=0),
        _event("sell", 110.0, idx=1),
        _event("buy", 110.0, idx=2),
        _event("sell", 121.0, idx=3),
    ]
    dd = compute_drawdown_envelope(events)
    assert dd.p50 == 0.0
    assert dd.p100 == 0.0


@pytest.mark.unit
def test_drawdown_envelope_losing_trade() -> None:
    events = [
        _event("buy", 100.0, idx=0),
        _event("sell", 80.0, idx=1),  # -20% drawdown
    ]
    dd = compute_drawdown_envelope(events)
    # single trade → p50 == p100
    assert abs(dd.p100 - 0.20) < 1e-5
    assert dd.p50 == dd.p100


# ---------------------------------------------------------------------------
# sensitivity_analysis
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_sensitivity_analysis_empty() -> None:
    sa = compute_sensitivity_analysis([])
    assert sa.parameter == "confidence_threshold"
    assert len(sa.points) == 5  # default 5 thresholds
    for pt in sa.points:
        assert pt.trade_count == 0


@pytest.mark.unit
def test_sensitivity_analysis_filters_by_threshold() -> None:
    # Buy at confidence 0.4, sell at 0.8 — trade is a win (+10%)
    events = [
        _event("buy", 100.0, confidence=0.4, idx=0),
        _event("sell", 110.0, confidence=0.8, idx=1),
    ]
    sa = compute_sensitivity_analysis(events)
    # At threshold 0.0 — both events pass → 1 trade
    pt_0 = next(p for p in sa.points if p.confidence_threshold == 0.0)
    assert pt_0.trade_count == 1

    # At threshold 0.5 — buy (0.4) is filtered out → no paired trade
    pt_50 = next(p for p in sa.points if p.confidence_threshold == 0.50)
    assert pt_50.trade_count == 0


# ---------------------------------------------------------------------------
# max_leverage_envelope (P1.5-AC2 / #252)
# ---------------------------------------------------------------------------


def _dd(p99: float, *, p50: float | None = None, p100: float | None = None):
    """Helper: build a DrawdownEnvelope where only p99 carries semantic weight.

    The other percentiles are filled with consistent placeholders so the
    dataclass invariants (p50 <= p90 <= p99 <= p100) hold; the helper under
    test only reads p99.
    """
    return DrawdownEnvelope(
        p50=p50 if p50 is not None else p99,
        p90=p99,
        p99=p99,
        p100=p100 if p100 is not None else p99,
    )


@pytest.mark.unit
def test_max_leverage_envelope_zero_drawdown_caps_at_operator_max() -> None:
    """AC2 corner case — flat equity curve → producer cannot recommend more
    than the operator's hard cap (no implicit infinity from divide-by-zero)."""
    from backtest.analytics import (
        DEFAULT_OPERATOR_MAX_LEVERAGE,
        compute_max_leverage_envelope,
    )

    bound = compute_max_leverage_envelope([], _dd(0.0))
    assert bound == DEFAULT_OPERATOR_MAX_LEVERAGE


@pytest.mark.unit
def test_max_leverage_envelope_monotone_in_budget() -> None:
    """AC2 monotonicity — more budget → more leverage (until the operator cap)."""
    from backtest.analytics import compute_max_leverage_envelope

    dd = _dd(0.02)  # 2% p99 drawdown
    low = compute_max_leverage_envelope([], dd, budget=0.05)
    high = compute_max_leverage_envelope([], dd, budget=0.10)
    assert high >= low
    # Increasing budget should strictly increase leverage until the cap.
    assert high > low


@pytest.mark.unit
def test_max_leverage_envelope_inverse_monotone_in_drawdown() -> None:
    """AC2 monotonicity — more drawdown → less leverage."""
    from backtest.analytics import compute_max_leverage_envelope

    low_dd = compute_max_leverage_envelope([], _dd(0.01), budget=0.10)
    high_dd = compute_max_leverage_envelope([], _dd(0.05), budget=0.10)
    assert low_dd > high_dd


@pytest.mark.unit
def test_max_leverage_envelope_clipped_at_operator_cap() -> None:
    """AC2 cap — even when budget/p99 would exceed the cap, output stays bounded."""
    from backtest.analytics import compute_max_leverage_envelope

    # budget 1.0 / p99 0.01 = 100 → cap at 10.0
    bound = compute_max_leverage_envelope([], _dd(0.01), budget=1.0, operator_max=10.0)
    assert bound == 10.0


@pytest.mark.unit
def test_max_leverage_envelope_zero_budget_returns_zero() -> None:
    """AC2 invariant — operator can pin the producer to no leverage via budget=0."""
    from backtest.analytics import compute_max_leverage_envelope

    assert compute_max_leverage_envelope([], _dd(0.05), budget=0.0) == 0.0


@pytest.mark.unit
def test_max_leverage_envelope_negative_inputs_clipped_to_safe() -> None:
    """AC2 defensive — operator misconfig with negatives must not produce
    negative leverage or a divide-by-bogus value."""
    from backtest.analytics import compute_max_leverage_envelope

    # Negative budget → treated as 0 → bound = 0
    assert compute_max_leverage_envelope([], _dd(0.05), budget=-0.1) == 0.0
    # Negative operator_max → treated as 0 → bound = 0 (cap)
    assert (
        compute_max_leverage_envelope([], _dd(0.05), budget=0.1, operator_max=-1.0)
        == 0.0
    )


@pytest.mark.unit
def test_max_leverage_envelope_exact_formula_at_simple_inputs() -> None:
    """AC2 formula — when below the operator cap, bound == budget/p99 exactly."""
    from backtest.analytics import compute_max_leverage_envelope

    # 0.10 / 0.02 = 5.0 (below the 10.0 cap)
    bound = compute_max_leverage_envelope([], _dd(0.02), budget=0.10, operator_max=10.0)
    assert abs(bound - 5.0) < 1e-9
