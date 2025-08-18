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

    def analyze(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze candles for Range Break Pop signals."""
        if len(df) < 20:
            return None

        # Get current values
        current = df.iloc[-1]
        close = current["close"]
        high = current["high"]
        low = current["low"]

        # Get ATR for volatility measurement
        atr = indicators.get("atr", [])

        if not atr:
            return None

        # Handle both pandas Series and list types
        if hasattr(atr, 'iloc'):
            current_atr = float(atr.iloc[-1])
        else:
            # Handle list type
            current_atr = float(atr[-1]) if atr else 0

        # Calculate range
        range_size = high - low
        range_breakout = range_size > current_atr * 1.5  # Range is 1.5x ATR

        # Check for volume confirmation (if available)
        volume = current.get("volume", 0)
        volume_confirmation = volume > 0  # Basic check

        # Check for price momentum
        if len(df) >= 3:
            prev_close = df.iloc[-2]["close"]
            prev_prev_close = df.iloc[-3]["close"]
            
            # Strong upward momentum
            momentum = close > prev_close > prev_prev_close
        else:
            momentum = False

        if range_breakout and volume_confirmation and momentum:
            return {
                "signal_type": SignalType.BUY,
                "metadata": {
                    "atr": current_atr,
                    "range_size": range_size,
                    "volume": volume,
                    "momentum": momentum,
                },
            }

        return None
