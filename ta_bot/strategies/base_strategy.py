"""
Base strategy class for technical analysis strategies.
"""

import pandas as pd
import logging
from typing import Dict, Any, Optional

from ta_bot.models.signal import Signal

logger = logging.getLogger(__name__)


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
            # Handle pandas Series
            if isinstance(indicator_series, pd.Series):
                if not indicator_series.empty and len(indicator_series) > 0:
                    try:
                        current_values[indicator_name] = float(indicator_series.iloc[-1])
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Failed to get current value for {indicator_name}: {e}")
                        continue
            # Handle list type
            elif isinstance(indicator_series, list) and len(indicator_series) > 0:
                try:
                    current_values[indicator_name] = float(indicator_series[-1])
                except (ValueError, IndexError) as e:
                    logger.debug(f"Failed to get current value for {indicator_name}: {e}")
                    continue
            # Handle scalar values
            elif indicator_series is not None:
                try:
                    current_values[indicator_name] = float(indicator_series)
                except (ValueError, TypeError) as e:
                    logger.debug(f"Failed to get current value for {indicator_name}: {e}")
                    continue

        # Add current price data
        if len(df) > 0:
            try:
                current_values["open"] = float(df["open"].iloc[-1])
                current_values["high"] = float(df["high"].iloc[-1])
                current_values["low"] = float(df["low"].iloc[-1])
                current_values["close"] = float(df["close"].iloc[-1])
                current_values["volume"] = float(df["volume"].iloc[-1])
            except (ValueError, IndexError) as e:
                logger.debug(f"Failed to get current price data: {e}")

        return current_values

    def _get_previous_values(
        self, indicators: Dict[str, Any], df: pd.DataFrame
    ) -> Dict[str, float]:
        """Get previous values of indicators for the previous candle."""
        previous_values = {}

        for indicator_name, indicator_series in indicators.items():
            # Handle pandas Series
            if isinstance(indicator_series, pd.Series):
                if not indicator_series.empty and len(indicator_series) > 1:
                    try:
                        previous_values[indicator_name] = float(indicator_series.iloc[-2])
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Failed to get previous value for {indicator_name}: {e}")
                        continue
            # Handle list type
            elif isinstance(indicator_series, list) and len(indicator_series) > 1:
                try:
                    previous_values[indicator_name] = float(indicator_series[-2])
                except (ValueError, IndexError) as e:
                    logger.debug(f"Failed to get previous value for {indicator_name}: {e}")
                    continue
            # Handle scalar values (use same value for previous)
            elif indicator_series is not None:
                try:
                    previous_values[indicator_name] = float(indicator_series)
                except (ValueError, TypeError) as e:
                    logger.debug(f"Failed to get previous value for {indicator_name}: {e}")
                    continue

        # Add previous price data
        if len(df) > 1:
            try:
                previous_values["open"] = float(df["open"].iloc[-2])
                previous_values["high"] = float(df["high"].iloc[-2])
                previous_values["low"] = float(df["low"].iloc[-2])
                previous_values["close"] = float(df["close"].iloc[-2])
                previous_values["volume"] = float(df["volume"].iloc[-2])
            except (ValueError, IndexError) as e:
                logger.debug(f"Failed to get previous price data: {e}")

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
