"""
Tests for the indicators module.
"""

import pytest
import pandas as pd
import numpy as np
from ta_bot.core.indicators import Indicators


class TestIndicators:
    """Test cases for the indicators module."""

    def setup_method(self):
        """Set up test fixtures."""
        self.indicators = Indicators()

    def test_rsi_basic(self):
        """Test RSI calculation."""
        df = pd.DataFrame(
            {
                "close": [
                    100,
                    101,
                    102,
                    103,
                    104,
                    105,
                    106,
                    107,
                    108,
                    109,
                    110,
                    111,
                    112,
                    113,
                    114,
                ]
            }
        )

        rsi = Indicators.rsi(df)

        assert isinstance(rsi, pd.Series)
        assert len(rsi) == len(df)

    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data."""
        df = pd.DataFrame({"close": [100, 101, 102]})  # Less than 14 periods

        rsi = Indicators.rsi(df)

        assert isinstance(rsi, pd.Series)
        # Should be all NaN or empty for insufficient data
        assert rsi.isna().all() or rsi.empty or len(rsi) == len(df)

    def test_macd_basic(self):
        """Test MACD calculation."""
        df = pd.DataFrame(
            {
                "close": [
                    100,
                    101,
                    102,
                    103,
                    104,
                    105,
                    106,
                    107,
                    108,
                    109,
                    110,
                    111,
                    112,
                    113,
                    114,
                ]
            }
        )

        macd, signal, hist = Indicators.macd(df)

        assert isinstance(macd, pd.Series)
        assert isinstance(signal, pd.Series)
        assert isinstance(hist, pd.Series)
        # For short data, may be all NaN or empty
        assert macd.isna().all() or macd.empty or len(macd) == len(df)
        assert signal.isna().all() or signal.empty or len(signal) == len(df)
        assert hist.isna().all() or hist.empty or len(hist) == len(df)

    def test_macd_insufficient_data(self):
        """Test MACD with insufficient data."""
        df = pd.DataFrame({"close": [100, 101, 102]})  # Less than 26 periods

        macd, signal, hist = Indicators.macd(df)

        assert isinstance(macd, pd.Series)
        assert isinstance(signal, pd.Series)
        assert isinstance(hist, pd.Series)

    def test_adx_basic(self):
        """Test ADX calculation."""
        df = pd.DataFrame(
            {
                "high": [
                    105,
                    106,
                    107,
                    108,
                    109,
                    110,
                    111,
                    112,
                    113,
                    114,
                    115,
                    116,
                    117,
                    118,
                    119,
                ],
                "low": [
                    95,
                    96,
                    97,
                    98,
                    99,
                    100,
                    101,
                    102,
                    103,
                    104,
                    105,
                    106,
                    107,
                    108,
                    109,
                ],
                "close": [
                    100,
                    101,
                    102,
                    103,
                    104,
                    105,
                    106,
                    107,
                    108,
                    109,
                    110,
                    111,
                    112,
                    113,
                    114,
                ],
            }
        )

        adx = Indicators.adx(df)

        assert isinstance(adx, pd.Series)
        assert len(adx) == len(df)

    def test_adx_insufficient_data(self):
        """Test ADX with insufficient data."""
        df = pd.DataFrame(
            {"high": [105, 106, 107], "low": [95, 96, 97], "close": [100, 101, 102]}
        )

        adx = Indicators.adx(df)

        assert isinstance(adx, pd.Series)
        # Should be all NaN or empty for insufficient data
        assert adx.isna().all() or adx.empty or len(adx) == len(df)

    def test_bollinger_bands_basic(self):
        """Test Bollinger Bands calculation."""
        df = pd.DataFrame(
            {
                "close": [
                    100,
                    101,
                    102,
                    103,
                    104,
                    105,
                    106,
                    107,
                    108,
                    109,
                    110,
                    111,
                    112,
                    113,
                    114,
                    115,
                    116,
                    117,
                    118,
                    119,
                    120,
                ]
            }
        )

        lower, middle, upper = Indicators.bollinger_bands(df)

        assert isinstance(lower, pd.Series)
        assert isinstance(middle, pd.Series)
        assert isinstance(upper, pd.Series)
        assert len(lower) == len(df)
        assert len(middle) == len(df)
        assert len(upper) == len(df)

    def test_bollinger_bands_insufficient_data(self):
        """Test Bollinger Bands with insufficient data."""
        df = pd.DataFrame({"close": [100, 101, 102]})  # Less than 20 periods

        lower, middle, upper = Indicators.bollinger_bands(df)

        assert isinstance(lower, pd.Series)
        assert isinstance(middle, pd.Series)
        assert isinstance(upper, pd.Series)

    def test_ema_basic(self):
        """Test EMA calculation."""
        df = pd.DataFrame(
            {
                "close": [
                    100,
                    101,
                    102,
                    103,
                    104,
                    105,
                    106,
                    107,
                    108,
                    109,
                    110,
                    111,
                    112,
                    113,
                    114,
                ]
            }
        )

        ema = Indicators.ema(df, period=21)

        assert isinstance(ema, pd.Series)
        # For short data, may be all NaN or empty
        assert ema.isna().all() or ema.empty or len(ema) == len(df)

    def test_ema_insufficient_data(self):
        """Test EMA with insufficient data."""
        df = pd.DataFrame({"close": [100, 101, 102]})

        ema = Indicators.ema(df, period=21)

        assert isinstance(ema, pd.Series)
        # Should be all NaN or empty for insufficient data
        assert ema.isna().all() or ema.empty or len(ema) == len(df)

    def test_atr_basic(self):
        """Test ATR calculation."""
        df = pd.DataFrame(
            {
                "high": [
                    105,
                    106,
                    107,
                    108,
                    109,
                    110,
                    111,
                    112,
                    113,
                    114,
                    115,
                    116,
                    117,
                    118,
                    119,
                ],
                "low": [
                    95,
                    96,
                    97,
                    98,
                    99,
                    100,
                    101,
                    102,
                    103,
                    104,
                    105,
                    106,
                    107,
                    108,
                    109,
                ],
                "close": [
                    100,
                    101,
                    102,
                    103,
                    104,
                    105,
                    106,
                    107,
                    108,
                    109,
                    110,
                    111,
                    112,
                    113,
                    114,
                ],
            }
        )

        atr = Indicators.atr(df)

        assert isinstance(atr, pd.Series)
        assert len(atr) == len(df)

    def test_vwap_basic(self):
        """Test VWAP calculation."""
        df = pd.DataFrame(
            {
                "high": [105, 106, 107],
                "low": [95, 96, 97],
                "close": [100, 101, 102],
                "volume": [1000, 1100, 1200],
            }
        )

        vwap = Indicators.vwap(df)

        assert isinstance(vwap, pd.Series)
        assert len(vwap) == len(df)

    def test_volume_sma_basic(self):
        """Test Volume SMA calculation."""
        df = pd.DataFrame(
            {
                "volume": [
                    1000,
                    1100,
                    1200,
                    1300,
                    1400,
                    1500,
                    1600,
                    1700,
                    1800,
                    1900,
                    2000,
                    2100,
                    2200,
                    2300,
                    2400,
                    2500,
                    2600,
                    2700,
                    2800,
                    2900,
                    3000,
                ]
            }
        )

        volume_sma = Indicators.volume_sma(df, period=20)

        assert isinstance(volume_sma, pd.Series)
        assert len(volume_sma) == len(df)

    def test_price_range_basic(self):
        """Test price range calculation."""
        df = pd.DataFrame(
            {
                "high": [105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115],
                "low": [95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105],
            }
        )

        price_range = Indicators.price_range(df, period=10)

        assert isinstance(price_range, pd.Series)
        assert len(price_range) == len(df)

    def test_candle_wick_ratio_basic(self):
        """Test candle wick ratio calculation."""
        df = pd.DataFrame(
            {
                "open": [100, 101, 102],
                "high": [105, 106, 107],
                "low": [95, 96, 97],
                "close": [102, 103, 104],
            }
        )

        wick_ratio = Indicators.candle_wick_ratio(df)

        assert isinstance(wick_ratio, pd.Series)
        assert len(wick_ratio) == len(df)

    def test_is_inside_candle_basic(self):
        """Test inside candle detection."""
        df = pd.DataFrame(
            {"high": [105, 104, 106], "low": [95, 96, 94]}  # Second candle inside first
        )

        inside_candle = Indicators.is_inside_candle(df)

        assert isinstance(inside_candle, pd.Series)
        assert len(inside_candle) == len(df)

    def test_is_outside_candle_basic(self):
        """Test outside candle detection."""
        df = pd.DataFrame(
            {
                "high": [105, 107, 106],  # Second candle engulfs first
                "low": [95, 93, 94],
            }
        )

        outside_candle = Indicators.is_outside_candle(df)

        assert isinstance(outside_candle, pd.Series)
        assert len(outside_candle) == len(df)

    def test_indicators_with_nan_values(self):
        """Test indicators with NaN values."""
        df = pd.DataFrame(
            {
                "open": [100, np.nan, 102],
                "high": [105, 106, np.nan],
                "low": [95, 96, 97],
                "close": [102, 103, 104],
                "volume": [1000, 1100, 1200],
            }
        )

        # Test RSI with NaN values
        rsi = Indicators.rsi(df)
        assert isinstance(rsi, pd.Series)

        # Test MACD with NaN values
        macd, signal, hist = Indicators.macd(df)
        assert isinstance(macd, pd.Series)
        assert isinstance(signal, pd.Series)
        assert isinstance(hist, pd.Series)

    def test_indicators_with_constant_values(self):
        """Test indicators with constant values."""
        df = pd.DataFrame(
            {
                "open": [100] * 50,
                "high": [105] * 50,
                "low": [95] * 50,
                "close": [102] * 50,
                "volume": [1000] * 50,
            }
        )

        # Test RSI with constant values
        rsi = Indicators.rsi(df)
        assert isinstance(rsi, pd.Series)

        # Test MACD with constant values
        macd, signal, hist = Indicators.macd(df)
        assert isinstance(macd, pd.Series)
        assert isinstance(signal, pd.Series)
        assert isinstance(hist, pd.Series)

    def test_indicators_with_extreme_values(self):
        """Test indicators with extreme values."""
        df = pd.DataFrame(
            {
                "open": [0.001, 1000000, 0.001],
                "high": [0.002, 1000001, 0.002],
                "low": [0.0005, 999999, 0.0005],
                "close": [0.0015, 1000000.5, 0.0015],
                "volume": [1, 999999999, 1],
            }
        )

        # Test RSI with extreme values
        rsi = Indicators.rsi(df)
        assert isinstance(rsi, pd.Series)

        # Test MACD with extreme values
        macd, signal, hist = Indicators.macd(df)
        assert isinstance(macd, pd.Series)
        assert isinstance(signal, pd.Series)
        assert isinstance(hist, pd.Series)
