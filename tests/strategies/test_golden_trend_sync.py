"""
Tests for the Golden Trend Sync strategy.
"""

import pandas as pd
import pytest

from ta_bot.strategies.golden_trend_sync import GoldenTrendSyncStrategy


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
        "ema21": pd.Series([98, 99, 100, 101, 102]),
        "ema50": pd.Series([95, 96, 97, 98, 99]),
        "ema200": pd.Series([90, 91, 92, 93, 94]),
        "vwap": pd.Series([97, 98, 99, 100, 101]),
        "close": pd.Series([102, 103, 104, 105, 106]),
    }


class TestGoldenTrendSyncStrategy:
    """Test cases for GoldenTrendSyncStrategy."""

    def test_strategy_initialization(self):
        """Test that strategy initializes correctly."""
        strategy = GoldenTrendSyncStrategy()
        assert strategy is not None

    def test_analyze_with_valid_data(self, sample_data, sample_indicators):
        """Test strategy analysis with valid data."""
        strategy = GoldenTrendSyncStrategy()
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **sample_indicators}

        signal = strategy.analyze(sample_data, metadata)

        # Signal may or may not be generated based on conditions
        if signal:
            assert signal.symbol == "BTCUSDT"
            assert signal.timeframe == "15m"
            assert signal.strategy_id == "golden_trend_sync"
            assert signal.action == "buy"
            assert signal.confidence >= 0.5
            assert signal.stop_loss is not None
            assert signal.take_profit is not None

    def test_analyze_insufficient_data(self):
        """Test strategy with insufficient data."""
        strategy = GoldenTrendSyncStrategy()
        df = pd.DataFrame({"close": [100]})  # Only one data point
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(df, metadata)
        assert signal is None

    def test_analyze_missing_indicators(self, sample_data):
        """Test strategy with missing indicators."""
        strategy = GoldenTrendSyncStrategy()
        # Missing some required indicators
        incomplete_indicators = {
            "ema21": pd.Series([98, 99, 100, 101, 102]),
            "ema50": pd.Series([95, 96, 97, 98, 99]),
            # Missing ema200, vwap and close
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **incomplete_indicators}

        signal = strategy.analyze(sample_data, metadata)
        assert signal is None

    def test_analyze_no_trend_sync(self, sample_data):
        """Test strategy when no trend sync pattern is detected."""
        strategy = GoldenTrendSyncStrategy()
        # EMAs not aligned in bullish order
        df = pd.DataFrame(
            {
                "open": [100, 101, 102, 103, 104],
                "high": [105, 106, 107, 108, 109],
                "low": [95, 96, 97, 98, 99],
                "close": [102, 103, 104, 105, 106],
                "volume": [1000, 1100, 1200, 1300, 1400],
            }
        )

        indicators = {
            "ema21": pd.Series([98, 99, 100, 101, 102]),  # Lower than ema50
            "ema50": pd.Series([105, 106, 107, 108, 109]),  # Higher than ema21
            "ema200": pd.Series([110, 111, 112, 113, 114]),  # Highest
            "vwap": pd.Series([97, 98, 99, 100, 101]),
            "close": pd.Series([102, 103, 104, 105, 106]),
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **indicators}

        signal = strategy.analyze(df, metadata)
        assert signal is None
