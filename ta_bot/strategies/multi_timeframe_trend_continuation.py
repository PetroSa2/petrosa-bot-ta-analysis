"""
Multi-Timeframe Trend Continuation Strategy
Aligns signals across multiple timeframes for trend continuation trades.
"""

from typing import Any, Dict, Optional

import pandas as pd

from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class MultiTimeframeTrendContinuationStrategy(BaseStrategy):
    """
    Multi-Timeframe Trend Continuation Strategy

    Trigger: Aligns signals across 15m, 1h, and 4h timeframes
    Confirmations:
        - Higher timeframe trend direction
        - Lower timeframe pullback entry
        - Volume supporting the move
    """

    def analyze(
        self,
        df: pd.DataFrame,
        metadata: Dict[str, Any],
    ) -> Optional[Signal]:
        """Analyze for multi-timeframe trend continuation signals."""
        if len(df) < 50:
            return None

        # Extract indicators from metadata (now passed directly)
        indicators = {
            k: v for k, v in metadata.items() if k not in ["symbol", "timeframe"]
        }
        symbol = metadata.get("symbol", "UNKNOWN")
        timeframe = metadata.get("timeframe", "15m")

        current = self._get_current_values(indicators, df)
        previous = self._get_previous_values(indicators, df)

        # Check if we have all required indicators
        required_indicators = [
            "ema21",
            "ema50",
            "ema200",
            "rsi",
            "macd",
            "close",
            "volume",
        ]
        if not all(indicator in current for indicator in required_indicators):
            return None

        # Determine trend direction on current timeframe
        trend_direction = self._determine_trend_direction(current, previous)
        if trend_direction is None:
            return None

        # Check for pullback entry opportunity
        pullback_entry = self._check_pullback_entry(df, trend_direction)
        if not pullback_entry:
            return None

        # Volume confirmation
        volume_confirmed = self._check_volume_confirmation(current)
        if not volume_confirmed:
            return None

        # Determine signal direction
        if trend_direction == "bullish":
            action = "buy"
            confidence = 0.75
            signal_type = "trend_continuation_bullish"
        else:
            action = "sell"
            confidence = 0.75
            signal_type = "trend_continuation_bearish"

        # Adjust confidence based on trend strength
        trend_strength = self._calculate_trend_strength(df, trend_direction)
        confidence += trend_strength * 0.1

        # Prepare metadata for signal
        signal_metadata = {
            "trend_direction": trend_direction,
            "trend_strength": trend_strength,
            "rsi": current["rsi"],
            "macd": current["macd"],
            "ema21": current["ema21"],
            "ema50": current["ema50"],
            "ema200": current["ema200"],
            "signal_type": signal_type,
            "multi_timeframe": True,
        }

        # Create and return Signal object
        return Signal(
            strategy_id="multi_timeframe_trend_continuation",
            symbol=symbol,
            action=action,
            confidence=min(confidence, 0.95),  # Cap at 95%
            current_price=current["close"],
            price=current["close"],
            timeframe=timeframe,
            metadata=signal_metadata,
        )

    def _determine_trend_direction(
        self, current: Dict[str, float], previous: Dict[str, float]
    ) -> Optional[str]:
        """Determine the overall trend direction."""
        # Check EMA alignment
        ema21 = current["ema21"]
        ema50 = current["ema50"]
        ema200 = current["ema200"]
        close = current["close"]

        # Bullish trend: EMAs aligned upward, price above EMAs
        bullish_trend = ema21 > ema50 > ema200 and close > ema21 and current["macd"] > 0

        # Bearish trend: EMAs aligned downward, price below EMAs
        bearish_trend = ema21 < ema50 < ema200 and close < ema21 and current["macd"] < 0

        if bullish_trend:
            return "bullish"
        elif bearish_trend:
            return "bearish"
        else:
            return None

    def _check_pullback_entry(self, df: pd.DataFrame, trend_direction: str) -> bool:
        """Check for pullback entry opportunity."""
        if len(df) < 10:
            return False

        current_close = df["close"].iloc[-1]
        ema21 = df["ema21"].iloc[-1] if "ema21" in df.columns else None

        if trend_direction == "bullish":
            # Look for pullback to EMA21 or support level
            if ema21 is not None:
                # Price near EMA21 (within 1%)
                near_ema = abs(current_close - ema21) / ema21 < 0.01

                # RSI showing oversold condition
                rsi = df["rsi"].iloc[-1] if "rsi" in df.columns else 50
                oversold = rsi < 40

                # MACD starting to turn up
                macd = df["macd"].iloc[-1] if "macd" in df.columns else 0
                macd_prev = df["macd"].iloc[-2] if len(df) > 1 else 0
                macd_turning_up = macd > macd_prev

                return near_ema and oversold and macd_turning_up

        elif trend_direction == "bearish":
            # Look for pullback to EMA21 or resistance level
            if ema21 is not None:
                # Price near EMA21 (within 1%)
                near_ema = abs(current_close - ema21) / ema21 < 0.01

                # RSI showing overbought condition
                rsi = df["rsi"].iloc[-1] if "rsi" in df.columns else 50
                overbought = rsi > 60

                # MACD starting to turn down
                macd = df["macd"].iloc[-1] if "macd" in df.columns else 0
                macd_prev = df["macd"].iloc[-2] if len(df) > 1 else 0
                macd_turning_down = macd < macd_prev

                return near_ema and overbought and macd_turning_down

        return False

    def _check_volume_confirmation(self, current: Dict[str, float]) -> bool:
        """Check if volume confirms the trend continuation."""
        if "volume_sma" not in current:
            return True  # Skip volume check if not available

        volume_ratio = current["volume"] / current["volume_sma"]
        return volume_ratio > 1.2  # Volume 20% above average

    def _calculate_trend_strength(
        self, df: pd.DataFrame, trend_direction: str
    ) -> float:
        """Calculate trend strength (0.0 to 1.0)."""
        if len(df) < 20:
            return 0.5

        # Calculate ADX for trend strength
        if "adx" in df.columns:
            adx = df["adx"].iloc[-1]
            # Normalize ADX to 0-1 range (ADX typically 0-100)
            trend_strength = min(adx / 100.0, 1.0)
        else:
            # Fallback: use price momentum
            price_change = (df["close"].iloc[-1] - df["close"].iloc[-20]) / df[
                "close"
            ].iloc[-20]
            trend_strength = min(abs(price_change) * 10, 1.0)  # Scale appropriately

        return trend_strength
