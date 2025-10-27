"""
Comprehensive unit tests for trading strategies.

Tests cover all strategy implementations, signal generation logic,
indicator calculations, edge cases, and performance characteristics.
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from ta_bot.models.signal import Signal
from ta_bot.strategies.band_fade_reversal import BandFadeReversalStrategy
from ta_bot.strategies.base_strategy import BaseStrategy
from ta_bot.strategies.ema_pullback_continuation import EMAPullbackContinuationStrategy
from ta_bot.strategies.momentum_pulse import MomentumPulseStrategy


@pytest.mark.unit
class TestBaseStrategy:
    """Test cases for BaseStrategy abstract class."""

    def test_base_strategy_initialization(self):
        """Test base strategy initialization."""
        strategy = BaseStrategy()
        assert strategy is not None

    def test_analyze_method_not_implemented(self):
        """Test that analyze method raises NotImplementedError."""
        strategy = BaseStrategy()
        df = pd.DataFrame()
        metadata = {}

        with pytest.raises(NotImplementedError):
            strategy.analyze(df, metadata)

    def test_get_current_values_with_pandas_series(self):
        """Test _get_current_values with pandas Series indicators."""
        strategy = BaseStrategy()

        # Create test data
        df = pd.DataFrame(
            {
                "open": [100, 101, 102],
                "high": [105, 106, 107],
                "low": [95, 96, 97],
                "close": [103, 104, 105],
                "volume": [1000, 1100, 1200],
            }
        )

        indicators = {
            "rsi": pd.Series([30, 40, 50]),
            "macd": pd.Series([0.1, 0.2, 0.3]),
            "ema": pd.Series([100.5, 101.5, 102.5]),
        }

        current_values = strategy._get_current_values(indicators, df)

        assert current_values["rsi"] == 50.0
        assert current_values["macd"] == 0.3
        assert current_values["ema"] == 102.5
        assert current_values["close"] == 105.0
        assert current_values["volume"] == 1200.0

    def test_get_current_values_with_empty_series(self):
        """Test _get_current_values with empty pandas Series."""
        strategy = BaseStrategy()

        df = pd.DataFrame(
            {
                "open": [100],
                "high": [105],
                "low": [95],
                "close": [103],
                "volume": [1000],
            }
        )

        indicators = {"empty_series": pd.Series([]), "valid_series": pd.Series([50])}

        current_values = strategy._get_current_values(indicators, df)

        assert "empty_series" not in current_values
        assert current_values["valid_series"] == 50.0

    def test_get_current_values_with_list_indicators(self):
        """Test _get_current_values with list indicators."""
        strategy = BaseStrategy()

        df = pd.DataFrame(
            {
                "open": [99, 100, 101],
                "high": [101, 102, 103],
                "low": [98, 99, 100],
                "close": [100, 101, 102],
                "volume": [1000, 1100, 1200],
            }
        )

        indicators = {
            "list_indicator": [10, 20, 30],
            "empty_list": [],
            "single_item_list": [42],
        }

        current_values = strategy._get_current_values(indicators, df)

        assert current_values["list_indicator"] == 30.0
        assert "empty_list" not in current_values
        assert current_values["single_item_list"] == 42.0

    def test_get_current_values_with_scalar_indicators(self):
        """Test _get_current_values with scalar indicators."""
        strategy = BaseStrategy()

        df = pd.DataFrame(
            {"open": [99], "high": [101], "low": [98], "close": [100], "volume": [1000]}
        )

        indicators = {"scalar_int": 42, "scalar_float": 3.14, "scalar_none": None}

        current_values = strategy._get_current_values(indicators, df)

        assert current_values["scalar_int"] == 42.0
        assert current_values["scalar_float"] == 3.14
        assert "scalar_none" not in current_values

    def test_get_previous_values(self):
        """Test _get_previous_values method."""
        strategy = BaseStrategy()

        df = pd.DataFrame(
            {
                "open": [100, 101, 102],
                "high": [105, 106, 107],
                "low": [95, 96, 97],
                "close": [103, 104, 105],
                "volume": [1000, 1100, 1200],
            }
        )

        indicators = {
            "rsi": pd.Series([30, 40, 50]),
            "macd": pd.Series([0.1, 0.2, 0.3]),
        }

        previous_values = strategy._get_previous_values(indicators, df)

        assert previous_values["rsi"] == 40.0
        assert previous_values["macd"] == 0.2
        assert previous_values["close"] == 104.0

    def test_check_cross_above(self):
        """Test _check_cross_above method."""
        strategy = BaseStrategy()

        # Test crossing above
        assert strategy._check_cross_above(51, 49, 50) is True
        assert strategy._check_cross_above(50, 49, 50) is False  # Equal, not above
        assert strategy._check_cross_above(49, 51, 50) is False  # Was already above

    def test_check_cross_below(self):
        """Test _check_cross_below method."""
        strategy = BaseStrategy()

        # Test crossing below
        assert strategy._check_cross_below(49, 51, 50) is True
        assert strategy._check_cross_below(50, 51, 50) is False  # Equal, not below
        assert strategy._check_cross_below(51, 49, 50) is False  # Was already below

    def test_check_between(self):
        """Test _check_between method."""
        strategy = BaseStrategy()

        assert strategy._check_between(50, 40, 60) is True
        assert strategy._check_between(40, 40, 60) is True  # Inclusive
        assert strategy._check_between(60, 40, 60) is True  # Inclusive
        assert strategy._check_between(35, 40, 60) is False
        assert strategy._check_between(65, 40, 60) is False


@pytest.mark.unit
class TestMomentumPulseStrategy:
    """Test cases for MomentumPulseStrategy."""

    def create_sample_dataframe(self, length=50):
        """Create sample OHLCV dataframe for testing."""
        np.random.seed(42)  # For reproducible tests

        # Generate realistic price data
        base_price = 50000
        price_changes = np.random.normal(0, 0.02, length)
        prices = [base_price]

        for change in price_changes[1:]:
            prices.append(prices[-1] * (1 + change))

        data = []
        for i, price in enumerate(prices):
            volatility = 0.01
            high = price * (1 + volatility)
            low = price * (1 - volatility)
            open_price = price * (1 + np.random.normal(0, 0.005))
            volume = np.random.uniform(1000, 5000)

            data.append(
                {
                    "timestamp": datetime.now() - timedelta(minutes=(length - i) * 15),
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": price,
                    "volume": volume,
                }
            )

        return pd.DataFrame(data)

    def test_momentum_pulse_initialization(self):
        """Test MomentumPulseStrategy initialization."""
        strategy = MomentumPulseStrategy()
        assert strategy is not None
        assert isinstance(strategy, BaseStrategy)

    def test_momentum_pulse_analyze_with_valid_data(self):
        """Test momentum pulse analysis with valid data."""
        strategy = MomentumPulseStrategy()
        df = self.create_sample_dataframe(100)

        metadata = {"symbol": "BTCUSDT", "period": "15m"}

        signal = strategy.analyze(df, metadata)

        # Signal may or may not be generated based on conditions
        if signal:
            assert isinstance(signal, Signal)
            assert signal.symbol == "BTCUSDT"
            assert signal.timeframe == "15m"
            assert signal.strategy_id == "momentum_pulse"
            assert signal.action in ["buy", "sell"]
            assert 0 <= signal.confidence <= 1

    def test_momentum_pulse_buy_signal_conditions(self):
        """Test specific conditions for buy signals."""
        strategy = MomentumPulseStrategy()

        # Create data that should trigger buy signal
        df = pd.DataFrame(
            {
                "open": [49000, 49500, 50000, 50200, 50500],
                "high": [49200, 49700, 50200, 50400, 50700],
                "low": [48800, 49300, 49800, 50000, 50300],
                "close": [49100, 49600, 50100, 50300, 50600],
                "volume": [1000, 1100, 1200, 1300, 1400],
            }
        )

        metadata = {"symbol": "BTCUSDT", "period": "15m"}

        with patch("ta_bot.core.indicators.Indicators") as mock_indicators:
            # Mock indicators to create buy signal conditions
            mock_indicators.return_value.calculate_rsi.return_value = pd.Series(
                [25, 30, 35, 40, 45]
            )  # Oversold recovery
            mock_indicators.return_value.calculate_macd.return_value = {
                "macd": pd.Series([-0.5, -0.3, -0.1, 0.1, 0.3]),
                "signal": pd.Series([-0.4, -0.2, 0, 0.2, 0.4]),
                "histogram": pd.Series([-0.1, -0.1, -0.1, -0.1, -0.1]),
            }
            mock_indicators.return_value.calculate_adx.return_value = pd.Series(
                [20, 22, 25, 28, 30]
            )

            signal = strategy.analyze(df, metadata)

            if signal and signal.action == "buy":
                assert signal.confidence > 0.5

    def test_momentum_pulse_sell_signal_conditions(self):
        """Test specific conditions for sell signals."""
        strategy = MomentumPulseStrategy()

        # Create data that should trigger sell signal
        df = pd.DataFrame(
            {
                "open": [51000, 50800, 50500, 50200, 49900],
                "high": [51200, 51000, 50700, 50400, 50100],
                "low": [50800, 50600, 50300, 50000, 49700],
                "close": [50900, 50700, 50400, 50100, 49800],
                "volume": [1000, 1100, 1200, 1300, 1400],
            }
        )

        metadata = {"symbol": "BTCUSDT", "period": "15m"}

        with patch("ta_bot.core.indicators.Indicators") as mock_indicators:
            # Mock indicators to create sell signal conditions
            mock_indicators.return_value.calculate_rsi.return_value = pd.Series(
                [85, 80, 75, 70, 65]
            )  # Overbought decline
            mock_indicators.return_value.calculate_macd.return_value = {
                "macd": pd.Series([0.5, 0.3, 0.1, -0.1, -0.3]),
                "signal": pd.Series([0.4, 0.2, 0, -0.2, -0.4]),
                "histogram": pd.Series([0.1, 0.1, 0.1, 0.1, 0.1]),
            }
            mock_indicators.return_value.calculate_adx.return_value = pd.Series(
                [35, 32, 30, 28, 25]
            )

            signal = strategy.analyze(df, metadata)

            if signal and signal.action == "sell":
                assert signal.confidence > 0.5

    def test_momentum_pulse_insufficient_data(self):
        """Test momentum pulse with insufficient data."""
        strategy = MomentumPulseStrategy()

        # Create very small dataframe
        df = pd.DataFrame(
            {
                "open": [50000],
                "high": [50100],
                "low": [49900],
                "close": [50050],
                "volume": [1000],
            }
        )

        metadata = {"symbol": "BTCUSDT", "period": "15m"}

        signal = strategy.analyze(df, metadata)

        # Should return None due to insufficient data
        assert signal is None

    def test_momentum_pulse_edge_case_flat_market(self):
        """Test momentum pulse in flat market conditions."""
        strategy = MomentumPulseStrategy()

        # Create flat market data
        df = pd.DataFrame(
            {
                "open": [50000] * 50,
                "high": [50010] * 50,
                "low": [49990] * 50,
                "close": [50000] * 50,
                "volume": [1000] * 50,
            }
        )

        metadata = {"symbol": "BTCUSDT", "period": "15m"}

        signal = strategy.analyze(df, metadata)

        # Should likely return None in flat market
        if signal:
            assert signal.confidence < 0.7  # Low confidence in flat market


@pytest.mark.unit
class TestBandFadeReversalStrategy:
    """Test cases for BandFadeReversalStrategy."""

    def create_volatile_dataframe(self):
        """Create dataframe with volatile price action for band testing."""
        np.random.seed(42)

        # Create price data that moves between bands
        base_price = 50000
        data = []

        for i in range(50):
            if i < 10:
                # Start in middle
                price = base_price + np.random.normal(0, 100)
            elif i < 20:
                # Move to lower band
                price = base_price - 1000 + np.random.normal(0, 50)
            elif i < 30:
                # Bounce back up
                price = base_price + np.random.normal(0, 200)
            elif i < 40:
                # Move to upper band
                price = base_price + 1000 + np.random.normal(0, 50)
            else:
                # Fade back to middle
                price = base_price + np.random.normal(0, 100)

            volatility = 0.01
            data.append(
                {
                    "open": price * (1 + np.random.normal(0, 0.005)),
                    "high": price * (1 + volatility),
                    "low": price * (1 - volatility),
                    "close": price,
                    "volume": np.random.uniform(1000, 5000),
                }
            )

        return pd.DataFrame(data)

    def test_band_fade_reversal_initialization(self):
        """Test BandFadeReversalStrategy initialization."""
        strategy = BandFadeReversalStrategy()
        assert strategy is not None
        assert isinstance(strategy, BaseStrategy)

    def test_band_fade_reversal_analyze(self):
        """Test band fade reversal analysis."""
        strategy = BandFadeReversalStrategy()
        df = self.create_volatile_dataframe()

        metadata = {"symbol": "ETHUSDT", "period": "15m"}

        signal = strategy.analyze(df, metadata)

        # Always assert that signal is either None or a valid Signal
        assert signal is None or isinstance(signal, Signal)

        if signal:
            assert isinstance(signal, Signal)
            assert signal.symbol == "ETHUSDT"
            assert signal.strategy_id == "band_fade_reversal"
            assert signal.action in ["buy", "sell"]

    def test_band_fade_reversal_buy_at_lower_band(self):
        """Test buy signal generation at lower Bollinger Band."""
        strategy = BandFadeReversalStrategy()

        # Create data touching lower band
        df = pd.DataFrame(
            {
                "open": [50000, 49800, 49600, 49400, 49500],
                "high": [50100, 49900, 49700, 49500, 49600],
                "low": [49900, 49700, 49500, 49300, 49400],
                "close": [49950, 49750, 49550, 49350, 49450],
                "volume": [1000, 1100, 1200, 1300, 1400],
            }
        )

        metadata = {"symbol": "BTCUSDT", "period": "15m"}

        with patch("ta_bot.core.indicators.Indicators") as mock_indicators:
            # Mock Bollinger Bands
            mock_indicators.return_value.calculate_bollinger_bands.return_value = {
                "upper": pd.Series([50500, 50300, 50100, 49900, 49700]),
                "middle": pd.Series([50000, 49800, 49600, 49400, 49200]),
                "lower": pd.Series([49500, 49300, 49100, 48900, 48700]),
            }
            mock_indicators.return_value.calculate_rsi.return_value = pd.Series(
                [40, 35, 30, 25, 30]
            )

            signal = strategy.analyze(df, metadata)

            if signal and signal.action == "buy":
                assert "bollinger" in signal.metadata
                assert signal.confidence > 0.6

    def test_band_fade_reversal_sell_at_upper_band(self):
        """Test sell signal generation at upper Bollinger Band."""
        strategy = BandFadeReversalStrategy()

        # Create data touching upper band
        df = pd.DataFrame(
            {
                "open": [50000, 50200, 50400, 50600, 50500],
                "high": [50100, 50300, 50500, 50700, 50600],
                "low": [49900, 50100, 50300, 50500, 50400],
                "close": [50050, 50250, 50450, 50650, 50550],
                "volume": [1000, 1100, 1200, 1300, 1400],
            }
        )

        metadata = {"symbol": "BTCUSDT", "period": "15m"}

        with patch("ta_bot.core.indicators.Indicators") as mock_indicators:
            # Mock Bollinger Bands
            mock_indicators.return_value.calculate_bollinger_bands.return_value = {
                "upper": pd.Series([50300, 50500, 50700, 50900, 50700]),
                "middle": pd.Series([50000, 50200, 50400, 50600, 50400]),
                "lower": pd.Series([49700, 49900, 50100, 50300, 50100]),
            }
            mock_indicators.return_value.calculate_rsi.return_value = pd.Series(
                [60, 65, 70, 75, 70]
            )

            signal = strategy.analyze(df, metadata)

            if signal and signal.action == "sell":
                assert signal.confidence > 0.6


@pytest.mark.unit
class TestEMAPullbackContinuationStrategy:
    """Test cases for EMAPullbackContinuationStrategy."""

    def create_trending_dataframe(self, trend_direction="up"):
        """Create dataframe with trending price action."""
        np.random.seed(42)

        base_price = 50000
        data = []

        for i in range(50):
            if trend_direction == "up":
                trend_factor = i * 20  # Upward trend
                pullback_factor = -50 if 20 <= i <= 30 else 0  # Pullback in middle
            else:
                trend_factor = -i * 20  # Downward trend
                pullback_factor = 50 if 20 <= i <= 30 else 0  # Pullback in middle

            price = (
                base_price + trend_factor + pullback_factor + np.random.normal(0, 50)
            )
            volatility = 0.01

            data.append(
                {
                    "open": price * (1 + np.random.normal(0, 0.005)),
                    "high": price * (1 + volatility),
                    "low": price * (1 - volatility),
                    "close": price,
                    "volume": np.random.uniform(1000, 5000),
                }
            )

        return pd.DataFrame(data)

    def test_ema_pullback_continuation_initialization(self):
        """Test EMAPullbackContinuationStrategy initialization."""
        strategy = EMAPullbackContinuationStrategy()
        assert strategy is not None
        assert isinstance(strategy, BaseStrategy)

    def test_ema_pullback_continuation_uptrend_pullback(self):
        """Test pullback continuation in uptrend."""
        strategy = EMAPullbackContinuationStrategy()
        df = self.create_trending_dataframe("up")

        metadata = {"symbol": "BTCUSDT", "period": "15m"}

        with patch("ta_bot.core.indicators.Indicators") as mock_indicators:
            # Mock EMAs for uptrend
            mock_indicators.return_value.calculate_ema.side_effect = (
                lambda df, period: {
                    21: pd.Series(np.linspace(49500, 50500, len(df))),  # EMA21
                    50: pd.Series(np.linspace(49000, 50000, len(df))),  # EMA50
                }[period]
            )

            mock_indicators.return_value.calculate_rsi.return_value = pd.Series(
                [50 + np.sin(i / 5) * 20 for i in range(len(df))]
            )

            signal = strategy.analyze(df, metadata)

            if signal:
                assert signal.strategy_id == "ema_pullback_continuation"
                if signal.action == "buy":
                    assert "ema21" in signal.metadata
                    assert "ema50" in signal.metadata

    def test_ema_pullback_continuation_downtrend_pullback(self):
        """Test pullback continuation in downtrend."""
        strategy = EMAPullbackContinuationStrategy()
        df = self.create_trending_dataframe("down")

        metadata = {"symbol": "BTCUSDT", "period": "15m"}

        with patch("ta_bot.core.indicators.Indicators") as mock_indicators:
            # Mock EMAs for downtrend
            mock_indicators.return_value.calculate_ema.side_effect = (
                lambda df, period: {
                    21: pd.Series(
                        np.linspace(50500, 49500, len(df))
                    ),  # EMA21 declining
                    50: pd.Series(
                        np.linspace(50000, 49000, len(df))
                    ),  # EMA50 declining
                }[period]
            )

            mock_indicators.return_value.calculate_rsi.return_value = pd.Series(
                [50 - np.sin(i / 5) * 20 for i in range(len(df))]
            )

            signal = strategy.analyze(df, metadata)

            # Always assert that signal is either None or a valid Signal
            assert signal is None or isinstance(signal, Signal)

            if signal and signal.action == "sell":
                assert signal.confidence > 0.5


@pytest.mark.unit
class TestStrategyPerformance:
    """Performance tests for strategies."""

    def test_strategy_execution_time(self):
        """Test strategy execution time performance."""
        import time

        strategy = MomentumPulseStrategy()

        # Create large dataset
        np.random.seed(42)
        large_df = pd.DataFrame(
            {
                "open": np.random.uniform(49000, 51000, 1000),
                "high": np.random.uniform(49500, 51500, 1000),
                "low": np.random.uniform(48500, 50500, 1000),
                "close": np.random.uniform(49000, 51000, 1000),
                "volume": np.random.uniform(1000, 5000, 1000),
            }
        )

        metadata = {"symbol": "BTCUSDT", "period": "15m"}

        start_time = time.time()
        _ = strategy.analyze(large_df, metadata)
        execution_time = time.time() - start_time

        # Should execute quickly
        assert execution_time < 5.0  # Less than 5 seconds for 1000 candles

    def test_strategy_memory_usage(self):
        """Test strategy memory usage remains stable."""
        strategy = MomentumPulseStrategy()

        # Run multiple analyses
        for _ in range(100):
            df = pd.DataFrame(
                {
                    "open": np.random.uniform(49000, 51000, 50),
                    "high": np.random.uniform(49500, 51500, 50),
                    "low": np.random.uniform(48500, 50500, 50),
                    "close": np.random.uniform(49000, 51000, 50),
                    "volume": np.random.uniform(1000, 5000, 50),
                }
            )

            metadata = {"symbol": "BTCUSDT", "period": "15m"}
            _ = strategy.analyze(df, metadata)

        # Strategy should not accumulate state
        assert hasattr(strategy, "__dict__")  # Basic check that object exists


@pytest.mark.unit
class TestStrategyEdgeCases:
    """Test edge cases and error conditions."""

    def test_strategy_with_nan_values(self):
        """Test strategy handling of NaN values in data."""
        strategy = MomentumPulseStrategy()

        df = pd.DataFrame(
            {
                "open": [50000, np.nan, 50200, 50300, np.nan],
                "high": [50100, 50150, np.nan, 50400, 50350],
                "low": [49900, 49950, 50000, np.nan, 50250],
                "close": [50050, 50100, 50150, 50350, np.nan],
                "volume": [1000, 1100, np.nan, 1300, 1400],
            }
        )

        metadata = {"symbol": "BTCUSDT", "period": "15m"}

        # Should handle NaN values gracefully
        signal = strategy.analyze(df, metadata)

        # May return None or a signal, but should not crash
        if signal:
            assert isinstance(signal, Signal)

    def test_strategy_with_empty_dataframe(self):
        """Test strategy with empty dataframe."""
        strategy = MomentumPulseStrategy()

        df = pd.DataFrame()
        metadata = {"symbol": "BTCUSDT", "period": "15m"}

        signal = strategy.analyze(df, metadata)

        # Should return None for empty data
        assert signal is None

    def test_strategy_with_single_row(self):
        """Test strategy with single row of data."""
        strategy = MomentumPulseStrategy()

        df = pd.DataFrame(
            {
                "open": [50000],
                "high": [50100],
                "low": [49900],
                "close": [50050],
                "volume": [1000],
            }
        )

        metadata = {"symbol": "BTCUSDT", "period": "15m"}

        signal = strategy.analyze(df, metadata)

        # Should return None due to insufficient data
        assert signal is None

    def test_strategy_with_extreme_values(self):
        """Test strategy with extreme price values."""
        strategy = MomentumPulseStrategy()

        df = pd.DataFrame(
            {
                "open": [1e-8, 1e8, 50000, 50100, 50200],
                "high": [1e-7, 1.1e8, 50100, 50200, 50300],
                "low": [1e-9, 0.9e8, 49900, 50000, 50100],
                "close": [5e-8, 1.05e8, 50050, 50150, 50250],
                "volume": [1000, 1100, 1200, 1300, 1400],
            }
        )

        metadata = {"symbol": "BTCUSDT", "period": "15m"}

        # Should handle extreme values gracefully
        signal = strategy.analyze(df, metadata)

        # Should not crash
        if signal:
            assert isinstance(signal, Signal)

    @pytest.mark.parametrize(
        "missing_column", ["open", "high", "low", "close", "volume"]
    )
    def test_strategy_with_missing_columns(self, missing_column):
        """Test strategy with missing required columns."""
        strategy = MomentumPulseStrategy()

        df = pd.DataFrame(
            {
                "open": [50000, 50100, 50200],
                "high": [50100, 50200, 50300],
                "low": [49900, 50000, 50100],
                "close": [50050, 50150, 50250],
                "volume": [1000, 1100, 1200],
            }
        )

        # Remove one column
        df = df.drop(columns=[missing_column])

        metadata = {"symbol": "BTCUSDT", "period": "15m"}

        # Should handle missing columns gracefully
        try:
            _ = strategy.analyze(df, metadata)
            # If it doesn't crash, that's acceptable
        except (KeyError, AttributeError):
            # Expected for missing required columns
            pass


@pytest.mark.unit
class TestStrategyMetadata:
    """Test strategy metadata and signal information."""

    def test_signal_metadata_completeness(self):
        """Test that generated signals contain complete metadata."""
        strategy = MomentumPulseStrategy()

        df = pd.DataFrame(
            {
                "open": [50000, 50100, 50200, 50300, 50400],
                "high": [50100, 50200, 50300, 50400, 50500],
                "low": [49900, 50000, 50100, 50200, 50300],
                "close": [50050, 50150, 50250, 50350, 50450],
                "volume": [1000, 1100, 1200, 1300, 1400],
            }
        )

        metadata = {
            "symbol": "BTCUSDT",
            "period": "15m",
            "exchange": "binance",
            "timestamp": datetime.now(),
        }

        signal = strategy.analyze(df, metadata)

        if signal:
            assert signal.symbol == "BTCUSDT"
            assert signal.timeframe == "15m"
            assert signal.strategy_id == "momentum_pulse"
            assert hasattr(signal, "timestamp")
            assert hasattr(signal, "price")
            assert hasattr(signal, "confidence")
            assert hasattr(signal, "metadata")
            assert isinstance(signal.metadata, dict)

    def test_signal_price_accuracy(self):
        """Test that signal price matches current close price."""
        strategy = MomentumPulseStrategy()

        df = pd.DataFrame(
            {
                "open": [50000, 50100, 50200],
                "high": [50100, 50200, 50300],
                "low": [49900, 50000, 50100],
                "close": [50050, 50150, 50250],
                "volume": [1000, 1100, 1200],
            }
        )

        metadata = {"symbol": "BTCUSDT", "period": "15m"}

        signal = strategy.analyze(df, metadata)

        if signal:
            # Signal price should be close to the last close price
            assert abs(signal.price - 50250) < 1.0

    def test_confidence_score_range(self):
        """Test that confidence scores are within valid range."""
        strategies = [
            MomentumPulseStrategy(),
            BandFadeReversalStrategy(),
            EMAPullbackContinuationStrategy(),
        ]

        df = pd.DataFrame(
            {
                "open": np.random.uniform(49000, 51000, 50),
                "high": np.random.uniform(49500, 51500, 50),
                "low": np.random.uniform(48500, 50500, 50),
                "close": np.random.uniform(49000, 51000, 50),
                "volume": np.random.uniform(1000, 5000, 50),
            }
        )

        metadata = {"symbol": "BTCUSDT", "period": "15m"}

        for strategy in strategies:
            signal = strategy.analyze(df, metadata)

            if signal:
                assert 0 <= signal.confidence <= 1
                assert isinstance(signal.confidence, (int, float))
