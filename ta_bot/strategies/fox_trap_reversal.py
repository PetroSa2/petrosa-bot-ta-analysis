"""
Fox Trap Reversal Strategy
Adapted from Quantzed Screenings 19 & 20: "TRAP RAPOSA" strategies

Detects false breakout patterns where price briefly moves beyond
key levels before reversing, creating high-probability counter-trend opportunities.
"""

from typing import Any, Optional

import pandas as pd

from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class FoxTrapReversalStrategy(BaseStrategy):
    """
    Fox Trap Reversal Strategy

    Bullish Fox Trap (Screening 19):
        - Close > EMA8 > EMA80 (overall uptrend)
        - Low touches EMA8 (pullback test)
        - EMA8 > EMA20 (trend confirmation)
        - Highs above EMA8 in last 2-3 periods (trend strength)

    Bearish Fox Trap (Screening 20):
        - Close < EMA8 < EMA80 (overall downtrend)
        - High touches EMA8 (rally test)
        - EMA8 < EMA80 (trend confirmation)
        - Lows below EMA8 in last 2-3 periods (trend strength)

    The "trap" occurs when price briefly breaks the EMA level but fails
    to sustain, creating a reversal opportunity in the main trend direction.

    Adapted from Quantzed Brazilian market screening strategies.
    """

    def analyze(
        self,
        df: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> Signal | None:
        """Analyze for fox trap reversal signals."""
        if len(df) < 130:  # Need sufficient data for EMA80
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
        if "ema20" not in indicators:
            indicators["ema20"] = (
                df["close"].ewm(span=20, min_periods=19, adjust=True).mean()
            )
        if "ema80" not in indicators:
            indicators["ema80"] = (
                df["close"].ewm(span=80, min_periods=79, adjust=True).mean()
            )

        current = self._get_current_values(indicators, df)

        # Check if we have all required indicators
        required_indicators = ["ema8", "ema20", "ema80", "close", "high", "low"]
        if not all(indicator in current for indicator in required_indicators):
            return None

        # Extract values
        current_close = current["close"]
        current_high = current["high"]
        current_low = current["low"]
        ema8 = current["ema8"]
        ema20 = current["ema20"]
        ema80 = current["ema80"]

        # Check for Bullish Fox Trap (Screening 19)
        bullish_trend_alignment = current_close > ema8 and ema8 > ema80
        bullish_ema_strength = ema8 > ema20
        low_touches_ema8 = current_low <= ema8 * 1.02  # Within 2% of EMA8

        # Check if highs were above EMA8 in recent periods (trend strength)
        if len(df) >= 3:
            highs_last_3 = df["high"].iloc[-3:-1]  # Last 2-3 periods excluding current
            ema8_series = indicators["ema8"]

            if isinstance(ema8_series, pd.Series) and len(ema8_series) >= 3:
                ema8_last_3 = ema8_series.iloc[-3:-1]
                bullish_strength = any(
                    highs_last_3.iloc[i] > ema8_last_3.iloc[i]
                    for i in range(len(highs_last_3))
                )
            else:
                bullish_strength = True
        else:
            bullish_strength = True

        # Additional confirmation: EMA8 above EMA80 for last 6 periods
        if len(df) >= 6:
            ema8_series = indicators["ema8"]
            ema80_series = indicators["ema80"]

            if isinstance(ema8_series, pd.Series) and isinstance(
                ema80_series, pd.Series
            ):
                if len(ema8_series) >= 6 and len(ema80_series) >= 6:
                    ema8_last_6 = ema8_series.iloc[-6:]
                    ema80_last_6 = ema80_series.iloc[-6:]
                    bullish_trend_persistence = all(
                        ema8_last_6.iloc[i] > ema80_last_6.iloc[i] for i in range(6)
                    )
                else:
                    bullish_trend_persistence = ema8 > ema80
            else:
                bullish_trend_persistence = ema8 > ema80
        else:
            bullish_trend_persistence = ema8 > ema80

        bullish_fox_trap = (
            bullish_trend_alignment
            and bullish_ema_strength
            and low_touches_ema8
            and bullish_strength
            and bullish_trend_persistence
        )

        # Check for Bearish Fox Trap (Screening 20)
        bearish_trend_alignment = current_close < ema80 and current_close < ema8
        bearish_ema_weakness = ema8 < ema80
        high_touches_ema8 = current_high >= ema8 * 0.98  # Within 2% of EMA8

        # Check if lows were below EMA8 in recent periods (trend strength)
        if len(df) >= 3:
            lows_last_3 = df["low"].iloc[-3:-1]  # Last 2-3 periods excluding current
            ema8_series = indicators["ema8"]

            if isinstance(ema8_series, pd.Series) and len(ema8_series) >= 3:
                ema8_last_3 = ema8_series.iloc[-3:-1]
                bearish_strength = any(
                    lows_last_3.iloc[i] < ema8_last_3.iloc[i]
                    for i in range(len(lows_last_3))
                )
            else:
                bearish_strength = True
        else:
            bearish_strength = True

        # Additional confirmation: EMA8 below EMA80 for last 6 periods
        if len(df) >= 6:
            ema8_series = indicators["ema8"]
            ema80_series = indicators["ema80"]

            if isinstance(ema8_series, pd.Series) and isinstance(
                ema80_series, pd.Series
            ):
                if len(ema8_series) >= 6 and len(ema80_series) >= 6:
                    ema8_last_6 = ema8_series.iloc[-6:]
                    ema80_last_6 = ema80_series.iloc[-6:]
                    bearish_trend_persistence = all(
                        ema8_last_6.iloc[i] < ema80_last_6.iloc[i] for i in range(6)
                    )
                else:
                    bearish_trend_persistence = ema8 < ema80
            else:
                bearish_trend_persistence = ema8 < ema80
        else:
            bearish_trend_persistence = ema8 < ema80

        bearish_fox_trap = (
            bearish_trend_alignment
            and bearish_ema_weakness
            and high_touches_ema8
            and bearish_strength
            and bearish_trend_persistence
        )

        # Determine signal direction
        if bullish_fox_trap:
            signal_action = "buy"
            entry_price = current_high
            stop_loss = current_low
            trap_type = "bullish_fox_trap"
            screening_origin = "quantzed_screening_19"
            base_confidence = 0.78
        elif bearish_fox_trap:
            signal_action = "sell"
            entry_price = current_low
            stop_loss = current_high
            trap_type = "bearish_fox_trap"
            screening_origin = "quantzed_screening_20"
            base_confidence = 0.78
        else:
            return None

        # Calculate take profit using 2:1 risk-reward ratio
        risk_amount = abs(entry_price - stop_loss)
        if signal_action == "buy":
            take_profit = entry_price + (risk_amount * 2)
        else:
            take_profit = entry_price - (risk_amount * 2)

        # Calculate trap quality metrics
        ema_separation = abs(ema8 - ema80) / ema80 if ema80 > 0 else 0
        ema8_ema20_separation = abs(ema8 - ema20) / ema20 if ema20 > 0 else 0

        # Better trap when EMAs are well separated (stronger trend)
        trend_quality = min(1, ema_separation * 15)
        confirmation_quality = min(1, ema8_ema20_separation * 20)

        # Distance from EMA8 (closer = better trap)
        if signal_action == "buy":
            trap_distance = abs(current_low - ema8) / ema8 if ema8 > 0 else 0
        else:
            trap_distance = abs(current_high - ema8) / ema8 if ema8 > 0 else 0

        trap_quality = max(0, 1 - (trap_distance * 20))  # Prefer closer to EMA

        # Adjust confidence based on quality metrics
        trend_adjustment = trend_quality * 0.08  # Up to 8% boost
        confirmation_adjustment = confirmation_quality * 0.06  # Up to 6% boost
        trap_adjustment = trap_quality * 0.05  # Up to 5% boost

        final_confidence = min(
            0.92,
            base_confidence
            + trend_adjustment
            + confirmation_adjustment
            + trap_adjustment,
        )

        # Prepare metadata for signal
        signal_metadata = {
            "trap_type": trap_type,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": 2.0,
            "ema8": ema8,
            "ema20": ema20,
            "ema80": ema80,
            "ema_separation": ema_separation,
            "ema8_ema20_separation": ema8_ema20_separation,
            "trap_distance": trap_distance,
            "trend_quality": trend_quality,
            "trap_quality": trap_quality,
            "strategy_origin": screening_origin,
        }

        return Signal(
            strategy_id="fox_trap_reversal",
            symbol=symbol,
            action=signal_action,
            confidence=final_confidence,
            current_price=current_close,
            price=entry_price,
            timeframe=timeframe,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=signal_metadata,
        )
