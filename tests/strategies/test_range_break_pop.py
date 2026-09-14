"""
Tests for the Range Break Pop strategy.
"""

import pandas as pd
import pytest

from ta_bot.strategies.range_break_pop import RangeBreakPopStrategy


@pytest.fixture
def sample_data():
    """Create sample OHLCV data for testing."""
    return pd.DataFrame(
        {
            "open": [100, 101, 102, 103, 104],
            "high": [105, 106, 107, 108, 109],
            "low": [95, 96, 97, 98, 99],
            "close": [102, 103, 104, 105, 106],
            "volume": [1000, 1100, 1200, 1300, 1400],
        }
    )


@pytest.fixture
def sample_indicators():
    """Create sample indicators data for testing."""
    return {
        "atr": pd.Series([2, 2, 2, 2, 2]),
        "rsi": pd.Series([50, 50, 50, 50, 50]),
    }


class TestRangeBreakPopStrategy:
    """Test cases for RangeBreakPopStrategy."""

    def test_strategy_initialization(self):
        """Test that strategy initializes correctly."""
        strategy = RangeBreakPopStrategy()
        assert strategy is not None

    def test_analyze_insufficient_data(self):
        """Test strategy with insufficient data."""
        strategy = RangeBreakPopStrategy()
        df = pd.DataFrame({"close": [100]})  # Only one data point
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(df, metadata)
        assert signal is None

    def test_analyze_missing_indicators(self, sample_data):
        """Test strategy with missing indicators."""
        strategy = RangeBreakPopStrategy()
        incomplete_indicators = {
            "atr": pd.Series([2, 2, 2, 2, 2]),
            # Missing rsi
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **incomplete_indicators}

        signal = strategy.analyze(sample_data, metadata)
        assert signal is None

    def test_gate_rejects_signal_missing_tight_range_atr_and_rsi_gates(self):
        """Issue #282: restored production gates reject a candle series that
        `main` at HEAD accepts. Before this fix, `analyze()` only checked
        `range_size(current candle) > atr * 1.5`, `volume > 0` (a tautology),
        and 3-bar momentum. This series has a strong momentum breakout with a
        big current-candle range vs. flat ATR (satisfying `main`'s loosened
        gates) but fails the restored tight-range precondition (prior 10
        candles are NOT within a 2.5% spread), ATR-falling confirmation
        (ATR is flat, not falling), and RSI ~50 confirmation would also not
        even be reached -- all restored here as hard gates."""
        strategy = RangeBreakPopStrategy()
        closes = [100] * 17 + [110, 120, 130]
        highs = [c + 1 for c in closes]
        lows = [c - 1 for c in closes]
        highs[-1] = 140
        lows[-1] = 115
        volumes = [1000] * 20
        df = pd.DataFrame(
            {
                "open": closes,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volumes,
            }
        )
        metadata = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "atr": pd.Series([10] * 20),
            "rsi": pd.Series([50] * 20),
        }

        signal = strategy.analyze(df, metadata)
        assert signal is None

    def test_analyze_no_breakout(self, sample_data, sample_indicators):
        """Test strategy when price does not break above the recent range."""
        strategy = RangeBreakPopStrategy()
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **sample_indicators}

        signal = strategy.analyze(sample_data, metadata)
        assert signal is None
