"""
Tests for the TA Bot Signal Engine.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from ta_bot.core.signal_engine import SignalEngine


@pytest.fixture
def sample_candles():
    """Create sample OHLCV data for testing."""
    # Generate sample price data with some trend
    base_price = 50000
    num_candles = 100

    # Create timestamps
    end_time = datetime.now()
    interval = timedelta(minutes=15)
    timestamps = [end_time - interval * i for i in range(num_candles, 0, -1)]

    # Generate price data with some volatility and trend
    np.random.seed(42)  # For reproducible results

    # Create a trend with some volatility
    trend = np.linspace(0, 0.1, num_candles)  # 10% upward trend
    noise = np.random.normal(0, 0.02, num_candles)  # 2% volatility
    price_changes = trend + noise

    # Calculate OHLCV
    prices = [base_price]
    for change in price_changes[1:]:
        prices.append(prices[-1] * (1 + change))

    data = []
    for i, (timestamp, price) in enumerate(zip(timestamps, prices)):
        # Create realistic OHLCV data
        volatility = abs(price_changes[i]) * 2
        high = price * (1 + volatility)
        low = price * (1 - volatility)
        open_price = price * (1 + np.random.normal(0, volatility * 0.5))
        close_price = price
        volume = np.random.uniform(1000, 5000)

        data.append(
            {
                "timestamp": timestamp.isoformat(),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close_price,
                "volume": volume,
            }
        )

    return pd.DataFrame(data)


@pytest.fixture
def signal_engine():
    """Create a signal engine instance for testing."""
    return SignalEngine()


class TestSignalEngine:
    """Test the Signal Engine functionality."""

    def test_signal_engine_initialization(self, signal_engine):
        """Test that signal engine initializes correctly."""
        assert signal_engine is not None
        assert hasattr(signal_engine, "strategies")
        assert len(signal_engine.strategies) == 11  # 11 strategies

    def test_analyze_candles_with_sufficient_data(self, signal_engine, sample_candles):
        """Test signal analysis with sufficient data."""
        signals = signal_engine.analyze_candles(sample_candles, "BTCUSDT", "15m")

        # Should return a list (even if empty)
        assert isinstance(signals, list)

        # If signals are generated, they should be valid
        for signal in signals:
            assert signal.validate()
            assert signal.symbol == "BTCUSDT"
            assert signal.timeframe == "15m"
            assert signal.confidence >= 0.0
            assert signal.confidence <= 1.0

    def test_analyze_candles_insufficient_data(self, signal_engine):
        """Test signal analysis with insufficient data."""
        # Create minimal data
        minimal_data = pd.DataFrame(
            {
                "open": [50000],
                "high": [50100],
                "low": [49900],
                "close": [50050],
                "volume": [1000],
            }
        )

        signals = signal_engine.analyze_candles(minimal_data, "BTCUSDT", "15m")
        assert signals == []  # Should return empty list for insufficient data

    def test_indicators_calculation(self, signal_engine, sample_candles):
        """Test that indicators are calculated correctly."""
        indicators = signal_engine._calculate_indicators(sample_candles)

        # Check that all required indicators are present
        required_indicators = [
            "rsi",
            "macd",
            "macd_signal",
            "macd_hist",
            "adx",
            "atr",
            "ema21",
            "ema50",
            "ema200",
            "bb_lower",
            "bb_middle",
            "bb_upper",
        ]

        for indicator in required_indicators:
            assert indicator in indicators
            assert indicators[indicator] is not None

    def test_strategy_execution(self, signal_engine, sample_candles):
        """Test individual strategy execution."""
        indicators = signal_engine._calculate_indicators(sample_candles)

        # Test each strategy
        current_price = float(sample_candles["close"].iloc[-1])
        for strategy_name, strategy in signal_engine.strategies.items():
            signal = signal_engine._run_strategy(
                strategy,
                strategy_name,
                sample_candles,
                "BTCUSDT",
                "15m",
                indicators,
                current_price,
            )

            # Signal should be None or a valid Signal object
            if signal is not None:
                assert signal.validate()
                assert signal.strategy_id == strategy_name


class TestSignalModel:
    """Test the Signal model."""

    def test_signal_creation(self):
        """Test creating a valid signal."""
        from ta_bot.models.signal import Signal

        metadata = {"rsi": 58.3, "macd_hist": 0.0012, "adx": 27}

        signal = Signal(
            strategy_id="momentum_pulse",
            symbol="BTCUSDT",
            action="buy",
            confidence=0.74,
            current_price=50000.0,
            price=50000.0,
            timeframe="15m",
            metadata=metadata,
        )

        assert signal.validate()
        assert signal.symbol == "BTCUSDT"
        assert signal.timeframe == "15m"
        assert signal.action == "buy"
        assert signal.confidence == 0.74
        assert signal.strategy_id == "momentum_pulse"

    def test_signal_validation(self):
        """Test signal validation."""
        from ta_bot.models.signal import Signal

        # Test invalid confidence
        signal = Signal(
            strategy_id="momentum_pulse",
            symbol="BTCUSDT",
            action="buy",
            confidence=1.5,  # Invalid confidence
            current_price=50000.0,
            price=50000.0,
            timeframe="15m",
            metadata={},
        )
        assert not signal.validate()

        # Test missing required fields
        signal = Signal(
            strategy_id="momentum_pulse",
            symbol="",  # Empty symbol
            action="buy",
            confidence=0.74,
            current_price=50000.0,
            price=50000.0,
            timeframe="15m",
            metadata={},
        )
        assert not signal.validate()

    def test_signal_to_dict(self):
        """Test signal serialization."""
        from ta_bot.models.signal import Signal

        metadata = {"rsi": 58.3}
        signal = Signal(
            strategy_id="momentum_pulse",
            symbol="BTCUSDT",
            action="buy",
            confidence=0.74,
            current_price=50000.0,
            price=50000.0,
            timeframe="15m",
            metadata=metadata,
        )

        signal_dict = signal.to_dict()
        assert signal_dict["symbol"] == "BTCUSDT"
        assert signal_dict["action"] == "buy"
        assert signal_dict["confidence"] == 0.74
        assert signal_dict["metadata"] == metadata


class TestConfidenceCalculator:
    """Test the confidence calculator."""

    def test_momentum_pulse_confidence(self):
        """Test momentum pulse confidence calculation."""
        from ta_bot.core.confidence import ConfidenceCalculator

        df = pd.DataFrame({"close": [50000]})
        metadata = {"rsi": 55.0, "ema21": 50025.0, "ema50": 49980.0, "ema200": 49500.0}

        confidence = ConfidenceCalculator.momentum_pulse_confidence(df, metadata)
        assert 0.6 <= confidence <= 0.8

        # Test with RSI > 60 (should not add RSI bonus)
        metadata["rsi"] = 65.0
        confidence = ConfidenceCalculator.momentum_pulse_confidence(df, metadata)
        assert confidence == 0.7  # Base 0.6 + EMA bonus 0.1

    def test_confidence_bounds(self):
        """Test that confidence is always between 0 and 1."""
        from ta_bot.core.confidence import ConfidenceCalculator

        df = pd.DataFrame({"close": [50000]})

        # Test all strategies
        strategies = [
            "momentum_pulse",
            "band_fade_reversal",
            "golden_trend_sync",
            "range_break_pop",
            "divergence_trap",
        ]

        for strategy in strategies:
            metadata = {"rsi": 50.0}
            confidence = ConfidenceCalculator.calculate_confidence(
                strategy, df, metadata
            )
            assert 0.0 <= confidence <= 1.0


if __name__ == "__main__":
    pytest.main([__file__])
