"""
Tests for the EMA Alignment Bearish strategy.

Covers #302: current_close == 0 (degenerate candle) previously reached the
pure-Python divisions at lines 110-121 (price_distance_from_ema8,
price_distance_from_ema80, ema_separation, slope_strength -- all divide by
current_close), raising ZeroDivisionError. The broad `except Exception`
handler at the bottom of analyze() caught it and logged
"Error in EMA Alignment Bearish analysis: float division by zero", silently
disabling the strategy for that candle instead of returning a clean None.
"""

import pandas as pd
import pytest

from ta_bot.strategies.ema_alignment_bearish import EMAAlignmentBearishStrategy


def _declining_ema_series(n: int, start: float, step: float) -> pd.Series:
    """Build a monotonically declining series suitable as a stand-in EMA."""
    return pd.Series([start - step * i for i in range(n)])


@pytest.fixture
def bearish_df():
    """OHLCV data long enough (>= min_periods=125) and shaped so that price
    sits below a declining EMA8/EMA80, satisfying the bearish-alignment
    gates once current_close is non-zero."""
    n = 130
    closes = [200.0 - 0.5 * i for i in range(n)]
    highs = [c + 1.0 for c in closes]
    lows = [c - 1.0 for c in closes]
    return pd.DataFrame(
        {
            "open": closes,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [1000.0] * n,
        }
    )


class TestEMAAlignmentBearishStrategy:
    """Test cases for EMAAlignmentBearishStrategy."""

    def test_strategy_initialization(self):
        strategy = EMAAlignmentBearishStrategy()
        assert strategy is not None
        assert strategy.name == "EMA Alignment Bearish"

    def test_analyze_insufficient_data(self):
        strategy = EMAAlignmentBearishStrategy()
        df = pd.DataFrame({"close": [100.0] * 10, "high": [101.0] * 10})
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(df, metadata)
        assert signal is None

    def test_analyze_zero_current_close_returns_none(self, bearish_df):
        """Issue #302: current_close == 0 must not raise ZeroDivisionError;
        analyze() should return None instead."""
        strategy = EMAAlignmentBearishStrategy()
        df = bearish_df.copy()
        df.loc[df.index[-1], "close"] = 0.0

        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(df, metadata)
        assert signal is None

    def test_analyze_no_bearish_alignment_returns_none(self):
        """Flat/uptrending data has no bearish EMA alignment -> None."""
        strategy = EMAAlignmentBearishStrategy()
        n = 130
        closes = [100.0 + 0.5 * i for i in range(n)]
        df = pd.DataFrame(
            {
                "open": closes,
                "high": [c + 1.0 for c in closes],
                "low": [c - 1.0 for c in closes],
                "close": closes,
                "volume": [1000.0] * n,
            }
        )
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(df, metadata)
        assert signal is None

    def test_analyze_bearish_alignment_generates_sell_signal(self, bearish_df):
        """Sanity check: a genuinely declining series still produces a
        sell signal with a positive current_price (no regression from the
        current_close guard)."""
        strategy = EMAAlignmentBearishStrategy()
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(bearish_df, metadata)

        if signal is not None:
            assert signal.action == "sell"
            assert signal.strategy_id == "ema_alignment_bearish"
            assert signal.current_price > 0
