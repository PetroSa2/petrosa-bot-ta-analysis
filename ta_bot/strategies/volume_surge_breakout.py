"""
Volume Surge Breakout Strategy
Detects unusual volume spikes (3x+ average) combined with price breakouts.
"""

from typing import Any, Dict, Optional

import pandas as pd

from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class VolumeSurgeBreakoutStrategy(BaseStrategy):
    """
    Volume Surge Breakout Strategy

    Trigger: Volume > 3x average + price breakout
    Confirmations:
        - RSI not overbought/oversold (25-75 range)
        - MACD showing momentum alignment
        - Price breaks above/below key resistance/support
    """

    def analyze(
        self,
        df: pd.DataFrame,
        metadata: Dict[str, Any],
    ) -> Optional[Signal]:
        """Analyze for volume surge breakout signals."""
        if len(df) < 25:
            return None

        # Extract indicators from metadata (now passed directly)
        indicators = {
            k: v for k, v in metadata.items() if k not in ["symbol", "timeframe"]
        }
        symbol = metadata.get("symbol", "UNKNOWN")
        timeframe = metadata.get("timeframe", "15m")

        current = self._get_current_values(indicators, df)

        # Check if we have all required indicators
        required_indicators = [
            "volume_sma",
            "rsi",
            "macd",
            "macd_signal",
            "close",
            "volume",
        ]
        if not all(indicator in current for indicator in required_indicators):
            return None

        # Volume surge condition: current volume > 3x average
        volume_surge = current["volume"] > (current["volume_sma"] * 3)
        if not volume_surge:
            return None

        # RSI not overbought/oversold (25-75 range)
        rsi_ok = self._check_between(current["rsi"], 25, 75)
        if not rsi_ok:
            return None

        # MACD momentum alignment
        macd_aligned = current["macd"] > current["macd_signal"]
        if not macd_aligned:
            return None

        # Price breakout detection
        breakout_up = self._detect_breakout_up(df)
        breakout_down = self._detect_breakout_down(df)

        if not breakout_up and not breakout_down:
            return None

        # Determine signal direction
        if breakout_up:
            action = "buy"
            breakout_type = "resistance"
            confidence = 0.75
        else:
            action = "sell"
            breakout_type = "support"
            confidence = 0.75

        # Adjust confidence based on volume strength
        volume_ratio = current["volume"] / current["volume_sma"]
        if volume_ratio > 5:
            confidence += 0.05
        if volume_ratio > 7:
            confidence += 0.05

        # Prepare metadata for signal
        signal_metadata = {
            "volume_ratio": volume_ratio,
            "rsi": current["rsi"],
            "macd": current["macd"],
            "macd_signal": current["macd_signal"],
            "breakout_type": breakout_type,
            "volume_surge": True,
        }

        # Create and return Signal object
        return Signal(
            strategy_id="volume_surge_breakout",
            symbol=symbol,
            action=action,
            confidence=min(confidence, 0.95),  # Cap at 95%
            current_price=current["close"],
            price=current["close"],
            timeframe=timeframe,
            metadata=signal_metadata,
        )

    def _detect_breakout_up(self, df: pd.DataFrame) -> bool:
        """Detect upward breakout above recent resistance."""
        if len(df) < 20:
            return False

        current_close = df["close"].iloc[-1]
        current_high = df["high"].iloc[-1]

        # Look for resistance in the last 20 candles
        recent_highs = df["high"].iloc[-20:-1]
        resistance_level = recent_highs.max()

        # Check if current candle breaks above resistance
        breakout = (
            current_high > resistance_level and current_close > resistance_level * 0.998
        )

        return breakout

    def _detect_breakout_down(self, df: pd.DataFrame) -> bool:
        """Detect downward breakout below recent support."""
        if len(df) < 20:
            return False

        current_close = df["close"].iloc[-1]
        current_low = df["low"].iloc[-1]

        # Look for support in the last 20 candles
        recent_lows = df["low"].iloc[-20:-1]
        support_level = recent_lows.min()

        # Check if current candle breaks below support
        breakout = current_low < support_level and current_close < support_level * 1.002

        return breakout
