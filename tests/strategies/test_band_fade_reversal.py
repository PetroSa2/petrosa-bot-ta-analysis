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

    def test_gate_rejects_signal_missing_rsi_and_volume_confirmation(self):
        """Issue #282: restored production gates reject a candle series that
        `main` at HEAD accepts. Before this fix, `analyze()` only checked
        `near_lower_band`, `below_middle`, and `reversal_pattern` -- RSI and
        volume confirmation were never read. This series satisfies all three
        of those (loosened) conditions but fails RSI-oversold (rsi=51, not
        <= 30) and volume confirmation (flat volume, ratio ~1.0, not > 1.5),
        both restored here as hard gates."""
        strategy = BandFadeReversalStrategy()
        n = 20
        closes = [100] * 15 + [99, 98, 97, 90, 91]
        highs = [c + 2 for c in closes]
        lows = [c - 2 for c in closes]
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
        indicators = {
            "bb_lower": pd.Series([91] * n),
            "bb_middle": pd.Series([100] * n),
            "bb_upper": pd.Series([110] * n),
            "rsi": pd.Series([50] * 15 + [55, 54, 53, 52, 51]),
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **indicators}

        signal = strategy.analyze(df, metadata)
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

    def test_config_override_changes_signal_outcome(self):
        """Issue #283 AC5: overriding `rsi_oversold` produces a signal under
        the default (30) and no signal under a stricter override (20), for
        the exact same candle series (rsi=27 on the final candle: <= 30 but
        not <= 20)."""
        strategy = BandFadeReversalStrategy()
        n = 20
        closes = [100] * 15 + [99, 98, 97, 90, 91]
        highs = [c + 2 for c in closes]
        lows = [c - 2 for c in closes]
        volumes = [1000] * 19 + [1700]
        df = pd.DataFrame(
            {
                "open": closes,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volumes,
            }
        )
        indicators = {
            "bb_lower": pd.Series([91] * n),
            "bb_middle": pd.Series([100] * n),
            "bb_upper": pd.Series([110] * n),
            "rsi": pd.Series([50] * 15 + [40, 35, 30, 28, 27]),
        }

        baseline_metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **indicators}
        baseline_signal = strategy.analyze(df, baseline_metadata)

        override_metadata = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            **indicators,
            "config": {
                "parameters": {"rsi_oversold": 20},
                "version": 2,
                "source": "mongodb",
                "is_override": True,
            },
        }
        override_signal = strategy.analyze(df, override_metadata)

        assert baseline_signal is not None
        assert baseline_signal.confidence == 0.72
        assert override_signal is None
