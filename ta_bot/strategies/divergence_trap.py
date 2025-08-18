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
        if len(df) < 20:
            return None

        # Get current values
        current = df.iloc[-1]
        close = current["close"]

        # Get RSI for divergence detection
        rsi = indicators.get("rsi", [])
        if not rsi:
            return None

        current_rsi = float(rsi.iloc[-1])

        # Check for hidden bullish divergence
        # Price makes lower low, but RSI makes higher low
        if len(df) >= 10:
            # Find recent lows
            recent_lows = self._find_recent_lows(df, 10)
            recent_rsi_lows = self._find_recent_lows(rsi, 10)

            if len(recent_lows) >= 2 and len(recent_rsi_lows) >= 2:
                # Check for hidden bullish divergence
                price_lower_low = recent_lows[-1] < recent_lows[-2]
                rsi_higher_low = recent_rsi_lows[-1] > recent_rsi_lows[-2]

                if price_lower_low and rsi_higher_low:
                    # Additional confirmation: RSI should be above 30
                    rsi_oversold = current_rsi > 30

                    if rsi_oversold:
                        return {
                            "signal_type": SignalType.BUY,
                            "metadata": {
                                "rsi": current_rsi,
                                "price_lower_low": price_lower_low,
                                "rsi_higher_low": rsi_higher_low,
                                "divergence_type": "hidden_bullish",
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
