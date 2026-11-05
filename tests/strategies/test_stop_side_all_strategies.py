"""Property test: no strategy emits a stop on the wrong side of its entry (#375).

Every strategy the signal engine runs is driven over seeded random price series
with volatility shocks, through SignalEngine._run_strategy (so stops the engine
fills in are covered too). A buy must have stop_loss < entry and a sell
stop_loss > entry. The series are deterministic, so a failure is reproducible.
"""

from __future__ import annotations

import collections
import logging

import numpy as np
import pandas as pd
import pytest

from ta_bot.core.signal_engine import SignalEngine

SEEDS = range(150)
BARS = 260
WINDOW_ENDS = range(210, BARS, 5)

# Strategies whose stop could cross the entry before #375 (found by this test).
HAD_WRONG_SIDE_STOPS = {
    "mean_reversion_scalper",
    "ichimoku_cloud_momentum",
    "golden_trend_sync",
    "bollinger_breakout_signals",
    "liquidity_grab_reversal",
    "order_flow_imbalance",
}
# Fixed one by one under #375.
NOT_FIXED_YET = {
    "golden_trend_sync",
    "bollinger_breakout_signals",
    "liquidity_grab_reversal",
    "order_flow_imbalance",
}


def _series(seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    returns = rng.normal(0, 0.006, BARS)
    shocks = rng.random(BARS) < 0.04
    returns[shocks] += rng.normal(0, 0.05, shocks.sum())
    close = 100 * np.exp(np.cumsum(returns))
    spread = np.abs(rng.normal(0, 0.004, BARS)) * close
    open_ = np.r_[close[0], close[:-1]]
    return pd.DataFrame(
        {
            "open": open_,
            "high": np.maximum(open_, close) + spread,
            "low": np.minimum(open_, close) - spread,
            "close": close,
            "volume": rng.lognormal(8, 0.6, BARS) * (1 + 4 * shocks),
        },
        index=pd.date_range("2026-01-01", periods=BARS, freq="15min"),
    )


@pytest.fixture(scope="module")
def outcomes():
    """Per strategy: how many signals it emitted and how many had a wrong-side stop."""
    logging.disable(logging.CRITICAL)
    try:
        engine = SignalEngine()
        emitted: collections.Counter[str] = collections.Counter()
        wrong: dict[str, list[tuple]] = collections.defaultdict(list)
        for seed in SEEDS:
            full = _series(seed)
            for end in WINDOW_ENDS:
                df = full.iloc[:end]
                indicators = engine._calculate_indicators(df)
                price = float(df["close"].iloc[-1])
                for name, strategy in engine.strategies.items():
                    signal = engine._run_strategy(
                        strategy, name, df, "TESTUSDT", "15m", indicators, price
                    )
                    if signal is None or signal.action not in ("buy", "sell"):
                        continue
                    emitted[name] += 1
                    entry = signal.current_price
                    protective = (
                        signal.stop_loss < entry
                        if signal.action == "buy"
                        else signal.stop_loss > entry
                    )
                    if not protective:
                        wrong[name].append(
                            (seed, end, signal.action, entry, signal.stop_loss)
                        )
        return emitted, wrong
    finally:
        logging.disable(logging.NOTSET)


def _strategy_names() -> list:
    return [
        pytest.param(
            name,
            marks=pytest.mark.xfail(strict=True, reason="#375: not fixed yet"),
        )
        if name in NOT_FIXED_YET
        else name
        for name in sorted(SignalEngine().strategies)
    ]


@pytest.mark.parametrize("name", _strategy_names())
def test_no_stop_on_the_wrong_side_of_the_entry(outcomes, name):
    _, wrong = outcomes

    assert wrong.get(name, [])[:3] == []


def test_the_property_is_not_vacuous(outcomes):
    emitted, _ = outcomes

    # Every strategy that ever had a wrong-side stop is exercised here.
    for name in HAD_WRONG_SIDE_STOPS:
        assert emitted[name] > 0, name
    assert sum(emitted.values()) > 1000
