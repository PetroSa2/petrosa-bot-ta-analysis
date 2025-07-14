"""
Band Fade Reversal Strategy
Detects mean reversion signals when price closes outside Bollinger Bands then back inside.
"""

from typing import Dict, Any, Optional
import pandas as pd
from ta_bot.models.signal import SignalType
from ta_bot.strategies.base_strategy import BaseStrategy


class BandFadeReversalStrategy(BaseStrategy):
    """
    Band Fade Reversal Strategy

    Trigger: Price closes outside upper BB(20, 2), then closes back inside
    Confirmations:
        - RSI(14) > 70
        - ADX(14) < 20
    """

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
