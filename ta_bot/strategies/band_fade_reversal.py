"""
Band Fade Reversal strategy for technical analysis.
"""

import pandas as pd
from typing import Dict, Any, Optional

from ta_bot.strategies.base_strategy import BaseStrategy
from ta_bot.core.indicators import Indicators
from ta_bot.models.signal import Signal, SignalType


class BandFadeReversalStrategy(BaseStrategy):
    """Band Fade Reversal strategy implementation."""

    def __init__(self):
        """Initialize the strategy."""
        super().__init__()
        self.indicators = Indicators()

    def analyze(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze candles for Band Fade Reversal signals."""
        if len(df) < 20:
            return None

        # Get current values
        current = df.iloc[-1]
        close = current["close"]

        # Get Bollinger Bands
        bb_lower = indicators.get("bb_lower", [])
        bb_upper = indicators.get("bb_upper", [])
        bb_middle = indicators.get("bb_middle", [])

        if not all([bb_lower, bb_upper, bb_middle]):
            return None

        current_bb_lower = float(bb_lower.iloc[-1])
        current_bb_upper = float(bb_upper.iloc[-1])
        current_bb_middle = float(bb_middle.iloc[-1])

        # Check if price is near the lower band
        near_lower_band = close <= current_bb_lower * 1.01

        # Check if price is below the middle band
        below_middle = close < current_bb_middle

        # Check for reversal pattern (price was lower but now moving up)
        if len(df) >= 3:
            prev_close = df.iloc[-2]["close"]
            prev_prev_close = df.iloc[-3]["close"]
            
            # Price was declining but now showing signs of reversal
            was_declining = prev_close < prev_prev_close
            now_reversing = close > prev_close
            
            reversal_pattern = was_declining and now_reversing
        else:
            reversal_pattern = False

        if near_lower_band and below_middle and reversal_pattern:
            return {
                "signal_type": SignalType.BUY,
                "metadata": {
                    "bb_lower": current_bb_lower,
                    "bb_middle": current_bb_middle,
                    "bb_upper": current_bb_upper,
                    "distance_from_lower": (close - current_bb_lower) / current_bb_lower,
                },
            }

        return None
