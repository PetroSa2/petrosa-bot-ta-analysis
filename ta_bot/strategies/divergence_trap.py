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

    def analyze(self, df: pd.DataFrame, metadata: Dict[str, Any]) -> Optional[Signal]:
        """Analyze candles for Divergence Trap signals."""
        if len(df) < 20:
            return None

        # Get current and previous values
        current = df.iloc[-1]
        previous = df.iloc[-2]

        # Calculate RSI
        rsi = self.indicators.rsi(df)
        if rsi is None:
            return None

        current_rsi = rsi.iloc[-1]
        previous_rsi = rsi.iloc[-2]

        # Get price lows
        current_low = current["low"]
        previous_low = previous["low"]

        # Check for hidden bullish divergence
        # Price makes lower low, but RSI makes higher low
        price_lower_low = current_low < previous_low
        rsi_higher_low = current_rsi > previous_rsi

        if price_lower_low and rsi_higher_low:
            # Calculate divergence strength
            rsi_change = (current_rsi - previous_rsi) / previous_rsi

            # Strong divergence if RSI change is significant
            strong_divergence = abs(rsi_change) > 0.1  # 10% RSI change

            if strong_divergence:
                return Signal(
                    symbol=metadata.get("symbol", "UNKNOWN"),
                    period=metadata.get("period", "15m"),
                    signal=SignalType.BUY,
                    strategy="divergence_trap",
                    confidence=0.78,
                    metadata={
                        "rsi_current": current_rsi,
                        "rsi_previous": previous_rsi,
                        "divergence_strength": abs(rsi_change),
                        "price_change": price_change
                    }
                )

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
