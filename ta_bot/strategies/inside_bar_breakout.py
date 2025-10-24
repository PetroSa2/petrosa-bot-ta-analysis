"""
Inside Bar Breakout Strategy
Adapted from Quantzed Screening 10: "INSIDE BAR COMPRA"

Detects inside bar consolidation patterns with trend alignment
for high-probability breakout opportunities.
"""

from typing import Any, Dict, Optional

import pandas as pd

from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class InsideBarBreakoutStrategy(BaseStrategy):
    """
    Inside Bar Breakout Strategy

    Trigger: Inside bar pattern with EMA trend alignment
    Conditions:
        - Current high < previous high AND current low > previous low (inside bar)
        - Close > EMA8 > EMA80 (bullish trend alignment)
        - Price above EMAs for last 4 periods (trend strength)
        - Both EMAs showing positive momentum

    Risk Management:
        - Entry: Break above inside bar high
        - Stop: Inside bar low
        - Target: 2:1 risk-reward ratio

    Adapted from Quantzed Brazilian market screening strategy.
    """

    def analyze(
        self,
        df: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> Optional[Signal]:
        """Analyze for inside bar breakout signals."""
        if len(df) < 130:  # Need sufficient data for EMA80 + pattern confirmation
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

        # Check if we have all required indicators and price data
        required_indicators = ["ema8", "ema80", "close", "high", "low"]
        if not all(indicator in current for indicator in required_indicators):
            return None

        # Need at least 2 candles for inside bar pattern
        if len(df) < 2:
            return None

        # Extract current and previous candle data
        current_high = current["high"]
        current_low = current["low"]
        current_close = current["close"]

        previous_high = float(df["high"].iloc[-2])
        previous_low = float(df["low"].iloc[-2])

        # Quantzed Inside Bar Logic: Current candle inside previous candle
        inside_bar_pattern = (current_high < previous_high) and (
            current_low > previous_low
        )

        if not inside_bar_pattern:
            return None

        # EMA trend alignment conditions from Quantzed
        ema8 = current["ema8"]
        ema80 = current["ema80"]

        # Condition 1: Close > EMA8 > EMA80
        bullish_alignment = current_close > ema8 and ema8 > ema80

        if not bullish_alignment:
            return None

        # Condition 2: Price above EMAs for last 4 periods (trend strength)
        if len(df) >= 4:
            closes_series = df["close"].iloc[-4:]
            ema8_series = indicators["ema8"]

            if isinstance(ema8_series, pd.Series) and len(ema8_series) >= 4:
                ema8_last_4 = ema8_series.iloc[-4:]
                trend_strength = all(
                    closes_series.iloc[i] > ema8_last_4.iloc[i] for i in range(4)
                )
            else:
                trend_strength = True  # Fallback if insufficient data
        else:
            trend_strength = True

        # Condition 3: EMA momentum (both EMAs rising)
        previous = self._get_previous_values(indicators, df)
        ema8_momentum = ema8 > previous.get("ema8", ema8)
        ema80_momentum = ema80 > previous.get("ema80", ema80)

        # Additional momentum confirmation from 2 periods ago
        ema8_strong_momentum = ema8_momentum
        ema80_strong_momentum = ema80_momentum

        if len(df) >= 3:
            ema8_series = indicators["ema8"]
            ema80_series = indicators["ema80"]

            if isinstance(ema8_series, pd.Series) and len(ema8_series) >= 3:
                ema8_prev2 = float(ema8_series.iloc[-3])
                ema8_prev1 = previous.get("ema8", ema8)
                ema8_strong_momentum = (ema8_prev1 > ema8_prev2) and ema8_momentum

            if isinstance(ema80_series, pd.Series) and len(ema80_series) >= 3:
                ema80_prev2 = float(ema80_series.iloc[-3])
                ema80_prev1 = previous.get("ema80", ema80)
                ema80_strong_momentum = (ema80_prev1 > ema80_prev2) and ema80_momentum

        # All Quantzed conditions must be met
        all_conditions_met = (
            inside_bar_pattern
            and bullish_alignment
            and trend_strength
            and ema8_strong_momentum
            and ema80_strong_momentum
        )

        if not all_conditions_met:
            return None

        # Calculate risk management levels (Quantzed approach)
        entry_price = current_high  # Break above inside bar high
        stop_loss = current_low  # Inside bar low

        # 2:1 risk-reward ratio as per Quantzed
        risk_amount = entry_price - stop_loss
        take_profit = entry_price + (risk_amount * 2)

        # Calculate pattern quality metrics for confidence
        inside_bar_size = (
            (current_high - current_low) / current_close if current_close > 0 else 0
        )
        previous_bar_size = (
            (previous_high - previous_low) / current_close if current_close > 0 else 0
        )

        # Smaller inside bar relative to previous = higher quality
        pattern_quality = (
            1 - (inside_bar_size / previous_bar_size) if previous_bar_size > 0 else 0.5
        )
        pattern_quality = max(0, min(1, pattern_quality))

        # Trend strength factor
        trend_factor = (ema8 - ema80) / ema80 if ema80 > 0 else 0

        # Base confidence with adjustments
        base_confidence = 0.76  # From Quantzed analysis
        pattern_adjustment = pattern_quality * 0.1  # Up to 10% boost
        trend_adjustment = min(0.08, trend_factor * 5)  # Up to 8% boost

        final_confidence = min(
            0.92, base_confidence + pattern_adjustment + trend_adjustment
        )

        # Prepare metadata for signal
        signal_metadata = {
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": 2.0,
            "inside_bar_high": current_high,
            "inside_bar_low": current_low,
            "previous_high": previous_high,
            "previous_low": previous_low,
            "pattern_quality": pattern_quality,
            "ema8": ema8,
            "ema80": ema80,
            "trend_strength": trend_strength,
            "strategy_origin": "quantzed_screening_10",
        }

        return Signal(
            strategy_id="inside_bar_breakout",
            symbol=symbol,
            action="buy",
            confidence=final_confidence,
            current_price=current_close,
            price=entry_price,  # Entry above inside bar high
            timeframe=timeframe,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=signal_metadata,
        )
