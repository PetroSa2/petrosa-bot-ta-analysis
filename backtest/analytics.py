"""Analytic computation for characterization artifacts (P3.2-v2 / FR3).

All functions operate on a sequence of ``BacktestEvent`` objects and return
the corresponding analytic dataclasses.  No I/O, no OTel metrics — pure
computation so downstream consumers (engine, tests, scripts) can call them
without side effects.

Trade pairing model
-------------------
Events are scanned left-to-right.  A "long" position opens on the first
``buy`` action and closes on the next ``sell`` or ``close`` action.  The
return for each pair is::

    ret = (exit_price - entry_price) / entry_price

Unpaired events at the end of the sequence are discarded (open position at
backtest horizon — no realised P&L).  If fewer than two events are present
or no trades can be paired, sensible zero-return defaults are returned so
callers never receive None from these functions.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence

from backtest.artifact import (
    BacktestEvent,
    DrawdownEnvelope,
    EdgeEstimate,
    SensitivityAnalysis,
    SensitivityPoint,
)

_SENSITIVITY_THRESHOLDS = (0.0, 0.30, 0.50, 0.70, 0.90)

# P1.5-AC2 (#252) — defaults for the max-leverage envelope helper. The operator
# can override these per-strategy in the persistence path; the values here are
# the conservative producer-side fallbacks used when the artifact is generated
# without an explicit operator budget. Operator-configurable bounds + versioning
# is petrosa-data-manager#182 (separate child story under EPIC #691).
DEFAULT_OPERATOR_DRAWDOWN_BUDGET = 0.10  # 10% drawdown budget — safe default
DEFAULT_OPERATOR_MAX_LEVERAGE = 10.0  # P1.5 absolute cap on producer recommendation


def _pair_trades(events: Sequence[BacktestEvent]) -> list[float]:
    """Return per-trade returns (fraction) for consecutive buy→sell/close pairs."""
    returns: list[float] = []
    entry_price: float | None = None
    entry_action: str | None = None

    for ev in events:
        action = ev.action.lower()
        if action == "buy" and entry_price is None:
            entry_price = ev.current_price
            entry_action = "buy"
        elif action in {"sell", "close"} and entry_price is not None:
            if entry_action == "buy" and entry_price > 0:
                returns.append((ev.current_price - entry_price) / entry_price)
            entry_price = None
            entry_action = None
        # "hold" events and repeated same-side events are ignored

    return returns


def compute_edge_estimate(events: Sequence[BacktestEvent]) -> EdgeEstimate:
    """Compute per-trade edge metrics from the events list."""
    returns = _pair_trades(events)
    if not returns:
        return EdgeEstimate(
            expected_pnl=0.0,
            win_rate=0.0,
            sharpe_ratio=0.0,
            trade_count=0,
        )

    mean_ret = statistics.mean(returns)
    wins = sum(1 for r in returns if r > 0)
    win_rate = wins / len(returns)

    std_ret = statistics.stdev(returns) if len(returns) > 1 else 0.0
    sharpe = (mean_ret / std_ret) if std_ret > 0 else 0.0
    # Clamp to avoid extreme values from tiny sample sizes
    sharpe = max(-10.0, min(10.0, sharpe))

    return EdgeEstimate(
        expected_pnl=round(mean_ret, 6),
        win_rate=round(win_rate, 4),
        sharpe_ratio=round(sharpe, 4),
        trade_count=len(returns),
    )


def compute_drawdown_envelope(events: Sequence[BacktestEvent]) -> DrawdownEnvelope:
    """Simulate an equity curve and return drawdown percentiles."""
    returns = _pair_trades(events)
    if not returns:
        return DrawdownEnvelope(p50=0.0, p90=0.0, p99=0.0, p100=0.0)

    # Build cumulative equity curve starting at 1.0
    equity = 1.0
    peak = equity
    drawdowns: list[float] = []
    for ret in returns:
        equity *= 1.0 + ret
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0.0
        drawdowns.append(dd)

    drawdowns.sort()
    n = len(drawdowns)

    def _pct(p: float) -> float:
        idx = min(int(math.ceil(p * n)) - 1, n - 1)
        return round(drawdowns[max(0, idx)], 6)

    return DrawdownEnvelope(
        p50=_pct(0.50),
        p90=_pct(0.90),
        p99=_pct(0.99),
        p100=round(max(drawdowns), 6),
    )


def _edge_at_threshold(
    events: Sequence[BacktestEvent], threshold: float
) -> SensitivityPoint:
    filtered = [e for e in events if e.confidence >= threshold]
    edge = compute_edge_estimate(filtered)
    return SensitivityPoint(
        confidence_threshold=threshold,
        win_rate=edge.win_rate,
        expected_pnl=edge.expected_pnl,
        trade_count=edge.trade_count,
    )


def compute_sensitivity_analysis(
    events: Sequence[BacktestEvent],
    thresholds: Sequence[float] = _SENSITIVITY_THRESHOLDS,
) -> SensitivityAnalysis:
    """Sweep confidence thresholds and report how edge changes."""
    points = tuple(_edge_at_threshold(events, t) for t in thresholds)
    return SensitivityAnalysis(parameter="confidence_threshold", points=points)


def compute_max_leverage_envelope(
    events: Sequence[BacktestEvent],
    drawdown_envelope: DrawdownEnvelope,
    budget: float = DEFAULT_OPERATOR_DRAWDOWN_BUDGET,
    operator_max: float = DEFAULT_OPERATOR_MAX_LEVERAGE,
) -> float:
    """P1.5-AC2 (#252) — analytic upper bound on leverage from the drawdown envelope.

    Derives the max leverage at which the strategy's characterized 99th-percentile
    drawdown stays inside the operator's drawdown budget::

        leverage_bound = budget / drawdown_envelope.p99

    The returned value is clipped to ``operator_max`` so a near-zero drawdown
    cannot recommend unbounded leverage. ``events`` is accepted to keep the
    helper's signature symmetric with ``compute_edge_estimate`` /
    ``compute_drawdown_envelope`` (the parent EPIC's per-artifact callback
    convention) and is reserved for future per-event refinements; the current
    formula reads only the already-characterized ``drawdown_envelope``.

    Properties (locked by unit tests in tests/backtest/test_analytics.py):
      - Monotone in budget: more budget → more leverage (until the cap).
      - Inverse-monotone in p99 drawdown: more drawdown → less leverage.
      - Zero-drawdown floor: when ``drawdown_envelope.p99 <= 0`` the bound is
        ``operator_max`` (cannot divide by zero, and a flat equity curve is a
        characterization artifact of a strategy with no realised trades, not
        a license for infinite leverage).
      - Returns 0.0 when ``budget <= 0`` (operator has forbidden any drawdown).

    Inputs must be non-negative: a negative ``budget`` or ``operator_max`` is
    clipped to zero before the formula runs. The output is always
    ``0.0 <= result <= operator_max``.
    """
    # ``events`` is intentionally unused on the current code path — the
    # signature accepts it for forward-compat with per-event refinements
    # (e.g. tail-conditioning on the equity-curve shape) the EPIC may pull in
    # later without churning the public API.
    _ = events

    safe_budget = max(0.0, float(budget))
    safe_cap = max(0.0, float(operator_max))
    if safe_budget == 0.0:
        return 0.0
    p99 = float(drawdown_envelope.p99)
    if p99 <= 0.0:
        return safe_cap
    bound = safe_budget / p99
    return min(safe_cap, bound)
