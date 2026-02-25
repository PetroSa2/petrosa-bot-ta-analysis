"""
Tests for the Mean Reversion Scalper strategy.
"""

import pandas as pd
import pytest

from ta_bot.strategies.mean_reversion_scalper import MeanReversionScalperStrategy


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
        "bb_lower": pd.Series([90, 91, 92, 93, 94]),
        "bb_upper": pd.Series([110, 111, 112, 113, 114]),
        "bb_middle": pd.Series([100, 101, 102, 103, 104]),
        "rsi": pd.Series([30, 35, 40, 45, 50]),
        "close": pd.Series([102, 103, 104, 105, 106]),
    }


class TestMeanReversionScalperStrategy:
    """Test cases for MeanReversionScalperStrategy."""

    def test_strategy_initialization(self):
        """Test that strategy initializes correctly."""
        strategy = MeanReversionScalperStrategy()
        assert strategy is not None

    def test_analyze_with_valid_data(self, sample_data, sample_indicators):
        """Test strategy analysis with valid data."""
        strategy = MeanReversionScalperStrategy()
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **sample_indicators}

        signal = strategy.analyze(sample_data, metadata)

        # Signal may or may not be generated based on conditions
        if signal:
            assert signal.symbol == "BTCUSDT"
            assert signal.timeframe == "15m"
            assert signal.strategy_id == "mean_reversion_scalper"
            assert signal.action in ["buy", "sell"]
            assert signal.confidence >= 0.5
            assert signal.stop_loss is not None
            assert signal.take_profit is not None

    def test_analyze_insufficient_data(self):
        """Test strategy with insufficient data."""
        strategy = MeanReversionScalperStrategy()
        df = pd.DataFrame({"close": [100]})  # Only one data point
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(df, metadata)
        assert signal is None

    def test_analyze_missing_indicators(self, sample_data):
        """Test strategy with missing indicators."""
        strategy = MeanReversionScalperStrategy()
        # Missing some required indicators
        incomplete_indicators = {
            "bb_lower": pd.Series([90, 91, 92, 93, 94]),
            "bb_upper": pd.Series([110, 111, 112, 113, 114]),
            # Missing bb_middle, rsi and close
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **incomplete_indicators}

        signal = strategy.analyze(sample_data, metadata)
        assert signal is None

    def test_analyze_no_mean_reversion_pattern(self, sample_data):
        """Test strategy when no mean reversion pattern is detected."""
        strategy = MeanReversionScalperStrategy()
        # Price near middle band (no extreme)
        df = pd.DataFrame(
            {
                "open": [100, 101, 102, 103, 104],
                "high": [105, 106, 107, 108, 109],
                "low": [95, 96, 97, 98, 99],
                "close": [102, 103, 104, 105, 106],  # Near middle
                "volume": [1000, 1100, 1200, 1300, 1400],
            }
        )

        indicators = {
            "bb_lower": pd.Series([90, 91, 92, 93, 94]),
            "bb_upper": pd.Series([110, 111, 112, 113, 114]),
            "bb_middle": pd.Series([100, 101, 102, 103, 104]),
            "rsi": pd.Series([30, 35, 40, 45, 50]),
            "close": pd.Series([102, 103, 104, 105, 106]),
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **indicators}

        signal = strategy.analyze(df, metadata)
        assert signal is None
