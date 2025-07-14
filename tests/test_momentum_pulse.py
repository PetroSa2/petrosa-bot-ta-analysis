"""
Tests for the Momentum Pulse Strategy.
"""

import pytest
import pandas as pd
import numpy as np
from ta_bot.strategies.momentum_pulse import MomentumPulseStrategy
from ta_bot.models.signal import SignalType


class TestMomentumPulseStrategy:
    """Test cases for the MomentumPulseStrategy class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = MomentumPulseStrategy()

    def test_analyze_insufficient_data(self):
        """Test that analyze returns None for insufficient data."""
        df = pd.DataFrame({"open": [99], "high": [101], "low": [98], "close": [100], "volume": [1000]})  # Only 1 row
        indicators = {"macd_hist": [0.1], "rsi": [55], "adx": [25]}
        
        result = self.strategy.analyze(df, indicators)
        assert result is None

    def test_analyze_missing_indicators(self):
        """Test that analyze returns None when required indicators are missing."""
        df = pd.DataFrame({
            "open": [99, 100],
            "high": [101, 102],
            "low": [98, 99],
            "close": [100, 101],
            "volume": [1000, 1100]
        })
        indicators = {
            "macd_hist": [0.1, 0.2],
            "rsi": [55, 56]
            # Missing adx, ema21, ema50
        }
        
        result = self.strategy.analyze(df, indicators)
        assert result is None

    def test_analyze_no_macd_cross(self):
        """Test that analyze returns None when MACD histogram doesn't cross above."""
        df = pd.DataFrame({
            "open": [99, 100, 101],
            "high": [101, 102, 103],
            "low": [98, 99, 100],
            "close": [100, 101, 102],
            "volume": [1000, 1100, 1200]
        })
        indicators = {
            "macd_hist": [0.1, 0.2, 0.3],  # All positive, no cross
            "rsi": [55, 56, 57],
            "adx": [25, 26, 27],
            "ema21": [99, 100, 101],
            "ema50": [98, 99, 100],
            "close": [100, 101, 102]
        }
        
        result = self.strategy.analyze(df, indicators)
        assert result is None

    def test_analyze_rsi_out_of_range(self):
        """Test that analyze returns None when RSI is out of range."""
        df = pd.DataFrame({
            "open": [99, 100, 101],
            "high": [101, 102, 103],
            "low": [98, 99, 100],
            "close": [100, 101, 102],
            "volume": [1000, 1100, 1200]
        })
        indicators = {
            "macd_hist": [-0.1, 0.2, 0.3],  # Cross from negative to positive
            "rsi": [55, 70, 57],  # RSI above 65
            "adx": [25, 26, 27],
            "ema21": [99, 100, 101],
            "ema50": [98, 99, 100],
            "close": [100, 101, 102]
        }
        
        result = self.strategy.analyze(df, indicators)
        assert result is None

    def test_analyze_adx_too_low(self):
        """Test that analyze returns None when ADX is too low."""
        df = pd.DataFrame({
            "open": [99, 100, 101],
            "high": [101, 102, 103],
            "low": [98, 99, 100],
            "close": [100, 101, 102],
            "volume": [1000, 1100, 1200]
        })
        indicators = {
            "macd_hist": [-0.1, 0.2, 0.3],  # Cross from negative to positive
            "rsi": [55, 56, 57],  # RSI in range
            "adx": [25, 15, 27],  # ADX below 20
            "ema21": [99, 100, 101],
            "ema50": [98, 99, 100],
            "close": [100, 101, 102]
        }
        
        result = self.strategy.analyze(df, indicators)
        assert result is None

    def test_analyze_price_below_emas(self):
        """Test that analyze returns None when price is below EMAs."""
        df = pd.DataFrame({
            "open": [99, 100, 101],
            "high": [101, 102, 103],
            "low": [98, 99, 100],
            "close": [100, 101, 102],
            "volume": [1000, 1100, 1200]
        })
        indicators = {
            "macd_hist": [-0.1, 0.2, 0.3],  # Cross from negative to positive
            "rsi": [55, 56, 57],  # RSI in range
            "adx": [25, 26, 27],  # ADX above 20
            "ema21": [99, 102, 101],  # Price below EMA21
            "ema50": [98, 103, 100],  # Price below EMA50
            "close": [100, 101, 102]
        }
        
        result = self.strategy.analyze(df, indicators)
        assert result is None

    def test_analyze_successful_signal(self):
        """Test that analyze returns a signal when all conditions are met."""
        df = pd.DataFrame({
            "open": [99, 100, 101],
            "high": [101, 102, 103],
            "low": [98, 99, 100],
            "close": [100, 101, 102],
            "volume": [1000, 1100, 1200]
        })
        indicators = {
            "macd_hist": pd.Series([0.1, -0.1, 0.2]),  # Cross from negative to positive at the end
            "rsi": pd.Series([55, 56, 57]),  # RSI in range
            "adx": pd.Series([25, 26, 27]),  # ADX above 20
            "ema21": pd.Series([99, 100, 101]),  # Price above EMA21
            "ema50": pd.Series([98, 99, 100]),  # Price above EMA50
            "close": pd.Series([100, 101, 102]),
            "macd_signal": pd.Series([0.05, 0.06, 0.07])
        }
        
        result = self.strategy.analyze(df, indicators, "BTCUSDT", "15m")
        
        assert result is not None
        assert result.symbol == "BTCUSDT"
        assert result.period == "15m"
        assert result.signal == SignalType.BUY
        assert result.strategy == "momentum_pulse"
        assert result.confidence == 0.74
        assert "macd_hist" in result.metadata
        assert "macd_signal" in result.metadata
        assert "rsi" in result.metadata
        assert "volume" in result.metadata

    def test_analyze_with_volume_data(self):
        """Test that analyze works with volume data."""
        df = pd.DataFrame({
            "open": [99, 100, 101],
            "high": [101, 102, 103],
            "low": [98, 99, 100],
            "close": [100, 101, 102],
            "volume": [1000, 1100, 1200]
        })
        indicators = {
            "macd_hist": pd.Series([0.1, -0.1, 0.2]),
            "rsi": pd.Series([55, 56, 57]),
            "adx": pd.Series([25, 26, 27]),
            "ema21": pd.Series([99, 100, 101]),
            "ema50": pd.Series([98, 99, 100]),
            "close": pd.Series([100, 101, 102]),
            "volume": pd.Series([1000, 1100, 1200])
        }
        
        result = self.strategy.analyze(df, indicators, "ETHUSDT", "5m")
        
        assert result is not None
        assert result.symbol == "ETHUSDT"
        assert result.period == "5m"
        assert result.metadata["volume"] == 1200

    def test_analyze_edge_case_rsi_50(self):
        """Test that analyze works with RSI at the lower bound."""
        df = pd.DataFrame({
            "open": [99, 100, 101],
            "high": [101, 102, 103],
            "low": [98, 99, 100],
            "close": [100, 101, 102],
            "volume": [1000, 1100, 1200]
        })
        indicators = {
            "macd_hist": pd.Series([0.1, -0.1, 0.2]),
            "rsi": pd.Series([55, 50, 57]),  # RSI at lower bound
            "adx": pd.Series([25, 26, 27]),
            "ema21": pd.Series([99, 100, 101]),
            "ema50": pd.Series([98, 99, 100]),
            "close": pd.Series([100, 101, 102])
        }
        
        result = self.strategy.analyze(df, indicators)
        assert result is not None

    def test_analyze_edge_case_rsi_65(self):
        """Test that analyze works with RSI at the upper bound."""
        df = pd.DataFrame({
            "open": [99, 100, 101],
            "high": [101, 102, 103],
            "low": [98, 99, 100],
            "close": [100, 101, 102],
            "volume": [1000, 1100, 1200]
        })
        indicators = {
            "macd_hist": pd.Series([0.1, -0.1, 0.2]),
            "rsi": pd.Series([55, 65, 57]),  # RSI at upper bound
            "adx": pd.Series([25, 26, 27]),
            "ema21": pd.Series([99, 100, 101]),
            "ema50": pd.Series([98, 99, 100]),
            "close": pd.Series([100, 101, 102])
        }
        
        result = self.strategy.analyze(df, indicators)
        assert result is not None

    def test_analyze_edge_case_adx_20(self):
        """Test that analyze works with ADX at the minimum threshold."""
        df = pd.DataFrame({
            "open": [99, 100, 101],
            "high": [101, 102, 103],
            "low": [98, 99, 100],
            "close": [100, 101, 102],
            "volume": [1000, 1100, 1200]
        })
        indicators = {
            "macd_hist": pd.Series([0.1, -0.1, 0.2]),
            "rsi": pd.Series([55, 56, 57]),
            "adx": pd.Series([25, 20, 27]),  # ADX at minimum threshold
            "ema21": pd.Series([99, 100, 101]),
            "ema50": pd.Series([98, 99, 100]),
            "close": pd.Series([100, 101, 102])
        }
        
        result = self.strategy.analyze(df, indicators)
        assert result is not None

    def test_analyze_missing_macd_signal(self):
        """Test that analyze works when macd_signal is missing."""
        df = pd.DataFrame({
            "open": [99, 100, 101],
            "high": [101, 102, 103],
            "low": [98, 99, 100],
            "close": [100, 101, 102],
            "volume": [1000, 1100, 1200]
        })
        indicators = {
            "macd_hist": pd.Series([0.1, -0.1, 0.2]),
            "rsi": pd.Series([55, 56, 57]),
            "adx": pd.Series([25, 26, 27]),
            "ema21": pd.Series([99, 100, 101]),
            "ema50": pd.Series([98, 99, 100]),
            "close": pd.Series([100, 101, 102])
            # Missing macd_signal
        }
        
        result = self.strategy.analyze(df, indicators)
        assert result is not None
        assert result.metadata["macd_signal"] == 0  # Default value

    def test_analyze_missing_volume(self):
        """Test that analyze works when volume is missing."""
        df = pd.DataFrame({
            "open": [99, 100, 101],
            "high": [101, 102, 103],
            "low": [98, 99, 100],
            "close": [100, 101, 102],
            "volume": [1000, 1100, 1200]  # Include volume to avoid KeyError
        })
        indicators = {
            "macd_hist": pd.Series([0.1, -0.1, 0.2]),
            "rsi": pd.Series([55, 56, 57]),
            "adx": pd.Series([25, 26, 27]),
            "ema21": pd.Series([99, 100, 101]),
            "ema50": pd.Series([98, 99, 100]),
            "close": pd.Series([100, 101, 102])
        }
        
        result = self.strategy.analyze(df, indicators)
        assert result is not None
        assert result.metadata["volume"] == 1200  # Should use actual volume value 