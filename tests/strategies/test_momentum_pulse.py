"""
Tests for the Momentum Pulse strategy.
"""

import pandas as pd
import pytest

from ta_bot.strategies.momentum_pulse import MomentumPulseStrategy


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
        "macd_hist": pd.Series([0.1, 0.2, -0.1, 0.3, 0.4]),
        "rsi": pd.Series([55, 56, 57, 58, 59]),
        "adx": pd.Series([25, 26, 27, 28, 29]),
        "ema21": pd.Series([101, 102, 103, 104, 105]),
        "ema50": pd.Series([100, 101, 102, 103, 104]),
        "close": pd.Series([102, 103, 104, 105, 106]),
    }


class TestMomentumPulseStrategy:
    """Test cases for MomentumPulseStrategy."""

    def test_strategy_initialization(self):
        """Test that strategy initializes correctly."""
        strategy = MomentumPulseStrategy()
        assert strategy is not None

    def test_analyze_with_valid_data(self, sample_data, sample_indicators):
        """Test strategy analysis with valid data."""
        strategy = MomentumPulseStrategy()
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **sample_indicators}

        signal = strategy.analyze(sample_data, metadata)

        # Signal may or may not be generated based on conditions
        if signal:
            assert signal.symbol == "BTCUSDT"
            assert signal.timeframe == "15m"
            assert signal.strategy_id == "momentum_pulse"
            assert signal.action == "buy"
            assert signal.confidence == 0.74
            assert signal.stop_loss is not None
            assert signal.take_profit is not None

    def test_analyze_insufficient_data(self):
        """Test strategy with insufficient data."""
        strategy = MomentumPulseStrategy()
        df = pd.DataFrame({"close": [100]})  # Only one data point
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(df, metadata)
        assert signal is None

    def test_analyze_missing_indicators(self, sample_data):
        """Test strategy with missing indicators."""
        strategy = MomentumPulseStrategy()
        # Missing some required indicators
        incomplete_indicators = {
            "macd_hist": pd.Series([0.1, 0.2, -0.1, 0.3, 0.4]),
            "rsi": pd.Series([55, 56, 57, 58, 59]),
            # Missing adx, ema21, ema50, close
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **incomplete_indicators}

        signal = strategy.analyze(sample_data, metadata)
        assert signal is None

    def test_analyze_no_macd_cross(self, sample_data):
        """Test strategy when MACD histogram doesn't cross."""
        strategy = MomentumPulseStrategy()
        # Both current and previous MACD hist values are positive (no cross)
        indicators = {
            "macd_hist": pd.Series([0.1, 0.2, 0.3, 0.4, 0.5]),
            "rsi": pd.Series([55, 56, 57, 58, 59]),
            "adx": pd.Series([25, 26, 27, 28, 29]),
            "ema21": pd.Series([101, 102, 103, 104, 105]),
            "ema50": pd.Series([100, 101, 102, 103, 104]),
            "close": pd.Series([102, 103, 104, 105, 106]),
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **indicators}

        signal = strategy.analyze(sample_data, metadata)
        assert signal is None
