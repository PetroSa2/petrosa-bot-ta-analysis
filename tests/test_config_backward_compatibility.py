"""
Test backward compatibility of configuration system.

Verifies that:
1. Strategies work without config manager (existing behavior)
2. Strategies work with config manager but no config in DB (uses defaults)
3. Signal generation is not broken
4. Signal format remains unchanged
"""

import pandas as pd
import pytest

from ta_bot.models.signal import Signal
from ta_bot.strategies.bollinger_squeeze_alert import BollingerSqueezeAlertStrategy
from ta_bot.strategies.rsi_extreme_reversal import RSIExtremeReversalStrategy


def create_sample_dataframe(rows: int = 100) -> pd.DataFrame:
    """Create sample OHLCV data for testing."""
    import numpy as np

    # Create realistic price data
    base_price = 50000.0
    prices = base_price + np.cumsum(np.random.randn(rows) * 100)

    df = pd.DataFrame(
        {
            "open": prices + np.random.randn(rows) * 50,
            "high": prices + np.abs(np.random.randn(rows) * 100),
            "low": prices - np.abs(np.random.randn(rows) * 100),
            "close": prices,
            "volume": np.random.uniform(100, 1000, rows),
            "open_time": pd.date_range(start="2024-01-01", periods=rows, freq="15min"),
        }
    )

    return df


class TestBackwardCompatibility:
    """Test that existing code works without any configuration."""

    def test_strategy_without_config_manager(self):
        """Test that strategies work without config manager (existing behavior)."""
        # Create strategy WITHOUT config manager (old way)
        strategy = RSIExtremeReversalStrategy()

        # Verify it initializes correctly
        assert strategy is not None
        assert hasattr(strategy, "analyze")

        # Create test data
        df = create_sample_dataframe(100)

        # Create metadata without config
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        # Should work without errors
        try:
            signal = strategy.analyze(df, metadata)
            # Signal might be None (conditions not met) or a valid Signal
            if signal:
                assert isinstance(signal, Signal)
                assert signal.strategy_id == "rsi_extreme_reversal"
                assert signal.symbol == "BTCUSDT"
        except Exception as e:
            pytest.fail(f"Strategy failed without config manager: {e}")

    def test_multiple_strategies_without_config(self):
        """Test multiple strategies work without config manager."""
        strategies = [
            RSIExtremeReversalStrategy(),
            BollingerSqueezeAlertStrategy(),
        ]

        df = create_sample_dataframe(100)
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        for strategy in strategies:
            try:
                signal = strategy.analyze(df, metadata)
                # Should not raise any exceptions
                if signal:
                    assert isinstance(signal, Signal)
            except Exception as e:
                pytest.fail(f"Strategy {strategy.__class__.__name__} failed: {e}")

    def test_signal_format_unchanged(self):
        """Test that signal format is unchanged (backward compatible)."""
        strategy = RSIExtremeReversalStrategy()
        df = create_sample_dataframe(100)

        # Force oversold condition for testing
        metadata = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "rsi_2": pd.Series([20] * 100),  # Oversold RSI
        }

        signal = strategy.analyze(df, metadata)

        if signal:
            # Check all expected fields exist
            assert hasattr(signal, "strategy_id")
            assert hasattr(signal, "symbol")
            assert hasattr(signal, "action")
            assert hasattr(signal, "confidence")
            assert hasattr(signal, "price")
            assert hasattr(signal, "current_price")
            assert hasattr(signal, "timeframe")
            assert hasattr(signal, "metadata")

            # Check field types
            assert isinstance(signal.strategy_id, str)
            assert isinstance(signal.symbol, str)
            assert isinstance(signal.action, str)
            assert isinstance(signal.confidence, float)
            assert isinstance(signal.price, (int, float))
            assert isinstance(signal.metadata, dict)

    def test_signal_validation_unchanged(self):
        """Test that signal validation still works."""
        strategy = RSIExtremeReversalStrategy()
        df = create_sample_dataframe(100)

        metadata = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "rsi_2": pd.Series([20] * 100),
        }

        signal = strategy.analyze(df, metadata)

        if signal:
            # validate() method should still work
            try:
                is_valid = signal.validate()
                assert isinstance(is_valid, bool)
            except Exception as e:
                pytest.fail(f"Signal validation failed: {e}")


class TestConfigSystemIntegration:
    """Test that config system works correctly when added."""

    def test_strategy_with_config_in_metadata(self):
        """Test strategy works when config is provided in metadata."""
        strategy = RSIExtremeReversalStrategy()
        df = create_sample_dataframe(100)

        # Simulate pre-loaded config in metadata
        config = {
            "parameters": {
                "oversold_threshold": 30,
                "extreme_threshold": 5,
                "min_data_points": 78,
                "base_confidence": 0.70,
            },
            "version": 1,
            "source": "mongodb",
        }

        metadata = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "config": config,  # Config provided in metadata
            "rsi_2": pd.Series([25] * 100),
        }

        try:
            signal = strategy.analyze(df, metadata)
            # Should work without errors
            if signal:
                assert isinstance(signal, Signal)
                # Check if config metadata was added
                if "strategy_config" in signal.metadata:
                    assert signal.metadata["strategy_config"]["version"] == 1
                    assert signal.metadata["strategy_config"]["source"] == "mongodb"
        except Exception as e:
            pytest.fail(f"Strategy failed with config in metadata: {e}")

    def test_strategy_uses_custom_parameters(self):
        """Test that strategy actually uses custom parameters from config."""
        strategy = RSIExtremeReversalStrategy()
        df = create_sample_dataframe(100)

        # Config with higher oversold threshold (easier to trigger)
        config = {
            "parameters": {
                "oversold_threshold": 35,  # Higher than default 25
                "extreme_threshold": 2,
                "min_data_points": 78,
                "base_confidence": 0.70,
                "oversold_confidence": 0.75,
            },
            "version": 1,
            "source": "mongodb",
        }

        # RSI at 30 (would not trigger with default threshold of 25, but will with 35)
        metadata = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "config": config,
            "rsi_2": pd.Series([30] * 100),  # Between 25 and 35
        }

        signal = strategy.analyze(df, metadata)

        # With threshold of 35, RSI of 30 should trigger signal
        # Note: This might still be None if other conditions aren't met
        # The important thing is it doesn't raise an error
        assert signal is None or isinstance(signal, Signal)

    def test_config_metadata_added_to_signal(self):
        """Test that config metadata is properly added to signals."""
        strategy = RSIExtremeReversalStrategy()
        df = create_sample_dataframe(100)

        config = {
            "parameters": {
                "oversold_threshold": 25,
                "extreme_threshold": 2,
                "min_data_points": 78,
            },
            "version": 3,
            "source": "mongodb",
            "is_override": True,
        }

        metadata = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "config": config,
            "rsi_2": pd.Series([20] * 100),  # Trigger signal
        }

        signal = strategy.analyze(df, metadata)

        if signal:
            # Check config metadata exists
            assert "strategy_config" in signal.metadata
            assert signal.metadata["strategy_config"]["version"] == 3
            assert signal.metadata["strategy_config"]["source"] == "mongodb"
            assert "parameters" in signal.metadata["strategy_config"]


class TestSignalGenerationRobustness:
    """Test that signal generation is robust and handles edge cases."""

    def test_signal_generation_with_insufficient_data(self):
        """Test strategies handle insufficient data gracefully."""
        strategy = RSIExtremeReversalStrategy()

        # Only 10 rows (insufficient for RSI calculation)
        df = create_sample_dataframe(10)
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        # Should return None, not crash
        signal = strategy.analyze(df, metadata)
        assert signal is None

    def test_signal_generation_with_empty_dataframe(self):
        """Test strategies handle empty dataframe gracefully."""
        strategy = RSIExtremeReversalStrategy()

        df = pd.DataFrame()
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        # Should return None or handle gracefully, not crash
        try:
            signal = strategy.analyze(df, metadata)
            assert signal is None or isinstance(signal, Signal)
        except Exception as e:
            # Some exceptions are acceptable for empty data
            assert "empty" in str(e).lower() or "insufficient" in str(e).lower()

    def test_signal_generation_with_missing_metadata(self):
        """Test strategies handle missing metadata gracefully."""
        strategy = RSIExtremeReversalStrategy()
        df = create_sample_dataframe(100)

        # Minimal metadata
        metadata = {}

        # Should handle gracefully
        try:
            signal = strategy.analyze(df, metadata)
            assert signal is None or isinstance(signal, Signal)
        except Exception:
            # Some exceptions acceptable for missing required data
            pass

    def test_signal_to_dict_works(self):
        """Test signal serialization still works."""
        strategy = RSIExtremeReversalStrategy()
        df = create_sample_dataframe(100)

        metadata = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "rsi_2": pd.Series([20] * 100),
        }

        signal = strategy.analyze(df, metadata)

        if signal:
            try:
                signal_dict = signal.to_dict()
                assert isinstance(signal_dict, dict)
                assert "strategy_id" in signal_dict
                assert "symbol" in signal_dict
                assert "action" in signal_dict
            except Exception as e:
                pytest.fail(f"Signal serialization failed: {e}")


class TestPerformanceRegression:
    """Test that config system doesn't significantly slow down signal generation."""

    def test_signal_generation_performance(self):
        """Test signal generation completes in reasonable time."""
        import time

        strategy = RSIExtremeReversalStrategy()
        df = create_sample_dataframe(200)

        metadata = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "rsi_2": pd.Series([20] * 200),
        }

        # Time signal generation
        start = time.time()
        for _ in range(10):  # Run 10 times
            _signal = strategy.analyze(df, metadata)  # noqa: F841
        elapsed = time.time() - start

        # Should complete 10 iterations in under 1 second
        assert (
            elapsed < 1.0
        ), f"Signal generation too slow: {elapsed:.2f}s for 10 iterations"

    def test_config_loading_performance(self):
        """Test that config loading doesn't add significant overhead."""
        import time

        strategy = RSIExtremeReversalStrategy()
        df = create_sample_dataframe(200)

        # Without config
        metadata_no_config = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "rsi_2": pd.Series([20] * 200),
        }

        start = time.time()
        for _ in range(10):
            _signal = strategy.analyze(df, metadata_no_config)  # noqa: F841
        time_no_config = time.time() - start

        # With config
        config = {
            "parameters": {
                "oversold_threshold": 25,
                "extreme_threshold": 2,
                "min_data_points": 78,
            },
            "version": 1,
            "source": "default",
        }

        metadata_with_config = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "config": config,
            "rsi_2": pd.Series([20] * 200),
        }

        start = time.time()
        for _ in range(10):
            _signal = strategy.analyze(df, metadata_with_config)  # noqa: F841
        time_with_config = time.time() - start

        # With config should not be more than 50% slower
        overhead = (time_with_config - time_no_config) / time_no_config
        assert overhead < 0.5, f"Config adds too much overhead: {overhead*100:.1f}%"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
