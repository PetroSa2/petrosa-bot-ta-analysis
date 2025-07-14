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

    def analyze(self, df: pd.DataFrame, metadata: Dict[str, Any]) -> Optional[Signal]:
        """Analyze candles for Band Fade Reversal signals."""
        if len(df) < 20:
            return None

        # Get latest candle
        current = df.iloc[-1]
        high = current["high"]
        low = current["low"]
        close = current["close"]

        # Calculate Bollinger Bands
        bb_upper, bb_middle, bb_lower = self.indicators.bollinger_bands(df)

        if bb_upper is None or bb_middle is None or bb_lower is None:
            return None

        # Check if price is near upper band
        upper_band = bb_upper.iloc[-1]
        middle_band = bb_middle.iloc[-1]

        # Signal conditions
        near_upper = close >= upper_band * 0.98  # Within 2% of upper band
        bearish_candle = close < (high + low) / 2  # Close below midpoint
        volume_spike = metadata.get("volume_ratio", 0) > 1.5

        if near_upper and bearish_candle and volume_spike:
            return Signal(
                symbol=metadata.get("symbol", "UNKNOWN"),
                period=metadata.get("period", "15m"),
                signal_type=SignalType.SELL,
                strategy="band_fade_reversal",
                confidence=0.65,
                metadata={
                    "bb_upper": upper_band,
                    "bb_middle": middle_band,
                    "close": close,
                    "volume_ratio": metadata.get("volume_ratio", 0),
                },
            )

        return None
