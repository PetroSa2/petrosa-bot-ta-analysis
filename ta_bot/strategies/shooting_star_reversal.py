"""
Shooting Star Reversal Strategy

Adapted from Quantzed's screening_26 'ESTRELA CADENTE (TSS)'.

This strategy identifies bearish reversal opportunities when:
1. A shooting star candlestick pattern forms
2. Long upper shadow (at least 2.5x the body size)
3. Small or no lower shadow (max 1/5 of body size)
4. Indicates rejection at higher levels and potential reversal

The shooting star is a bearish reversal pattern that appears after an uptrend,
showing that buyers pushed price higher but sellers ultimately took control.
"""

from typing import Optional

import pandas as pd

from ta_bot.models.signal import Signal, SignalStrength, SignalType
from ta_bot.strategies.base_strategy import BaseStrategy


class ShootingStarReversalStrategy(BaseStrategy):
    """
    Shooting Star Reversal Strategy

    Identifies bearish reversal opportunities when a shooting star
    candlestick pattern forms, indicating rejection at higher levels.
    """

    def __init__(self):
        super().__init__()
        self.name = "Shooting Star Reversal"
        self.description = (
            "Identifies bearish reversals using shooting star candlestick patterns"
        )
        self.min_periods = 10  # Minimal data needed for candlestick analysis

    def analyze(self, data: pd.DataFrame) -> Optional[Signal]:
        """
        Analyze market data for shooting star reversal opportunities.

        Args:
            data: OHLCV DataFrame with datetime index

        Returns:
            Signal object if conditions are met, None otherwise
        """
        if len(data) < self.min_periods:
            return None

        try:
            # Current candle data
            current_open = float(data["open"].iloc[-1])
            current_close = float(data["close"].iloc[-1])
            current_high = float(data["high"].iloc[-1])
            current_low = float(data["low"].iloc[-1])

            # Calculate candle components
            body_size = abs(current_close - current_open)
            upper_shadow = current_high - max(current_close, current_open)
            lower_shadow = min(current_close, current_open) - current_low

            # Avoid division by zero for very small bodies
            if body_size < 0.0001:
                return None

            # Shooting star conditions:
            # 1. Upper shadow >= 2.5 * body size (long upper shadow)
            # 2. Lower shadow <= body size / 5 (small or no lower shadow)
            long_upper_shadow = upper_shadow >= (body_size * 2.5)
            small_lower_shadow = lower_shadow <= (body_size / 5)

            if long_upper_shadow and small_lower_shadow:
                # Risk management
                entry_price = current_low  # Enter at the low of the shooting star
                stop_loss = current_high  # Stop above the high (rejection level)
                risk_amount = stop_loss - entry_price
                take_profit = entry_price - (risk_amount * 1.5)  # 1:1.5 risk/reward

                # Calculate confidence based on pattern strength
                shadow_ratio = upper_shadow / body_size
                pattern_strength = min(1.0, shadow_ratio / 5.0)  # Normalize to max 1.0
                confidence = min(0.75, 0.50 + (pattern_strength * 0.25))

                # Check for trend context (optional enhancement)
                trend_strength = 0.0
                if len(data) >= 20:
                    sma20 = data["close"].rolling(20).mean()
                    if not sma20.empty and current_close > sma20.iloc[-1]:
                        trend_strength = 0.1  # Bonus confidence if in uptrend

                final_confidence = min(0.80, confidence + trend_strength)

                return Signal(
                    symbol=data.attrs.get("symbol", "UNKNOWN"),
                    strategy=self.name,
                    signal_type=SignalType.SELL,
                    strength=SignalStrength.MEDIUM,
                    confidence=final_confidence,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timestamp=data.index[-1],
                    metadata={
                        "body_size": body_size,
                        "upper_shadow": upper_shadow,
                        "lower_shadow": lower_shadow,
                        "shadow_ratio": shadow_ratio,
                        "pattern_strength": pattern_strength,
                        "risk_reward_ratio": 1.5,
                        "pattern": "shooting_star_bearish_reversal",
                    },
                )

        except Exception as e:
            self.logger.error(f"Error in {self.name} analysis: {e}")
            return None

        return None
