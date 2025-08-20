"""
Divergence Trap strategy for technical analysis.
"""

from typing import Any, Dict, Optional

import pandas as pd

from ta_bot.core.indicators import Indicators
from ta_bot.models.signal import SignalType
from ta_bot.strategies.base_strategy import BaseStrategy


class DivergenceTrapStrategy(BaseStrategy):
    """Divergence Trap strategy implementation."""

    def __init__(self):
        """Initialize the strategy."""
        super().__init__()
        self.indicators = Indicators()

    def analyze(
        self, df: pd.DataFrame, indicators: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Analyze candles for Divergence Trap signals."""
        if len(df) < 30:
            return None

        # Get current values using base strategy methods
        current_values = self._get_current_values(indicators, df)

        # Check if we have all required indicators
        required_indicators = ["rsi", "close"]
        if not all(indicator in current_values for indicator in required_indicators):
            return None

        close = current_values["close"]
        current_rsi = current_values["rsi"]

        # Get RSI series for divergence analysis
        rsi = indicators.get("rsi", [])
        # Properly check if RSI series is valid
        if (isinstance(rsi, pd.Series) and (rsi.empty or len(rsi) < 10)) or (
            not isinstance(rsi, pd.Series) and (not rsi or len(rsi) < 10)
        ):
            return None

        # Check for hidden bullish divergence
        # Price making lower lows but RSI making higher lows
        if len(df) >= 10:
            # Get recent price lows
            recent_lows = df["low"].iloc[-10:].values

            # Get recent RSI values as a list to avoid Series operations
            if hasattr(rsi, "iloc"):
                recent_rsi_values = rsi.iloc[-10:].tolist()
            else:
                recent_rsi_values = rsi[-10:] if rsi else []

            # Find local minima - use specific indices to avoid Series operations
            if len(recent_rsi_values) >= 10:
                try:
                    price_lower_low = (
                        recent_lows[-1] < recent_lows[-5]
                    )  # Current low < previous low
                    rsi_higher_low = (
                        current_rsi > recent_rsi_values[-5]
                    )  # Current RSI > previous RSI

                    hidden_bullish_divergence = price_lower_low and rsi_higher_low
                except (IndexError, ValueError):
                    hidden_bullish_divergence = False
            else:
                hidden_bullish_divergence = False
        else:
            hidden_bullish_divergence = False

        # Check for oversold conditions
        oversold = current_rsi < 30

        # Check for price momentum
        if len(df) >= 3:
            prev_close = df.iloc[-2]["close"]
            momentum = close > prev_close
        else:
            momentum = False

        if hidden_bullish_divergence and oversold and momentum:
            return {
                "signal_type": SignalType.BUY,
                "metadata": {
                    "rsi": current_rsi,
                    "divergence_type": "hidden_bullish",
                    "oversold": oversold,
                    "momentum": momentum,
                },
            }

        return None

    def _calculate_trend_percent(self, df: pd.DataFrame) -> float:
        """Calculate trend percentage based on price movement."""
        if len(df) < 10:
            return 0.0

        # Calculate simple trend percentage
        start_price = df["close"].iloc[-10]
        end_price = df["close"].iloc[-1]

        trend_percent = ((end_price - start_price) / start_price) * 100
        return trend_percent
