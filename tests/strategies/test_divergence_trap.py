"""
Tests for the Divergence Trap strategy.
"""

import pandas as pd
import pytest

from ta_bot.strategies.divergence_trap import DivergenceTrapStrategy


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
        "rsi": pd.Series([30, 35, 40, 45, 50]),
        "close": pd.Series([102, 103, 104, 105, 106]),
    }


class TestDivergenceTrapStrategy:
    """Test cases for DivergenceTrapStrategy."""

    def test_strategy_initialization(self):
        """Test that strategy initializes correctly."""
        strategy = DivergenceTrapStrategy()
        assert strategy is not None

    def test_analyze_with_valid_data(self, sample_data, sample_indicators):
        """Test strategy analysis with valid data."""
        strategy = DivergenceTrapStrategy()
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **sample_indicators}

        signal = strategy.analyze(sample_data, metadata)

        # Signal may or may not be generated based on conditions
        if signal:
            assert signal.symbol == "BTCUSDT"
            assert signal.timeframe == "15m"
            assert signal.strategy_id == "divergence_trap"
            assert signal.action in ["buy", "sell"]
            assert signal.confidence >= 0.5
            assert signal.stop_loss is not None
            assert signal.take_profit is not None

    def test_analyze_insufficient_data(self):
        """Test strategy with insufficient data."""
        strategy = DivergenceTrapStrategy()
        df = pd.DataFrame({"close": [100]})  # Only one data point
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(df, metadata)
        assert signal is None

    def test_analyze_missing_indicators(self, sample_data):
        """Test strategy with missing indicators."""
        strategy = DivergenceTrapStrategy()
        # Missing some required indicators
        incomplete_indicators = {
            "rsi": pd.Series([30, 35, 40, 45, 50]),
            # Missing close
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **incomplete_indicators}

        signal = strategy.analyze(sample_data, metadata)
        assert signal is None

    def test_gate_rejects_fixed_offset_false_divergence(self):
        """Issue #282: `main` at HEAD compares price/RSI at a fixed 5-bar
        offset (`recent_lows[-1] < recent_lows[-5]`), which fires on any
        5-bar drift and is not real divergence detection. This series is a
        near-monotonic decline with a 1-tick reversal on the final candle --
        the fixed-offset comparison confirms both a "lower low" and an
        RSI "higher low" (oversold + upward momentum are also both true),
        so `main` emits a signal. The restored `_find_recent_lows`
        swing-low detection does not confirm a genuine RSI higher-low here
        and must reject it."""
        strategy = DivergenceTrapStrategy()
        n = 30
        tail_closes = [85, 84, 83, 82, 81, 80, 79, 78, 77, 77.5]
        closes = [100] * (n - 10) + tail_closes
        highs = [c + 1 for c in closes]
        lows = [c - 1 for c in closes]
        volumes = [1000] * n
        df = pd.DataFrame(
            {
                "open": closes,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volumes,
            }
        )
        rsi_tail = [45, 43, 41, 25, 20, 18, 20, 22, 24, 26]
        rsi_vals = [50] * (n - 10) + rsi_tail
        metadata = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "rsi": pd.Series(rsi_vals),
        }

        signal = strategy.analyze(df, metadata)
        assert signal is None

    def test_analyze_no_divergence_pattern(self, sample_data):
        """Test strategy when no divergence pattern is detected."""
        strategy = DivergenceTrapStrategy()
        # Prices and RSI moving in same direction (no divergence)
        df = pd.DataFrame(
            {
                "open": [100, 101, 102, 103, 104],
                "high": [105, 106, 107, 108, 109],
                "low": [95, 96, 97, 98, 99],
                "close": [102, 103, 104, 105, 106],  # Increasing prices
                "volume": [1000, 1100, 1200, 1300, 1400],
            }
        )

        indicators = {
            "rsi": pd.Series([30, 35, 40, 45, 50]),  # Increasing RSI
            "close": pd.Series([102, 103, 104, 105, 106]),
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **indicators}

        signal = strategy.analyze(df, metadata)
        assert signal is None
