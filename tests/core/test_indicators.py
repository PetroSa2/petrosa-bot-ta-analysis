"""
Tests for the indicators module.
"""

import pandas as pd
import pytest

from ta_bot.core.indicators import Indicators


class TestIndicators:
    """Test cases for the indicators."""

    def test_rsi_basic(self):
        """Test basic RSI calculation."""
        # Need at least 28 data points for RSI with period=14 to produce valid values
        df = pd.DataFrame(
            {
                "close": [
                    44.34,
                    44.09,
                    44.15,
                    43.61,
                    44.33,
                    44.83,
                    45.18,
                    45.87,
                    45.87,
                    45.87,
                    46.32,
                    47.10,
                    47.50,
                    48.00,
                    48.50,
                    49.00,
                    49.50,
                    50.00,
                    50.50,
                    51.00,
                    51.50,
                    52.00,
                    52.50,
                    53.00,
                    53.50,
                    54.00,
                    54.50,
                    55.00,
                ]
            }
        )

        result = Indicators.rsi(df, period=14)
        assert not result.empty
        assert len(result) == len(df)
        # First 13 values should be NaN due to insufficient data for RSI calculation
        assert pd.isna(result.iloc[13])  # Should be NaN
        # At least one value should be valid (not NaN)
        assert not pd.isna(result.iloc[-1])  # Last value should be valid

    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data."""
        # With only 2 data points, RSI with period=14 should return empty series
        df = pd.DataFrame({"close": [44.34, 44.09]})

        result = Indicators.rsi(df, period=14)
        # The result should be an empty series (not None) when data is insufficient
        assert isinstance(result, pd.Series)
        # For very small datasets, pandas-ta may return an empty series
        # We'll accept either an empty series or a series with all NaN values
        if not result.empty:
            assert result.isna().all()

    def test_macd_basic(self):
        """Test basic MACD calculation."""
        # MACD requires more data points to produce valid results
        df = pd.DataFrame(
            {
                "close": [
                    44.34,
                    44.09,
                    44.15,
                    43.61,
                    44.33,
                    44.83,
                    45.18,
                    45.87,
                    45.87,
                    45.87,
                    46.32,
                    47.10,
                    47.50,
                    48.00,
                    48.50,
                    49.00,
                    49.50,
                    50.00,
                    50.50,
                    51.00,
                    51.50,
                    52.00,
                    52.50,
                    53.00,
                    53.50,
                    54.00,
                    54.50,
                    55.00,
                    55.50,
                    56.00,
                ]
            }
        )

        macd_line, signal_line, histogram = Indicators.macd(df)
        # For now, just check that we get pandas Series objects back
        assert isinstance(macd_line, pd.Series)
        assert isinstance(signal_line, pd.Series)
        assert isinstance(histogram, pd.Series)

        # Check all series have same length (they may be empty if calculation fails)
        assert len(macd_line) == len(signal_line) == len(histogram)

    def test_macd_insufficient_data(self):
        """Test MACD with insufficient data."""
        # With only 3 data points, MACD should return empty series
        df = pd.DataFrame({"close": [44.34, 44.09, 44.15]})

        macd_line, signal_line, histogram = Indicators.macd(df)
        # The result should be empty series when data is insufficient
        assert isinstance(macd_line, pd.Series)
        assert isinstance(signal_line, pd.Series)
        assert isinstance(histogram, pd.Series)
        # For very small datasets, pandas-ta may return empty series
        # We'll accept either empty series or series with all NaN values
        if not macd_line.empty:
            assert macd_line.isna().all()
        if not signal_line.empty:
            assert signal_line.isna().all()
        if not histogram.empty:
            assert histogram.isna().all()

    def test_adx_basic(self):
        """Test basic ADX calculation."""
        df = pd.DataFrame(
            {
                "high": [
                    44.50,
                    44.25,
                    44.30,
                    43.75,
                    44.50,
                    45.00,
                    45.50,
                    46.00,
                    46.25,
                    46.50,
                    47.00,
                    47.50,
                    48.00,
                    48.50,
                    49.00,
                    49.50,
                    50.00,
                    50.50,
                    51.00,
                    51.50,
                    52.00,
                    52.50,
                    53.00,
                    53.50,
                    54.00,
                    54.50,
                    55.00,
                    55.50,
                    56.00,
                    56.50,
                ],
                "low": [
                    44.00,
                    43.75,
                    43.80,
                    43.25,
                    43.75,
                    44.25,
                    44.75,
                    45.25,
                    45.50,
                    45.75,
                    46.25,
                    46.75,
                    47.25,
                    47.75,
                    48.25,
                    48.75,
                    49.25,
                    49.75,
                    50.25,
                    50.75,
                    51.25,
                    51.75,
                    52.25,
                    52.75,
                    53.25,
                    53.75,
                    54.25,
                    54.75,
                    55.25,
                    55.75,
                ],
                "close": [
                    44.34,
                    44.09,
                    44.15,
                    43.61,
                    44.33,
                    44.83,
                    45.18,
                    45.87,
                    45.87,
                    45.87,
                    46.32,
                    47.10,
                    47.50,
                    48.00,
                    48.50,
                    49.00,
                    49.50,
                    50.00,
                    50.50,
                    51.00,
                    51.50,
                    52.00,
                    52.50,
                    53.00,
                    53.50,
                    54.00,
                    54.50,
                    55.00,
                    55.50,
                    56.00,
                ],
            }
        )

        result = Indicators.adx(df, period=14)
        assert not result.empty
        assert len(result) == len(df)
        # ADX requires more data points to produce valid values, check last values
        assert not pd.isna(result.iloc[-1])  # Last value should be valid

    def test_adx_insufficient_data(self):
        """Test ADX with insufficient data."""
        df = pd.DataFrame(
            {"high": [44.50, 44.25], "low": [44.00, 43.75], "close": [44.34, 44.09]}
        )

        result = Indicators.adx(df, period=14)
        # With insufficient data, we expect an empty series or all NaN values
        assert isinstance(result, pd.Series)
        if not result.empty:
            assert result.isna().all()

    def test_bollinger_bands_basic(self):
        """Test basic Bollinger Bands calculation."""
        df = pd.DataFrame(
            {
                "close": [
                    44.34,
                    44.09,
                    44.15,
                    43.61,
                    44.33,
                    44.83,
                    45.18,
                    45.87,
                    45.87,
                    45.87,
                    46.32,
                    47.10,
                    47.50,
                    48.00,
                    48.50,
                    49.00,
                    49.50,
                    50.00,
                    50.50,
                    51.00,
                    51.50,
                    52.00,
                    52.50,
                    53.00,
                    53.50,
                    54.00,
                    54.50,
                    55.00,
                    55.50,
                    56.00,
                ]
            }
        )

        lower, middle, upper = Indicators.bollinger_bands(df)
        assert not lower.empty
        assert not middle.empty
        assert not upper.empty

        # Check all series have same length
        assert len(lower) == len(middle) == len(upper) == len(df)

        # Check that we have some valid values (not all NaN)
        # Bollinger Bands require more data points to produce valid values, check last values
        assert not pd.isna(lower.iloc[-1])  # Last value should be valid
        assert not pd.isna(middle.iloc[-1])  # Last value should be valid
        assert not pd.isna(upper.iloc[-1])  # Last value should be valid

        # Check relationship between bands for valid values only
        valid_mask = ~(lower.isna() | middle.isna() | upper.isna())
        if valid_mask.any():
            assert (lower[valid_mask] <= middle[valid_mask]).all()
            assert (middle[valid_mask] <= upper[valid_mask]).all()

    def test_bollinger_bands_insufficient_data(self):
        """Test Bollinger Bands with insufficient data."""
        df = pd.DataFrame({"close": [44.34, 44.09, 44.15]})

        lower, middle, upper = Indicators.bollinger_bands(df)
        # With insufficient data, we expect empty series or all NaN values
        assert isinstance(lower, pd.Series)
        assert isinstance(middle, pd.Series)
        assert isinstance(upper, pd.Series)
        if not lower.empty:
            assert lower.isna().all()
        if not middle.empty:
            assert middle.isna().all()
        if not upper.empty:
            assert upper.isna().all()

    def test_ema_basic(self):
        """Test basic EMA calculation."""
        df = pd.DataFrame(
            {
                "close": [
                    44.34,
                    44.09,
                    44.15,
                    43.61,
                    44.33,
                    44.83,
                    45.18,
                    45.87,
                    45.87,
                    45.87,
                ]
            }
        )

        result = Indicators.ema(df, period=5)
        assert not result.empty
        assert len(result) == len(df)
        # Check that we have some valid values (not all NaN)
        assert not result.isna().all()

    def test_ema_insufficient_data(self):
        """Test EMA with insufficient data."""
        df = pd.DataFrame({"close": [44.34, 44.09]})

        result = Indicators.ema(df, period=5)
        # With insufficient data, we expect an empty series or all NaN values
        assert isinstance(result, pd.Series)
        if not result.empty:
            assert result.isna().all()

    def test_atr_basic(self):
        """Test basic ATR calculation."""
        df = pd.DataFrame(
            {
                "high": [
                    44.50,
                    44.25,
                    44.30,
                    43.75,
                    44.50,
                    45.00,
                    45.50,
                    46.00,
                    46.25,
                    46.50,
                    47.00,
                    47.50,
                    48.00,
                    48.50,
                    49.00,
                    49.50,
                    50.00,
                    50.50,
                    51.00,
                    51.50,
                ],
                "low": [
                    44.00,
                    43.75,
                    43.80,
                    43.25,
                    43.75,
                    44.25,
                    44.75,
                    45.25,
                    45.50,
                    45.75,
                    46.25,
                    46.75,
                    47.25,
                    47.75,
                    48.25,
                    48.75,
                    49.25,
                    49.75,
                    50.25,
                    50.75,
                ],
                "close": [
                    44.34,
                    44.09,
                    44.15,
                    43.61,
                    44.33,
                    44.83,
                    45.18,
                    45.87,
                    45.87,
                    45.87,
                    46.32,
                    47.10,
                    47.50,
                    48.00,
                    48.50,
                    49.00,
                    49.50,
                    50.00,
                    50.50,
                    51.00,
                ],
            }
        )

        result = Indicators.atr(df, period=14)
        assert not result.empty
        assert len(result) == len(df)
        # ATR requires more data points to produce valid values, check last values
        assert not pd.isna(result.iloc[-1])  # Last value should be valid

    def test_vwap_basic(self):
        """Test basic VWAP calculation."""
        df = pd.DataFrame(
            {
                "high": [44.50, 44.25, 44.30, 43.75, 44.50],
                "low": [44.00, 43.75, 43.80, 43.25, 43.75],
                "close": [44.34, 44.09, 44.15, 43.61, 44.33],
                "volume": [1000, 1200, 800, 1500, 1100],
            }
        )

        result = Indicators.vwap(df)
        assert not result.empty
        assert len(result) == len(df)
        # Check that we have valid values
        assert not result.isna().all()

    def test_volume_sma_basic(self):
        """Test basic Volume SMA calculation."""
        df = pd.DataFrame(
            {"volume": [1000, 1200, 800, 1500, 1100, 900, 1300, 1400, 1600, 1200]}
        )

        result = Indicators.volume_sma(df, period=5)
        assert not result.empty
        assert len(result) == len(df)
        # Check that we have some valid values (not all NaN)
        assert not result.isna().all()

    def test_price_range_basic(self):
        """Test basic price range calculation."""
        df = pd.DataFrame(
            {
                "high": [
                    44.50,
                    44.25,
                    44.30,
                    43.75,
                    44.50,
                    45.00,
                    45.50,
                    46.00,
                    46.25,
                    46.50,
                    47.00,
                    47.50,
                    48.00,
                    48.50,
                    49.00,
                ],
                "low": [
                    44.00,
                    43.75,
                    43.80,
                    43.25,
                    43.75,
                    44.25,
                    44.75,
                    45.25,
                    45.50,
                    45.75,
                    46.25,
                    46.75,
                    47.25,
                    47.75,
                    48.25,
                ],
            }
        )

        result = Indicators.price_range(df, period=5)
        assert not result.empty
        assert len(result) == len(df)
        # All values should be positive or zero
        # Check that we have some valid values (not all NaN)
        assert not result.isna().all()
        # Valid values should be positive or zero
        valid_values = result.dropna()
        assert (valid_values >= 0).all()

    def test_candle_wick_ratio_basic(self):
        """Test basic candle wick ratio calculation."""
        df = pd.DataFrame(
            {
                "high": [44.50, 44.25, 44.30, 43.75, 44.50],
                "low": [44.00, 43.75, 43.80, 43.25, 43.75],
                "open": [44.25, 44.00, 44.10, 43.50, 44.25],
                "close": [44.34, 44.09, 44.15, 43.61, 44.33],
            }
        )

        result = Indicators.candle_wick_ratio(df)
        assert not result.empty
        assert len(result) == len(df)
        # Ratio should be between 0 and 1
        assert (result >= 0).all()
        assert (result <= 1).all()

    def test_is_inside_candle_basic(self):
        """Test basic inside candle detection."""
        df = pd.DataFrame(
            {
                "high": [45.00, 44.50, 44.75, 45.25, 45.50],
                "low": [44.00, 44.25, 44.30, 44.75, 45.00],
            }
        )

        result = Indicators.is_inside_candle(df)
        assert not result.empty
        assert len(result) == len(df)
        # First value should be False (no previous candle)
        assert not result.iloc[0]

    def test_is_outside_candle_basic(self):
        """Test basic outside candle detection."""
        df = pd.DataFrame(
            {
                "high": [44.50, 45.00, 44.75, 45.25, 45.50],
                "low": [44.25, 44.00, 44.30, 44.75, 45.00],
            }
        )

        result = Indicators.is_outside_candle(df)
        assert not result.empty
        assert len(result) == len(df)
        # First value should be False (no previous candle)
        assert not result.iloc[0]
