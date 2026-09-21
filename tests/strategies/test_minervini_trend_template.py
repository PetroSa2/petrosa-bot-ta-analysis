"""Tests for the daily-only Minervini trend template strategy."""

import pandas as pd

from ta_bot.strategies.minervini_trend_template import MinerviniTrendTemplateStrategy


def make_rising_candles(periods: int = 265) -> pd.DataFrame:
    closes = pd.Series(range(100, 100 + periods), dtype=float)
    return pd.DataFrame(
        {
            "open": closes - 0.5,
            "high": closes + 1,
            "low": closes - 1,
            "close": closes,
            "volume": 1000,
        }
    )


def test_intraday_candles_are_skipped_before_strategy_calculations():
    strategy = MinerviniTrendTemplateStrategy()

    signal = strategy.analyze(
        make_rising_candles(), {"symbol": "BTCUSDT", "timeframe": "5m"}
    )

    assert signal is None


def test_daily_candles_continue_through_timeframe_gate():
    strategy = MinerviniTrendTemplateStrategy()

    signal = strategy.analyze(
        make_rising_candles(), {"symbol": "BTCUSDT", "timeframe": "1d"}
    )

    assert signal is not None
    assert signal.symbol == "BTCUSDT"
