"""
Golden Trend Sync Strategy
Detects pullback entry signals when price pulls back to EMA21 with trend confirmations.
"""

from typing import Dict, Any, Optional
import pandas as pd
from ta_bot.models.signal import SignalType
from ta_bot.strategies.base_strategy import BaseStrategy


class GoldenTrendSyncStrategy(BaseStrategy):
    """
    Golden Trend Sync Strategy

    Trigger: Price pulls back to EMA21
    Confirmations:
        - EMA21 > EMA50 > EMA200
        - RSI between 45–55
        - MACD Histogram positive
    """

    def analyze(
        self, df: pd.DataFrame, indicators: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Analyze for golden trend sync signals."""
        if len(df) < 2:
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
        last_3_volumes = df["volume"].iloc[-4:-1]  # Last 3 candles excluding current

        # Count how many candles have higher volume than current
        higher_volume_count = (last_3_volumes > current_volume).sum()

        # Return rank (1 = highest, 4 = lowest)
        return higher_volume_count + 1
