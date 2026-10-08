"""Signals anchor on the candles data-manager really serves, and are never dropped for want of an anchor
(petrosa-bot-ta-analysis#364).

Since rollout r109 every signal was skipped: data-manager serves candle timestamps as ISO strings with no
timezone (``2026-10-08T00:30:00``, UTC), data_manager_client turns them into a naive DatetimeIndex, and the
anchor treated a naive timestamp as unknown.
"""

import logging
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
            metadata={},
        )


def engine() -> SignalEngine:
    e = SignalEngine(dedupe_cache_size=8)
    e.strategies = {"test_strategy": _AlwaysBuy()}
    return e


def data_manager_frame(last_open: datetime, minutes: int) -> pd.DataFrame:
    """Built exactly as data_manager_client does from the live ``/data/candles`` rows: ISO strings with no
    timezone, ``pd.to_datetime`` on the column, sorted, ``set_index("timestamp")``."""
    rows = [
        {
            "timestamp": (last_open - timedelta(minutes=minutes * i)).strftime(
                "%Y-%m-%dT%H:%M:%S"
            ),
            "open": "100.0",
            "high": "102.0",
            "low": "99.0",
            "close": "101.0",
            "volume": "12.0",
            "quote_volume": "1200.0",
            "trades_count": 10,
        }
        for i in range(2)
    ]
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    return df.sort_values("timestamp").set_index("timestamp")


PERIODS = [("5m", 5), ("15m", 15), ("30m", 30), ("1h", 60), ("4h", 240), ("1d", 1440)]


@pytest.mark.parametrize(("period", "minutes"), PERIODS)
def test_a_naive_utc_index_as_data_manager_serves_it_anchors(period, minutes):
    last_open = (datetime.now(UTC) - timedelta(minutes=minutes * 2)).replace(
        second=0, microsecond=0, tzinfo=None
    )
    frame = data_manager_frame(last_open, minutes)
    assert frame.index.tz is None  # the live shape
    signals = engine().analyze_candles(frame, "BTCUSDT", period)
    assert len(signals) == 1
    expected = last_open.replace(tzinfo=UTC)
    assert signals[0].bar_open_time == expected
    assert signals[0].bar_close_time == expected + timedelta(minutes=minutes)
    assert len(signals[0].signal_key) == 40


def test_a_naive_timestamp_column_anchors_too():
    last_open = (datetime.now(UTC) - timedelta(minutes=30)).replace(
        second=0, microsecond=0, tzinfo=None
    )
    frame = data_manager_frame(last_open, 5).reset_index()
    assert not isinstance(frame.index, pd.DatetimeIndex)
    signals = engine().analyze_candles(frame, "BTCUSDT", "5m")
    assert len(signals) == 1
    assert signals[0].bar_open_time == last_open.replace(tzinfo=UTC)


def test_the_still_forming_candle_is_still_skipped_with_a_naive_index():
    last_open = (datetime.now(UTC) - timedelta(minutes=2)).replace(tzinfo=None)
    assert (
        engine().analyze_candles(data_manager_frame(last_open, 5), "BTCUSDT", "5m")
        == []
    )


def test_the_same_closed_bar_is_still_emitted_once_with_a_naive_index():
    last_open = (datetime.now(UTC) - timedelta(minutes=30)).replace(
        second=0, microsecond=0, tzinfo=None
    )
    e = engine()
    frame = data_manager_frame(last_open, 5)
    assert len(e.analyze_candles(frame, "BTCUSDT", "5m")) == 1
    assert e.analyze_candles(frame, "BTCUSDT", "5m") == []


@pytest.mark.parametrize("period", ["1w", "", "5x", "m", "abc"])
def test_an_unsupported_period_publishes_without_an_anchor_and_says_why(period, caplog):
    last_open = (datetime.now(UTC) - timedelta(minutes=30)).replace(
        second=0, microsecond=0, tzinfo=None
    )
    with caplog.at_level(logging.WARNING, logger="ta_bot.core.signal_engine"):
        signals = engine().analyze_candles(
            data_manager_frame(last_open, 5), "BTCUSDT", period
        )
    assert len(signals) == 1  # never dropped
    signal = signals[0]
    assert signal.bar_open_time is None and signal.signal_key is None
    assert "bar_open_time" not in signal.to_dict()
    text = caplog.text
    assert "Publishing signal without a bar anchor" in text
    assert f"period={period!r}" in text
    assert "index_type=DatetimeIndex" in text and "columns=" in text


def test_a_frame_without_any_timestamp_publishes_without_an_anchor(caplog):
    frame = pd.DataFrame(
        {
            "open": [100.0],
            "high": [102.0],
            "low": [99.0],
            "close": [101.0],
            "volume": [1.0],
        }
    )
    with caplog.at_level(logging.WARNING, logger="ta_bot.core.signal_engine"):
        signals = engine().analyze_candles(frame, "BTCUSDT", "5m")
    assert len(signals) == 1 and signals[0].bar_open_time is None
    assert "Publishing signal without a bar anchor" in caplog.text
    assert "index_type=RangeIndex" in caplog.text


def test_a_missing_timestamp_value_publishes_without_an_anchor():
    frame = pd.DataFrame(
        {
            "timestamp": [pd.NaT],
            "open": [100.0],
            "high": [102.0],
            "low": [99.0],
            "close": [101.0],
            "volume": [1.0],
        }
    )
    signals = engine().analyze_candles(frame, "BTCUSDT", "5m")
    assert len(signals) == 1 and signals[0].bar_open_time is None


def test_an_aware_index_keeps_working():
    last_open = (datetime.now(UTC) - timedelta(minutes=30)).replace(
        second=0, microsecond=0
    )
    frame = data_manager_frame(last_open.replace(tzinfo=None), 5)
    frame.index = frame.index.tz_localize("UTC")
    signals = engine().analyze_candles(frame, "BTCUSDT", "5m")
    assert len(signals) == 1 and signals[0].bar_open_time == last_open


def test_a_non_utc_aware_index_is_converted_to_utc():
    last_open = (datetime.now(UTC) - timedelta(minutes=30)).replace(
        second=0, microsecond=0
    )
    frame = data_manager_frame(last_open.replace(tzinfo=None), 5)
    frame.index = frame.index.tz_localize("UTC").tz_convert("Asia/Tokyo")
    signals = engine().analyze_candles(frame, "BTCUSDT", "5m")
    assert signals[0].bar_open_time == last_open
