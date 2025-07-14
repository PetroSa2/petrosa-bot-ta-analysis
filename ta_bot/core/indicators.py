"""
Technical indicators wrapper using pandas-ta.
"""

import pandas as pd
import pandas_ta as ta
from typing import Tuple, Optional
import numpy as np


class Indicators:
    """Wrapper for technical indicators using pandas-ta."""
    
    @staticmethod
    def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        return df.ta.rsi(length=period)
    
    @staticmethod
    def macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD indicator."""
        macd_result = df.ta.macd(fast=fast, slow=slow, signal=signal)
        return macd_result['MACD_12_26_9'], macd_result['MACDs_12_26_9'], macd_result['MACDh_12_26_9']
    
    @staticmethod
    def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ADX indicator."""
        adx_result = df.ta.adx(length=period)
        return adx_result['ADX_14']
    
    @staticmethod
    def bollinger_bands(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands."""
        bb_result = df.ta.bbands(length=period, std=std)
        return bb_result['BBL_20_2.0'], bb_result['BBM_20_2.0'], bb_result['BBU_20_2.0']
    
    @staticmethod
    def ema(df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate EMA indicator."""
        return df.ta.ema(length=period)
    
    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        return df.ta.atr(length=period)
    
    @staticmethod
    def vwap(df: pd.DataFrame) -> pd.Series:
        """Calculate VWAP indicator."""
        try:
            return df.ta.vwap()
        except AttributeError:
            # Fallback for non-datetime index
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
            return vwap
    
    @staticmethod
    def volume_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate Volume Simple Moving Average."""
        return df['volume'].rolling(window=period).mean()
    
    @staticmethod
    def price_range(df: pd.DataFrame, period: int = 10) -> pd.Series:
        """Calculate price range (high - low) over period."""
        return (df['high'] - df['low']).rolling(window=period).mean()
    
    @staticmethod
    def candle_wick_ratio(df: pd.DataFrame) -> pd.Series:
        """Calculate candle wick ratio (body vs wick)."""
        body = abs(df['close'] - df['open'])
        total_range = df['high'] - df['low']
        wick = total_range - body
        return wick / total_range
    
    @staticmethod
    def is_inside_candle(df: pd.DataFrame) -> pd.Series:
        """Check if current candle is inside the previous candle."""
        return (df['high'] <= df['high'].shift(1)) & (df['low'] >= df['low'].shift(1))
    
    @staticmethod
    def is_outside_candle(df: pd.DataFrame) -> pd.Series:
        """Check if current candle engulfs the previous candle."""
        return (df['high'] > df['high'].shift(1)) & (df['low'] < df['low'].shift(1)) 