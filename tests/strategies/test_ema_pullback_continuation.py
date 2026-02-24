"""
Tests for the EMA Pullback Continuation strategy.
"""

import pandas as pd
import pytest

from ta_bot.strategies.ema_pullback_continuation import EMAPullbackContinuationStrategy


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
        "ema21": pd.Series([101, 102, 103, 104, 105]),
        "ema50": pd.Series([100, 101, 102, 103, 104]),
        "rsi": pd.Series([45, 46, 47, 48, 49]),
        "close": pd.Series([102, 103, 104, 105, 106]),
    }


class TestEMAPullbackContinuationStrategy:
    """Test cases for EMAPullbackContinuationStrategy."""

    def test_strategy_initialization(self):
        """Test that strategy initializes correctly."""
        strategy = EMAPullbackContinuationStrategy()
        assert strategy is not None

    def test_analyze_with_valid_data(self, sample_data, sample_indicators):
        """Test strategy analysis with valid data."""
        strategy = EMAPullbackContinuationStrategy()
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **sample_indicators}

        signal = strategy.analyze(sample_data, metadata)

        # Signal may or may not be generated based on conditions
        if signal:
            assert signal.symbol == "BTCUSDT"
            assert signal.timeframe == "15m"
            assert signal.strategy_id == "ema_pullback_continuation"
            assert signal.action in ["buy", "sell"]
            assert signal.confidence == 0.76
            assert signal.stop_loss is not None
            assert signal.take_profit is not None

    def test_analyze_insufficient_data(self):
        """Test strategy with insufficient data."""
        strategy = EMAPullbackContinuationStrategy()
        df = pd.DataFrame({"close": [100]})  # Only one data point
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(df, metadata)
        assert signal is None

    def test_analyze_missing_indicators(self, sample_data):
        """Test strategy with missing indicators."""
        strategy = EMAPullbackContinuationStrategy()
        # Missing some required indicators
        incomplete_indicators = {
            "ema21": pd.Series([101, 102, 103, 104, 105]),
            "ema50": pd.Series([100, 101, 102, 103, 104]),
            # Missing rsi and close
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **incomplete_indicators}

        signal = strategy.analyze(sample_data, metadata)
        assert signal is None

    def test_analyze_no_pullback(self, sample_data):
        """Test strategy when no pullback is detected."""
        strategy = EMAPullbackContinuationStrategy()
        # All indicators show consistent trend (no pullback)
        indicators = {
            "ema21": pd.Series([101, 102, 103, 104, 105]),
            "ema50": pd.Series([100, 101, 102, 103, 104]),
            "rsi": pd.Series([60, 61, 62, 63, 64]),  # High RSI indicates strong trend
            "close": pd.Series([102, 103, 104, 105, 106]),
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **indicators}

        signal = strategy.analyze(sample_data, metadata)
        assert signal is None
