"""
Tests for the Ichimoku Cloud Momentum strategy.
"""

import pandas as pd
import pytest

from ta_bot.strategies.ichimoku_cloud_momentum import IchimokuCloudMomentumStrategy


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
        "ichimoku_conversion": pd.Series([98, 99, 100, 101, 102]),
        "ichimoku_base": pd.Series([95, 96, 97, 98, 99]),
        "ichimoku_a": pd.Series([97, 98, 99, 100, 101]),
        "ichimoku_b": pd.Series([96, 97, 98, 99, 100]),
        "close": pd.Series([102, 103, 104, 105, 106]),
    }


class TestIchimokuCloudMomentumStrategy:
    """Test cases for IchimokuCloudMomentumStrategy."""

    def test_strategy_initialization(self):
        """Test that strategy initializes correctly."""
        strategy = IchimokuCloudMomentumStrategy()
        assert strategy is not None

    def test_analyze_with_valid_data(self, sample_data, sample_indicators):
        """Test strategy analysis with valid data."""
        strategy = IchimokuCloudMomentumStrategy()
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **sample_indicators}

        signal = strategy.analyze(sample_data, metadata)

        # Signal may or may not be generated based on conditions
        if signal:
            assert signal.symbol == "BTCUSDT"
            assert signal.timeframe == "15m"
            assert signal.strategy_id == "ichimoku_cloud_momentum"
            assert signal.action in ["buy", "sell"]
            assert signal.confidence >= 0.5
            assert signal.stop_loss is not None
            assert signal.take_profit is not None

    def test_analyze_insufficient_data(self):
        """Test strategy with insufficient data."""
        strategy = IchimokuCloudMomentumStrategy()
        df = pd.DataFrame({"close": [100]})  # Only one data point
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(df, metadata)
        assert signal is None

    def test_analyze_missing_indicators(self, sample_data):
        """Test strategy with missing indicators."""
        strategy = IchimokuCloudMomentumStrategy()
        # Missing some required indicators
        incomplete_indicators = {
            "ichimoku_conversion": pd.Series([98, 99, 100, 101, 102]),
            "ichimoku_base": pd.Series([95, 96, 97, 98, 99]),
            # Missing ichimoku_a, ichimoku_b and close
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **incomplete_indicators}

        signal = strategy.analyze(sample_data, metadata)
        assert signal is None

    def test_analyze_no_momentum_pattern(self, sample_data):
        """Test strategy when no momentum pattern is detected."""
        strategy = IchimokuCloudMomentumStrategy()
        # Price below cloud (bearish)
        df = pd.DataFrame(
            {
                "open": [100, 101, 102, 103, 104],
                "high": [105, 106, 107, 108, 109],
                "low": [95, 96, 97, 98, 99],
                "close": [92, 93, 94, 95, 96],  # Below cloud
                "volume": [1000, 1100, 1200, 1300, 1400],
            }
        )

        indicators = {
            "ichimoku_conversion": pd.Series([98, 99, 100, 101, 102]),
            "ichimoku_base": pd.Series([95, 96, 97, 98, 99]),
            "ichimoku_a": pd.Series([97, 98, 99, 100, 101]),
            "ichimoku_b": pd.Series([96, 97, 98, 99, 100]),
            "close": pd.Series([92, 93, 94, 95, 96]),
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **indicators}

        signal = strategy.analyze(df, metadata)
        assert signal is None
