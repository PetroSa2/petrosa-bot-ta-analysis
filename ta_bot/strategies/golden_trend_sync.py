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

    def analyze(self, df: pd.DataFrame, metadata: Dict[str, Any]) -> Optional[Signal]:
        """Analyze candles for Golden Trend Sync signals."""
        if len(df) < 20:
            return None

        # Get current values
        current = df.iloc[-1]
        close = current["close"]
        high = current["high"]
        low = current["low"]

        # Calculate EMAs
        ema21 = self.indicators.ema(df, 21)
        ema50 = self.indicators.ema(df, 50)

        if ema21 is None or ema50 is None:
            return None

        current_ema21 = ema21.iloc[-1]
        current_ema50 = ema50.iloc[-1]

        # Check for golden cross (EMA21 > EMA50)
        golden_cross = current_ema21 > current_ema50

        # Check for pullback to EMA21
        pullback_to_ema21 = abs(close - current_ema21) / current_ema21 < 0.02

        # Check for bullish candle
        bullish_candle = close > (high + low) / 2

        if golden_cross and pullback_to_ema21 and bullish_candle:
            return Signal(
                symbol=metadata.get("symbol", "UNKNOWN"),
                period=metadata.get("period", "15m"),
                signal_type=SignalType.BUY,
                strategy="golden_trend_sync",
                confidence=0.7,
                metadata={
                    "ema21": current_ema21,
                    "ema50": current_ema50,
                    "close": close,
                    "pullback_percent": abs(close - current_ema21)
                    / current_ema21
                    * 100,
                },
            )

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
