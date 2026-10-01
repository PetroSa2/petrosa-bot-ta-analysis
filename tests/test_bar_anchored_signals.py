from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from ta_bot.core.signal_engine import SignalEngine
from ta_bot.models.signal import Signal


class _AlwaysBuy:
    def analyze(self, df, metadata):
        close = float(df["close"].iloc[-1])
        return Signal(
            strategy_id="test_strategy",
            symbol=metadata["symbol"],
            action="buy",
            confidence=0.8,
            current_price=close,
            price=close,
            timeframe=metadata["timeframe"],
            stop_loss=close - 1,
            take_profit=close + 2,
            metadata={"entry_price": close + 10},
        )


def _candles(last_open: datetime) -> pd.DataFrame:
    timestamps = [last_open - timedelta(minutes=5), last_open]
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [99.0, 100.0],
            "high": [101.0, 102.0],
            "low": [98.0, 99.0],
            "close": [100.0, 101.0],
            "volume": [10.0, 12.0],
        }
    )


def _engine() -> SignalEngine:
    engine = SignalEngine(dedupe_cache_size=8)
    engine.strategies = {"test_strategy": _AlwaysBuy()}
    return engine


def test_same_closed_bar_is_emitted_once_and_is_bar_anchored():
    last_open = datetime.now(UTC) - timedelta(minutes=10)
    engine = _engine()
    candles = _candles(last_open)

    first = engine.analyze_candles(candles, "BTCUSDT", "5m")
    second = engine.analyze_candles(candles, "BTCUSDT", "5m")

    assert len(first) == 1
    assert second == []
    assert first[0].bar_open_time == last_open
    assert first[0].bar_close_time == last_open + timedelta(minutes=5)
    assert first[0].metadata["entry_price"] == 101.0
    assert first[0].metadata["reference_price"] == 111.0
    assert len(first[0].signal_key) == 40


def test_forming_last_bar_is_not_used():
    engine = _engine()
    assert engine.analyze_candles(
        _candles(datetime.now(UTC) - timedelta(minutes=2)), "BTCUSDT", "5m"
    ) == []


def test_bar_times_reject_naive_datetimes():
    with pytest.raises(ValueError):
        Signal(
            strategy_id="test",
            symbol="BTCUSDT",
            action="buy",
            confidence=0.8,
            current_price=100,
            price=100,
            bar_open_time=datetime(2026, 1, 1),
        )


def test_restart_reemits_same_deterministic_key():
    last_open = datetime.now(UTC) - timedelta(minutes=10)
    first = _engine().analyze_candles(_candles(last_open), "BTCUSDT", "5m")[0]
    second = _engine().analyze_candles(_candles(last_open), "BTCUSDT", "5m")[0]
    assert first.signal_key == second.signal_key
    assert first.to_dict()["bar_open_time"] == second.to_dict()["bar_open_time"]
