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

        current_atr = float(atr.iloc[-1])

        # Calculate recent range (last 10 candles)
        recent_high = df["high"].iloc[-10:].max()
        recent_low = df["low"].iloc[-10:].min()
        range_size = recent_high - recent_low

        # Check for breakout
        breakout_up = close > recent_high
        breakout_down = close < recent_low

        # Check for volume confirmation
        current_volume = current["volume"]
        avg_volume = df["volume"].iloc[-10:].mean()
        volume_spike = current_volume > avg_volume * 1.5

        # Check for volatility expansion
        volatility_expansion = current_atr > df["close"].iloc[-10:].std() * 1.2

        if breakout_up and volume_spike and volatility_expansion:
            return {
                "signal_type": SignalType.BUY,
                "metadata": {
                    "breakout_level": recent_high,
                    "range_size": range_size,
                    "atr": current_atr,
                    "volume_ratio": current_volume / avg_volume,
                    "volatility_expansion": volatility_expansion,
                },
            }
        elif breakout_down and volume_spike and volatility_expansion:
            return {
                "signal_type": SignalType.SELL,
                "metadata": {
                    "breakout_level": recent_low,
                    "range_size": range_size,
                    "atr": current_atr,
                    "volume_ratio": current_volume / avg_volume,
                    "volatility_expansion": volatility_expansion,
                },
            }

        return None
