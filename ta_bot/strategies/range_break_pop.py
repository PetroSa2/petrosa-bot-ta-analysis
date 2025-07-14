"""
Range Break Pop Strategy
Detects volatility breakout signals when price breaks above a tight range.
"""

from typing import Dict, Any, Optional
import pandas as pd
from ta_bot.models.signal import Signal, SignalType
from ta_bot.strategies.base_strategy import BaseStrategy
from ta_bot.core.indicators import Indicators


class RangeBreakPopStrategy(BaseStrategy):
    """
    Range Break Pop Strategy

    Trigger: Price breaks above recent tight range (10 candles < 2.5% spread)
    Confirmations:
        - ATR(14) falling
        - RSI ~50
        - Breakout volume > 1.5x average
    """

    def __init__(self):
        """Initialize the strategy."""
        super().__init__()
        self.indicators = Indicators()

    def analyze(self, df: pd.DataFrame, metadata: Dict[str, Any]) -> Optional[Signal]:
        """Analyze for range break pop signals."""
        if len(df) < 12:
            return None

        # Get current values
        current = df.iloc[-1]
        close = current["close"]
        high = current["high"]
        low = current["low"]
        volume = current["volume"]

        # Calculate indicators
        atr = self.indicators.atr(df)
        rsi = self.indicators.rsi(df)

        if atr is None or rsi is None:
            return None

        current_atr = atr.iloc[-1]
        current_rsi = rsi.iloc[-1]
        previous_atr = atr.iloc[-2] if len(atr) > 1 else current_atr

        # Check if we have a tight range in the last 10 candles
        recent_high = df["high"].iloc[-11:-1].max()  # Last 10 candles excluding current
        recent_low = df["low"].iloc[-11:-1].min()
        range_spread = (recent_high - recent_low) / recent_low * 100

        # Range should be tight (< 2.5% spread)
        if range_spread >= 2.5:
            return None

        # Current price should break above the recent high
        breakout_trigger = close > recent_high

        if not breakout_trigger:
            return None

        # Confirmations
        # ATR falling (current ATR < previous ATR)
        atr_falling = current_atr < previous_atr

        # RSI around 50 (between 45-55)
        rsi_ok = 45 <= current_rsi <= 55

        # Breakout volume > 1.5x average
        avg_volume = df["volume"].iloc[-11:-1].mean()  # Average of last 10 candles
        volume_ratio = volume / avg_volume
        volume_ok = volume_ratio > 1.5

        # Check if all confirmations are met
        if not (atr_falling and rsi_ok and volume_ok):
            return None

        return Signal(
            symbol=metadata.get("symbol", "UNKNOWN"),
            period=metadata.get("period", "15m"),
            signal_type=SignalType.BUY,
            strategy="range_break_pop",
            confidence=0.75,
            metadata={
                "rsi": float(current_rsi),
                "atr": float(current_atr),
                "volume_ratio": float(volume_ratio),
                "range_spread": float(range_spread),
                "recent_high": float(recent_high),
                "atr_falling": atr_falling,
                "rsi_neutral": rsi_ok,
                "volume_breakout": volume_ok
            }
        )
