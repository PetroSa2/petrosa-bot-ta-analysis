"""
Base strategy class for technical analysis strategies.
"""

import pandas as pd
from typing import Dict, Any, Optional

from ta_bot.models.signal import Signal


class BaseStrategy:
    """Base class for all trading strategies."""

    def __init__(self):
        """Initialize the strategy."""
        pass

    def analyze(self, df: pd.DataFrame, metadata: Dict[str, Any]) -> Optional[Signal]:
        """
        Analyze candles and return a trading signal.

        Args:
            df: DataFrame with OHLCV data
            metadata: Additional metadata (symbol, period, etc.)

        Returns:
            Signal object if conditions are met, None otherwise
        """
        raise NotImplementedError("Subclasses must implement analyze method")

    def _get_current_values(
        self, indicators: Dict[str, Any], df: pd.DataFrame
    ) -> Dict[str, float]:
        """Get current values of indicators for the latest candle."""
        current_values = {}

        for indicator_name, indicator_series in indicators.items():
            if isinstance(indicator_series, pd.Series) and len(indicator_series) > 0:
                current_values[indicator_name] = float(indicator_series.iloc[-1])

        # Add current price data
        if len(df) > 0:
            current_values["open"] = float(df["open"].iloc[-1])
            current_values["high"] = float(df["high"].iloc[-1])
            current_values["low"] = float(df["low"].iloc[-1])
            current_values["close"] = float(df["close"].iloc[-1])
            current_values["volume"] = float(df["volume"].iloc[-1])

        return current_values

    def _get_previous_values(
        self, indicators: Dict[str, Any], df: pd.DataFrame
    ) -> Dict[str, float]:
        """Get previous values of indicators for the previous candle."""
        previous_values = {}

        for indicator_name, indicator_series in indicators.items():
            if isinstance(indicator_series, pd.Series) and len(indicator_series) > 1:
                previous_values[indicator_name] = float(indicator_series.iloc[-2])

        # Add previous price data
        if len(df) > 1:
            previous_values["open"] = float(df["open"].iloc[-2])
            previous_values["high"] = float(df["high"].iloc[-2])
            previous_values["low"] = float(df["low"].iloc[-2])
            previous_values["close"] = float(df["close"].iloc[-2])
            previous_values["volume"] = float(df["volume"].iloc[-2])

        return previous_values

    def _check_cross_above(
        self, current: float, previous: float, threshold: float = 0
    ) -> bool:
        """Check if a value crossed above a threshold."""
        return previous <= threshold and current > threshold

    def _check_cross_below(
        self, current: float, previous: float, threshold: float = 0
    ) -> bool:
        """Check if a value crossed below a threshold."""
        return previous >= threshold and current < threshold

    def _check_between(self, value: float, min_val: float, max_val: float) -> bool:
        """Check if a value is between min and max (inclusive)."""
        return min_val <= value <= max_val
