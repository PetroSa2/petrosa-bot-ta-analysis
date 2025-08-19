"""
Golden Trend Sync strategy for technical analysis.
"""

import pandas as pd
from typing import Dict, Any, Optional

from ta_bot.strategies.base_strategy import BaseStrategy
from ta_bot.core.indicators import Indicators
from ta_bot.models.signal import Signal, SignalType


class GoldenTrendSyncStrategy(BaseStrategy):
    """Golden Trend Sync strategy implementation."""

    def __init__(self):
        """Initialize the strategy."""
        super().__init__()
        self.indicators = Indicators()

    def analyze(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze candles for Golden Trend Sync signals."""
        if len(df) < 50:
            return None

        # Get current values
        current = df.iloc[-1]
        close = current["close"]

        # Get EMAs
        ema21 = indicators.get("ema21", [])
        ema50 = indicators.get("ema50", [])

        # Check if indicators are available and not empty
        if (not ema21 or (hasattr(ema21, 'empty') and ema21.empty)) or \
           (not ema50 or (hasattr(ema50, 'empty') and ema50.empty)):
            return None

        # Handle both pandas Series and list types
        if hasattr(ema21, 'iloc'):
            current_ema21 = float(ema21.iloc[-1])
            current_ema50 = float(ema50.iloc[-1])
        else:
            # Handle list type
            current_ema21 = float(ema21[-1]) if ema21 else 0
            current_ema50 = float(ema50[-1]) if ema50 else 0

        # Check for golden cross (EMA21 > EMA50)
        golden_cross = current_ema21 > current_ema50

        # Check for pullback to EMA21 (price near EMA21)
        pullback_distance = abs(close - current_ema21) / current_ema21
        pullback_to_ema21 = pullback_distance <= 0.02  # Within 2%

        # Check for bullish candle (close > open)
        bullish_candle = close > current["open"]

        if golden_cross and pullback_to_ema21 and bullish_candle:
            return {
                "signal_type": SignalType.BUY,
                "metadata": {
                    "ema21": current_ema21,
                    "ema50": current_ema50,
                    "pullback_distance": abs(close - current_ema21) / current_ema21,
                },
            }

        return None

    def _calculate_volume_rank(self, df: pd.DataFrame) -> int:
        """Calculate volume rank of current candle compared to last 3 candles."""
        if len(df) < 4:
            return 0

        current_volume = df["volume"].iloc[-1]
        recent_volumes = df["volume"].iloc[-4:-1]

        # Count how many recent candles have higher volume
        higher_volume_count = sum(1 for vol in recent_volumes if vol > current_volume)

        return higher_volume_count
