"""
Technical indicators wrapper using pandas-ta.
"""

from typing import Tuple

import pandas as pd
import pandas_ta_classic as ta

# Ensure pandas DataFrame has ta attribute
pd.DataFrame.ta = ta


class Indicators:
    """Wrapper for technical indicators using pandas-ta."""

    @staticmethod
    def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        result = df.ta.rsi(close=df["close"], length=period)
        return result if result is not None else pd.Series(dtype=float)

    @staticmethod
    def macd(
        df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD indicator."""
        macd_result = df.ta.macd(close=df["close"], fast=fast, slow=slow, signal=signal)
        if macd_result is None or macd_result.empty:
            # Return empty series for insufficient data
            empty_series = pd.Series(dtype=float)
            return empty_series, empty_series, empty_series
        # Handle different column naming conventions between pandas-ta versions
        macd_col = f"MACD_{fast}_{slow}_{signal}"
        macds_col = (
            f"MACDS_{fast}_{slow}_{signal}"
            if f"MACDS_{fast}_{slow}_{signal}" in macd_result.columns
            else f"MACDs_{fast}_{slow}_{signal}"
        )
        macdh_col = (
            f"MACDH_{fast}_{slow}_{signal}"
            if f"MACDH_{fast}_{slow}_{signal}" in macd_result.columns
            else f"MACDh_{fast}_{slow}_{signal}"
        )
        return (
            macd_result[macd_col],
            macd_result[macds_col],
            macd_result[macdh_col],
        )

    @staticmethod
    def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ADX indicator."""
        adx_result = df.ta.adx(
            high=df["high"], low=df["low"], close=df["close"], length=period
        )
        if adx_result is None or adx_result.empty:
            return pd.Series(dtype=float)
        return adx_result["ADX_14"]

    @staticmethod
    def bollinger_bands(
        df: pd.DataFrame, period: int = 20, std: float = 2.0
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands."""
        bb_result = df.ta.bbands(close=df["close"], length=period, std=std)
        if bb_result is None or bb_result.empty:
            empty_series = pd.Series(dtype=float)
            return empty_series, empty_series, empty_series
        # Handle different column naming conventions between pandas-ta versions
        bbl_col = (
            f"BBL_{period}_{std}"
            if f"BBL_{period}_{std}" in bb_result.columns
            else f"BBL_{period}"
        )
        bbm_col = (
            f"BBM_{period}_{std}"
            if f"BBM_{period}_{std}" in bb_result.columns
            else f"BBM_{period}"
        )
        bbu_col = (
            f"BBU_{period}_{std}"
            if f"BBU_{period}_{std}" in bb_result.columns
            else f"BBU_{period}"
        )
        return bb_result[bbl_col], bb_result[bbm_col], bb_result[bbu_col]

    @staticmethod
    def ema(df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate EMA indicator."""
        result = df.ta.ema(close=df["close"], length=period)
        return result if result is not None else pd.Series(dtype=float)

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        result = df.ta.atr(
            high=df["high"], low=df["low"], close=df["close"], length=period
        )
        return result if result is not None else pd.Series(dtype=float)

    @staticmethod
    def vwap(df: pd.DataFrame) -> pd.Series:
        """Calculate VWAP indicator."""
        try:
            return df.ta.vwap(
                high=df["high"], low=df["low"], close=df["close"], volume=df["volume"]
            )
        except AttributeError:
            # Fallback for non-datetime index
            typical_price = (df["high"] + df["low"] + df["close"]) / 3
            vwap = (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()
            return vwap

    @staticmethod
    def volume_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate Volume Simple Moving Average."""
        return df["volume"].rolling(window=period).mean()

    @staticmethod
    def price_range(df: pd.DataFrame, period: int = 10) -> pd.Series:
        """Calculate price range (high - low) over period."""
        return (df["high"] - df["low"]).rolling(window=period).mean()

    @staticmethod
    def candle_wick_ratio(df: pd.DataFrame) -> pd.Series:
        """Calculate candle wick ratio (body vs wick)."""
        body = abs(df["close"] - df["open"])
        total_range = df["high"] - df["low"]
        wick = total_range - body
        return wick / total_range

    @staticmethod
    def is_inside_candle(df: pd.DataFrame) -> pd.Series:
        """Check if current candle is inside the previous candle."""
        return (df["high"] <= df["high"].shift(1)) & (df["low"] >= df["low"].shift(1))

    @staticmethod
    def is_outside_candle(df: pd.DataFrame) -> pd.Series:
        """Check if current candle engulfs the previous candle."""
        return (df["high"] > df["high"].shift(1)) & (df["low"] < df["low"].shift(1))
