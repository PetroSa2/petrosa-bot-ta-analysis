"""
EMA Alignment Bullish Strategy
Adapted from Quantzed Screening 01: "ALINHAMENTO DE MÉDIAS (ALTA)"

Detects bullish trend alignment when multiple EMAs are properly aligned
with positive momentum confirmation.
"""

from typing import Any, Optional

import pandas as pd

from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class EMAAlignmentBullishStrategy(BaseStrategy):
    """
    EMA Alignment Bullish Strategy

    Trigger: Price above aligned EMAs with positive momentum
    Confirmations:
        - Close > EMA8 > EMA80
        - Both EMAs showing positive inclination (last 2 periods)
        - Price maintains above both EMAs

    Adapted from Quantzed Brazilian market screening strategy.
    """

    def analyze(
        self,
        df: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> Signal | None:
        """Analyze for EMA alignment bullish signals."""
        if len(df) < 125:  # Need sufficient data for EMA80
            return None

        # Extract indicators from metadata
        indicators = {
            k: v for k, v in metadata.items() if k not in ["symbol", "timeframe"]
        }
        symbol = metadata.get("symbol", "UNKNOWN")
        timeframe = metadata.get("timeframe", "15m")

        # Calculate EMAs if not provided
        if "ema8" not in indicators:
            indicators["ema8"] = (
                df["close"].ewm(span=8, min_periods=7, adjust=True).mean()
            )
        if "ema80" not in indicators:
            indicators["ema80"] = (
                df["close"].ewm(span=80, min_periods=79, adjust=True).mean()
            )

        current = self._get_current_values(indicators, df)
        previous = self._get_previous_values(indicators, df)

        # Check if we have all required indicators
        required_indicators = ["ema8", "ema80", "close"]
        if not all(indicator in current for indicator in required_indicators):
            return None

        # Core conditions from Quantzed logic
        close = current["close"]
        ema8 = current["ema8"]
        ema80 = current["ema80"]

        # Condition 1: Price above both EMAs
        price_above_emas = close > ema8 and close > ema80

        # Condition 2: EMA8 above EMA80 (proper alignment)
        ema_alignment = ema8 > ema80

        # Condition 3: Positive inclination for both EMAs (last 2 periods)
        ema8_momentum = current["ema8"] > previous.get("ema8", current["ema8"])
        ema80_momentum = current["ema80"] > previous.get("ema80", current["ema80"])

        # Additional momentum confirmation - check previous period too
        if len(df) >= 3:
            # Get EMA values from 2 periods ago for stronger momentum confirmation
            ema8_series = indicators["ema8"]
            ema80_series = indicators["ema80"]

            if isinstance(ema8_series, pd.Series) and len(ema8_series) >= 2:
                ema8_prev2 = (
                    float(ema8_series.iloc[-3])
                    if len(ema8_series) >= 3
                    else previous.get("ema8", current["ema8"])
                )
                ema80_prev2 = (
                    float(ema80_series.iloc[-3])
                    if len(ema80_series) >= 3
                    else previous.get("ema80", current["ema80"])
                )

                # Stronger momentum: both periods showing positive inclination
                ema8_strong_momentum = (
                    previous.get("ema8", current["ema8"]) > ema8_prev2
                ) and ema8_momentum
                ema80_strong_momentum = (
                    previous.get("ema80", current["ema80"]) > ema80_prev2
                ) and ema80_momentum
            else:
                ema8_strong_momentum = ema8_momentum
                ema80_strong_momentum = ema80_momentum
        else:
            ema8_strong_momentum = ema8_momentum
            ema80_strong_momentum = ema80_momentum

        # All conditions must be met (from Quantzed logic)
        all_conditions_met = (
            price_above_emas
            and ema_alignment
            and ema8_strong_momentum
            and ema80_strong_momentum
        )

        if not all_conditions_met:
            return None

        # Calculate trend strength for confidence adjustment
        trend_strength = (ema8 - ema80) / ema80 if ema80 > 0 else 0
        price_distance_from_ema8 = (close - ema8) / ema8 if ema8 > 0 else 0

        # Base confidence from Quantzed analysis, adjusted by trend strength
        base_confidence = 0.74
        strength_adjustment = min(0.1, trend_strength * 10)  # Cap at 0.1
        distance_adjustment = min(0.05, price_distance_from_ema8 * 20)  # Cap at 0.05

        final_confidence = min(
            0.95, base_confidence + strength_adjustment + distance_adjustment
        )

        # Calculate stop loss and take profit (trend following strategy)
        # Stop loss at EMA80 (key support in uptrend)
        stop_loss = ema80
        risk = abs(close - stop_loss)
        take_profit = close + (risk * 2.5)  # 2.5:1 R:R for strong trend alignment

        # Prepare metadata for signal
        signal_metadata = {
            "ema8": ema8,
            "ema80": ema80,
            "trend_strength": trend_strength,
            "price_distance_from_ema8": price_distance_from_ema8,
            "ema8_momentum": ema8_momentum,
            "ema80_momentum": ema80_momentum,
            "strategy_origin": "quantzed_screening_01",
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": 2.5,
        }

        # Create and return Signal object
        return Signal(
            strategy_id="ema_alignment_bullish",
            symbol=symbol,
            action="buy",
            confidence=final_confidence,
            current_price=close,
            price=close,
            timeframe=timeframe,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=signal_metadata,
        )
