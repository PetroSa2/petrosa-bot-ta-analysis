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
