"""
Divergence Trap strategy for technical analysis.
"""

import pandas as pd
from typing import Dict, Any, Optional

from ta_bot.strategies.base_strategy import BaseStrategy
from ta_bot.core.indicators import Indicators
from ta_bot.models.signal import Signal, SignalType


class DivergenceTrapStrategy(BaseStrategy):
    """Divergence Trap strategy implementation."""

    def __init__(self):
        """Initialize the strategy."""
        super().__init__()
        self.indicators = Indicators()

    def analyze(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze candles for Divergence Trap signals."""
        if len(df) < 30:
            return None

        # Get current values
        current = df.iloc[-1]
        close = current["close"]

        # Get RSI
        rsi = indicators.get("rsi", [])

        if not rsi:
            return None

        # Handle both pandas Series and list types
        if hasattr(rsi, 'iloc'):
            current_rsi = float(rsi.iloc[-1])
        else:
            # Handle list type
            current_rsi = float(rsi[-1]) if rsi else 50

        # Check for hidden bullish divergence
        # Price making lower lows but RSI making higher lows
        if len(df) >= 10:
            # Get recent price lows
            recent_lows = df["low"].iloc[-10:].values
            recent_rsi = rsi.iloc[-10:].values if hasattr(rsi, 'iloc') else rsi[-10:]
            
            # Find local minima
            price_lower_low = recent_lows[-1] < recent_lows[-5]  # Current low < previous low
            rsi_higher_low = current_rsi > recent_rsi[-5]  # Current RSI > previous RSI
            
            hidden_bullish_divergence = price_lower_low and rsi_higher_low
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
