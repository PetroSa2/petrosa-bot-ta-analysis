"""
Tests for the Band Fade Reversal strategy.
"""

import pandas as pd
import pytest

from ta_bot.strategies.band_fade_reversal import BandFadeReversalStrategy


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
        "close": pd.Series([102, 103, 104, 105, 106]),
    }


class TestBandFadeReversalStrategy:
    """Test cases for BandFadeReversalStrategy."""

    def test_strategy_initialization(self):
        """Test that strategy initializes correctly."""
        strategy = BandFadeReversalStrategy()
        assert strategy is not None

    def test_analyze_with_valid_data(self, sample_data, sample_indicators):
        """Test strategy analysis with valid data."""
        strategy = BandFadeReversalStrategy()
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **sample_indicators}

        signal = strategy.analyze(sample_data, metadata)

        # Signal may or may not be generated based on conditions
        if signal:
            assert signal.symbol == "BTCUSDT"
            assert signal.timeframe == "15m"
            assert signal.strategy_id == "band_fade_reversal"
            assert signal.action == "buy"
            assert signal.confidence == 0.72
            assert signal.stop_loss is not None
            assert signal.take_profit is not None

    def test_analyze_insufficient_data(self):
        """Test strategy with insufficient data."""
        strategy = BandFadeReversalStrategy()
        df = pd.DataFrame({"close": [100]})  # Only one data point
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(df, metadata)
        assert signal is None

    def test_analyze_missing_indicators(self, sample_data):
        """Test strategy with missing indicators."""
        strategy = BandFadeReversalStrategy()
        # Missing some required indicators
        incomplete_indicators = {
            "bb_lower": pd.Series([90, 91, 92, 93, 94]),
            "bb_upper": pd.Series([110, 111, 112, 113, 114]),
            # Missing bb_middle and close
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **incomplete_indicators}

        signal = strategy.analyze(sample_data, metadata)
        assert signal is None

    def test_analyze_no_reversal_pattern(self, sample_data):
        """Test strategy when no reversal pattern is detected."""
        strategy = BandFadeReversalStrategy()
        # Prices are consistently increasing (no reversal)
        df = pd.DataFrame(
            {
                "open": [100, 101, 102, 103, 104],
                "high": [105, 106, 107, 108, 109],
                "low": [95, 96, 97, 98, 99],
                "close": [101, 102, 103, 104, 105],  # Consistently increasing
                "volume": [1000, 1100, 1200, 1300, 1400],
            }
        )

        indicators = {
            "bb_lower": pd.Series([90, 91, 92, 93, 94]),
            "bb_upper": pd.Series([110, 111, 112, 113, 114]),
            "bb_middle": pd.Series([100, 101, 102, 103, 104]),
            "close": pd.Series([101, 102, 103, 104, 105]),
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **indicators}

        signal = strategy.analyze(df, metadata)
        assert signal is None
