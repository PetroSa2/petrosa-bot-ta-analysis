"""
Hammer Reversal Pattern Strategy
Adapted from Quantzed Screening 25: "MARTELO (TSI)"

Detects hammer candlestick patterns that indicate potential
bullish reversal after downward price movement.
"""

from typing import Any, Optional

import pandas as pd

from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class HammerReversalPatternStrategy(BaseStrategy):
    """
    Hammer Reversal Pattern Strategy

    Trigger: Classic hammer candlestick pattern
    Conditions:
        - Lower shadow >= 2.5 * body size (long lower wick)
        - Upper shadow <= body size / 5 (small upper wick)
        - Indicates rejection of lower prices

    The hammer pattern suggests that sellers pushed price down
    but buyers stepped in strongly, creating a potential reversal.

    Adapted from Quantzed Brazilian market screening strategy.
    """

    def analyze(
        self,
        df: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> Signal | None:
        """Analyze for hammer reversal pattern signals."""
        if len(df) < 10:  # Need minimal data for pattern recognition
            return None

        # Extract metadata
        symbol = metadata.get("symbol", "UNKNOWN")
        timeframe = metadata.get("timeframe", "15m")

        # Get current candle data
        current_open = float(df["open"].iloc[-1])
        current_high = float(df["high"].iloc[-1])
        current_low = float(df["low"].iloc[-1])
        current_close = float(df["close"].iloc[-1])

        # Calculate candle components
        body_size = abs(current_close - current_open)
        total_range = current_high - current_low

        # Calculate shadows
        lower_shadow = min(current_close, current_open) - current_low
        upper_shadow = current_high - max(current_close, current_open)

        # Avoid division by zero
        if body_size == 0 or total_range == 0:
            return None

        # Quantzed hammer conditions
        # Condition 1: Lower shadow >= 2.5 * body size
        long_lower_wick = lower_shadow >= (body_size * 2.5)

        # Condition 2: Upper shadow <= body size / 5
        small_upper_wick = upper_shadow <= (body_size / 5)

        # Both conditions must be met for hammer pattern
        is_hammer = long_lower_wick and small_upper_wick

        if not is_hammer:
            return None

        # Additional quality checks
        # Better hammer if it occurs after a downtrend
        downtrend_context = False
        if len(df) >= 5:
            # Check if recent candles show downward movement
            recent_closes = df["close"].iloc[-5:-1]  # Last 4 closes before current

            # Simple downtrend check: current close lower than most recent closes
            lower_closes_count = sum(
                1 for close in recent_closes if current_close < close
            )
            downtrend_context = (
                lower_closes_count >= 2
            )  # At least half showing downtrend

        # Calculate pattern quality metrics
        wick_to_body_ratio = lower_shadow / body_size if body_size > 0 else 0
        wick_dominance = lower_shadow / total_range if total_range > 0 else 0
        upper_wick_ratio = upper_shadow / body_size if body_size > 0 else 0

        # Quality scoring
        # Better hammer has:
        # - Longer lower wick relative to body (higher ratio)
        # - Lower wick dominates the candle
        # - Very small upper wick
        wick_quality = min(1, wick_to_body_ratio / 5)  # Normalize around 5x ratio
        dominance_quality = wick_dominance  # Already 0-1 range
        upper_wick_quality = max(
            0, 1 - (upper_wick_ratio * 5)
        )  # Penalize large upper wicks

        # Base confidence with quality adjustments
        base_confidence = 0.68

        # Context bonus for downtrend
        context_bonus = 0.08 if downtrend_context else 0

        # Quality adjustments
        wick_adjustment = wick_quality * 0.10  # Up to 10% boost
        dominance_adjustment = dominance_quality * 0.08  # Up to 8% boost
        upper_wick_adjustment = upper_wick_quality * 0.06  # Up to 6% boost

        final_confidence = min(
            0.88,
            base_confidence
            + context_bonus
            + wick_adjustment
            + dominance_adjustment
            + upper_wick_adjustment,
        )

        # Risk management
        # Entry: Above hammer high (breakout confirmation)
        # Stop: Below hammer low (invalidation)
        # Target: 2:1 risk-reward ratio
        entry_price = current_high
        stop_loss = current_low
        risk_amount = entry_price - stop_loss
        take_profit = entry_price + (risk_amount * 2)

        # Prepare metadata for signal
        signal_metadata = {
            "pattern_type": "hammer",
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": 2.0,
            "candle_open": current_open,
            "candle_high": current_high,
            "candle_low": current_low,
            "candle_close": current_close,
            "body_size": body_size,
            "lower_shadow": lower_shadow,
            "upper_shadow": upper_shadow,
            "total_range": total_range,
            "wick_to_body_ratio": wick_to_body_ratio,
            "wick_dominance": wick_dominance,
            "upper_wick_ratio": upper_wick_ratio,
            "downtrend_context": downtrend_context,
            "pattern_quality": (wick_quality + dominance_quality + upper_wick_quality)
            / 3,
            "strategy_origin": "quantzed_screening_25",
        }

        return Signal(
            strategy_id="hammer_reversal_pattern",
            symbol=symbol,
            action="buy",  # Hammer is a bullish reversal pattern
            confidence=final_confidence,
            current_price=current_close,
            price=entry_price,
            timeframe=timeframe,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=signal_metadata,
        )
