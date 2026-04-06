"""
Ticket #135 strategy layer coverage tests.

Coverage goals:
- Dedicated parametrized coverage for all strategy classes exported by ta_bot.strategies
- Standardized mock OHLCV generator used by all tests
- Edge cases: insufficient data, missing indicators, extreme volatility
- Signal consistency checks for confidence and TP/SL on actionable signals
"""

from __future__ import annotations

import sys
import types
from datetime import datetime, timedelta, timezone
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc

import numpy as np
import pandas as pd
import pytest

# Provide a lightweight tracer shim for local unit test environments
# where petrosa_otel is not installed.
if "petrosa_otel" not in sys.modules:
    shim = types.ModuleType("petrosa_otel")

    class _Span:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def set_attribute(self, _key, _value):
            return None

    class _Tracer:
        def start_as_current_span(self, _name):
            return _Span()

    shim.get_tracer = lambda _name: _Tracer()
    sys.modules["petrosa_otel"] = shim

import ta_bot.strategies as strategy_pkg
from ta_bot.models.signal import Signal

EXPECTED_STRATEGY_COUNT = 28
COMMON_METADATA = {"symbol": "BTCUSDT", "timeframe": "15m", "period": "15m"}


def _build_mock_ohlcv(
    *,
    length: int = 250,
    seed: int = 42,
    volatility: float = 0.015,
    drift: float = 0.0008,
    missing_tail: int = 0,
) -> pd.DataFrame:
    """Create deterministic mock OHLCV candles for strategy tests."""
    rng = np.random.default_rng(seed)

    timestamps = [
        datetime.now(UTC) - timedelta(minutes=(length - i) * 15) for i in range(length)
    ]

    price = 50_000.0
    closes: list[float] = []
    for _ in range(length):
        shock = rng.normal(drift, volatility)
        price = max(1.0, price * (1.0 + shock))
        closes.append(price)

    close_series = pd.Series(closes, dtype=float)
    open_series = close_series.shift(1).fillna(close_series.iloc[0])
    open_series *= 1 + rng.normal(0, volatility * 0.15, length)

    spread = np.abs(rng.normal(volatility * 0.8, volatility * 0.2, length))
    high_series = np.maximum(open_series, close_series) * (1 + spread)
    low_series = np.minimum(open_series, close_series) * (1 - spread)
    volume_series = rng.uniform(1_000, 5_000, length)

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": open_series,
            "high": high_series,
            "low": low_series,
            "close": close_series,
            "volume": volume_series,
        }
    )

    if missing_tail > 0:
        cols = ["open", "high", "low", "close", "volume"]
        tail_idx = df.tail(missing_tail).index
        df.loc[tail_idx, cols] = np.nan

    return df


STRATEGY_CLASSES = [
    getattr(strategy_pkg, class_name) for class_name in strategy_pkg.__all__
]


@pytest.mark.unit
def test_strategy_registry_has_expected_coverage():
    """Ensure this suite targets all expected strategy classes."""
    assert len(strategy_pkg.__all__) == EXPECTED_STRATEGY_COUNT
    assert len(STRATEGY_CLASSES) == EXPECTED_STRATEGY_COUNT


@pytest.mark.unit
@pytest.mark.parametrize(
    "strategy_cls", STRATEGY_CLASSES, ids=[c.__name__ for c in STRATEGY_CLASSES]
)
def test_each_strategy_smoke_runs_with_standardized_mock_ohlcv(strategy_cls):
    """Each strategy should run against standardized mock candles without crashing."""
    strategy = strategy_cls()
    df = _build_mock_ohlcv(length=250, seed=7)

    signal = strategy.analyze(df, COMMON_METADATA)

    assert signal is None or isinstance(signal, Signal)
    if signal is not None:
        assert signal.strategy_id
        assert signal.symbol == COMMON_METADATA["symbol"]
        assert isinstance(signal.confidence, (int, float))
        assert 0.0 <= signal.confidence <= 1.0


@pytest.mark.unit
@pytest.mark.parametrize(
    "strategy_cls", STRATEGY_CLASSES, ids=[c.__name__ for c in STRATEGY_CLASSES]
)
def test_each_strategy_handles_insufficient_data(strategy_cls):
    """Strategies should gracefully handle insufficient candle data."""
    strategy = strategy_cls()
    df = _build_mock_ohlcv(length=3, seed=11)

    try:
        signal = strategy.analyze(df, COMMON_METADATA)
    except Exception as exc:  # pragma: no cover - explicit failure message
        pytest.fail(f"{strategy_cls.__name__} raised with insufficient data: {exc}")

    assert signal is None or isinstance(signal, Signal)


@pytest.mark.unit
@pytest.mark.parametrize(
    "strategy_cls", STRATEGY_CLASSES, ids=[c.__name__ for c in STRATEGY_CLASSES]
)
def test_each_strategy_handles_missing_indicators_scenario(strategy_cls):
    """Strategies should not crash when indicator inputs are effectively missing."""
    strategy = strategy_cls()
    # Last candles are NaN to simulate unavailable indicators at decision time.
    df = _build_mock_ohlcv(length=250, seed=13, missing_tail=4)

    try:
        signal = strategy.analyze(df, COMMON_METADATA)
    except Exception as exc:  # pragma: no cover - explicit failure message
        pytest.fail(
            f"{strategy_cls.__name__} raised with missing indicators scenario: {exc}"
        )

    assert signal is None or isinstance(signal, Signal)


@pytest.mark.unit
@pytest.mark.parametrize(
    "strategy_cls", STRATEGY_CLASSES, ids=[c.__name__ for c in STRATEGY_CLASSES]
)
def test_each_strategy_handles_extreme_volatility_and_signal_consistency(strategy_cls):
    """Extreme volatility should not crash; generated actionable signals must be complete."""
    strategy = strategy_cls()
    df = _build_mock_ohlcv(length=280, seed=17, volatility=0.18, drift=0.0)

    try:
        signal = strategy.analyze(df, COMMON_METADATA)
    except Exception as exc:  # pragma: no cover - explicit failure message
        pytest.fail(f"{strategy_cls.__name__} raised with extreme volatility: {exc}")

    assert signal is None or isinstance(signal, Signal)
    if signal is None:
        return

    assert isinstance(signal.confidence, (int, float))
    assert 0.0 <= signal.confidence <= 1.0

    if signal.action in {"buy", "sell"}:
        assert signal.stop_loss is not None
        assert signal.take_profit is not None
