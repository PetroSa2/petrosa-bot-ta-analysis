"""
EMA Momentum Reversal Strategy
Adapted from Quantzed Screenings 13-16: "SETUP 9" series

Detects momentum reversals using EMA9 slope changes and
specific price action patterns for high-probability entries.
"""

from typing import Any, Dict, Optional

import pandas as pd

from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class EMAMomentumReversalStrategy(BaseStrategy):
    """
    EMA Momentum Reversal Strategy

    Multiple setups based on EMA9 momentum analysis:

    Setup 9.1 (Screening 13):
        - EMA9 slope changes from negative to positive
        - Current close > EMA9
        - Previous slope was negative

    Setup 9.2 (Screening 14):
        - No lows above EMA9 in last 5 periods
        - No positive slopes in last 5 periods
        - Current close < previous low (capitulation)

    Setup 9.3 (Screening 15):
        - Lows not consistently above EMA9 (last 3 periods)
        - Negative slopes in last 5 periods
        - Specific close pattern: close_2 < close_3 AND close < close_3

    Setup 9.4 (Screening 16):
        - Complex EMA9 reversal with slope analysis
        - Close_2 < EMA9_2 AND low > low_2
        - EMA9 slope: negative to positive transition

    Adapted from Quantzed Brazilian market screening strategies.
    """

    def analyze(
        self,
        df: pd.DataFrame,
        metadata: Dict[str, Any],
    ) -> Optional[Signal]:
        """Analyze for EMA momentum reversal signals."""
        if len(df) < 60:  # Need sufficient data for pattern analysis
            return None

        # Extract indicators from metadata
        indicators = {
            k: v for k, v in metadata.items() if k not in ["symbol", "timeframe"]
        }
        symbol = metadata.get("symbol", "UNKNOWN")
        timeframe = metadata.get("timeframe", "15m")

        # Calculate EMA9 if not provided
        if "ema9" not in indicators:
            indicators["ema9"] = (
                df["close"].ewm(span=9, min_periods=8, adjust=True).mean()
            )

        # Need sufficient historical data for pattern analysis
        if len(df) < 10:
            return None

        ema9_series = indicators["ema9"]
        if not isinstance(ema9_series, pd.Series) or len(ema9_series) < 10:
            return None

        # Calculate EMA9 slope (momentum)
        ema9_slope = ema9_series.diff()

        current = self._get_current_values(indicators, df)

        # Check if we have required data
        if "ema9" not in current or "close" not in current:
            return None

        current_close = current["close"]
        current_ema9 = current["ema9"]
        current_high = current["high"]
        current_low = current["low"]

        # Try each setup pattern
        setup_detected = None
        setup_confidence = 0.70

        # Setup 9.1: EMA slope reversal (Screening 13)
        if len(ema9_slope) >= 2:
            current_slope = ema9_slope.iloc[-1]
            previous_slope = ema9_slope.iloc[-2]

            # Slope changes from negative to positive
            slope_reversal = previous_slope < 0 and current_slope > 0
            price_above_ema = current_close > current_ema9

            if slope_reversal and price_above_ema:
                setup_detected = "setup_9_1_slope_reversal"
                setup_confidence = 0.76
                screening_origin = "quantzed_screening_13"

        # Setup 9.2: Capitulation pattern (Screening 14)
        if not setup_detected and len(df) >= 5:
            # Check if no lows above EMA9 in last 5 periods
            lows_last_5 = df["low"].iloc[-5:]
            ema9_last_5 = ema9_series.iloc[-5:]

            no_lows_above_ema9 = not any(
                lows_last_5.iloc[i] > ema9_last_5.iloc[i] for i in range(5)
            )

            # Check if no positive slopes in last 5 periods
            slopes_last_5 = ema9_slope.iloc[-5:]
            no_positive_slopes = not any(slope > 0 for slope in slopes_last_5)

            # Current close < previous low (capitulation)
            previous_low = df["low"].iloc[-2]
            capitulation = current_close < previous_low

            if no_lows_above_ema9 and no_positive_slopes and capitulation:
                setup_detected = "setup_9_2_capitulation"
                setup_confidence = 0.78
                screening_origin = "quantzed_screening_14"

        # Setup 9.3: Pattern-based reversal (Screening 15)
        if not setup_detected and len(df) >= 5:
            # Lows not consistently above EMA9 (last 3 periods)
            lows_last_3 = df["low"].iloc[-3:]
            ema9_last_3 = ema9_series.iloc[-3:]

            inconsistent_above_ema9 = not all(
                lows_last_3.iloc[i] > ema9_last_3.iloc[i] for i in range(3)
            )

            # Negative slopes in last 5 periods
            slopes_last_5 = ema9_slope.iloc[-5:]
            mostly_negative_slopes = sum(1 for slope in slopes_last_5 if slope < 0) >= 3

            # Specific close pattern
            if len(df) >= 3:
                close_3 = df["close"].iloc[-3]  # 3 candles ago
                close_2 = df["close"].iloc[-2]  # 2 candles ago
                close_1 = current_close  # Current close

                close_pattern = (close_2 < close_3) and (close_1 < close_3)
            else:
                close_pattern = False

            if inconsistent_above_ema9 and mostly_negative_slopes and close_pattern:
                setup_detected = "setup_9_3_pattern_reversal"
                setup_confidence = 0.74
                screening_origin = "quantzed_screening_15"

        # Setup 9.4: Advanced reversal (Screening 16)
        if not setup_detected and len(df) >= 7:
            # Complex conditions from Quantzed Screening 16
            if len(ema9_series) >= 7:
                # Lows not above EMA9 (periods -7 to -2)
                lows_range = df["low"].iloc[-7:-2]
                ema9_range = ema9_series.iloc[-7:-2]

                lows_not_above_ema9 = not all(
                    lows_range.iloc[i] > ema9_range.iloc[i] for i in range(5)
                )

                # Close_2 < EMA9_2 AND low > low_2
                close_2 = df["close"].iloc[-2]
                ema9_2 = ema9_series.iloc[-2]
                low_2 = df["low"].iloc[-2]

                condition_1 = close_2 < ema9_2
                condition_2 = current_low > low_2

                # EMA9 slope: negative to positive transition
                if len(ema9_slope) >= 2:
                    slope_transition = (
                        ema9_slope.iloc[-2] < 0 and ema9_slope.iloc[-1] > 0
                    )
                else:
                    slope_transition = False

                if (
                    lows_not_above_ema9
                    and condition_1
                    and condition_2
                    and slope_transition
                ):
                    setup_detected = "setup_9_4_advanced_reversal"
                    setup_confidence = 0.80
                    screening_origin = "quantzed_screening_16"

        if not setup_detected:
            return None

        # Calculate additional quality metrics
        ema9_momentum = (
            current_ema9 - ema9_series.iloc[-2] if len(ema9_series) >= 2 else 0
        )
        price_distance_from_ema = (
            abs(current_close - current_ema9) / current_ema9 if current_ema9 > 0 else 0
        )

        # Adjust confidence based on momentum and price position
        momentum_adjustment = (
            min(0.05, abs(ema9_momentum) * 100) if ema9_momentum > 0 else 0
        )
        distance_penalty = min(0.08, price_distance_from_ema * 10)

        final_confidence = max(
            0.60, min(0.88, setup_confidence + momentum_adjustment - distance_penalty)
        )

        # Risk management: Use current high/low for entry and stops
        entry_price = current_high  # Breakout entry
        stop_loss = current_low
        risk_amount = entry_price - stop_loss
        take_profit = entry_price + (risk_amount * 2)  # 2:1 R:R

        # Prepare metadata for signal
        signal_metadata = {
            "setup_type": setup_detected,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": 2.0,
            "ema9": current_ema9,
            "ema9_momentum": ema9_momentum,
            "price_distance_from_ema": price_distance_from_ema,
            "current_slope": ema9_slope.iloc[-1] if len(ema9_slope) >= 1 else 0,
            "previous_slope": ema9_slope.iloc[-2] if len(ema9_slope) >= 2 else 0,
            "strategy_origin": screening_origin,
        }

        return Signal(
            strategy_id="ema_momentum_reversal",
            symbol=symbol,
            action="buy",  # All setups are bullish reversal patterns
            confidence=final_confidence,
            current_price=current_close,
            price=entry_price,
            timeframe=timeframe,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=signal_metadata,
        )
