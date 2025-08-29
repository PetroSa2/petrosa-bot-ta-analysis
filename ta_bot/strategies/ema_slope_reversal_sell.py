"""
EMA Slope Reversal Sell Strategy

Adapted from Quantzed's screening_30 'SETUP 9.1 VENDA'.

This strategy identifies bearish reversal opportunities when:
1. EMA9 slope changes from positive to negative (momentum shift)
2. Price is below EMA9 (bearish context)
3. Previous inclination was positive (reversal from uptrend)

This captures the moment when bullish momentum starts to fade
and bearish momentum begins to take control.
"""

from typing import Optional

import pandas as pd

from ta_bot.models.signal import Signal, SignalStrength, SignalType
from ta_bot.strategies.base_strategy import BaseStrategy


class EMASlopeReversalSellStrategy(BaseStrategy):
    """
    EMA Slope Reversal Sell Strategy

    Identifies bearish reversal opportunities when EMA9 slope
    changes from positive to negative, indicating momentum shift.
    """

    def __init__(self):
        super().__init__()
        self.name = "EMA Slope Reversal Sell"
        self.description = "Identifies bearish reversals when EMA9 slope changes from positive to negative"
        self.min_periods = 60  # Need sufficient data for EMA9 and slope analysis

    def analyze(self, data: pd.DataFrame) -> Optional[Signal]:
        """
        Analyze market data for EMA slope reversal sell opportunities.

        Args:
            data: OHLCV DataFrame with datetime index

        Returns:
            Signal object if conditions are met, None otherwise
        """
        if len(data) < self.min_periods:
            return None

        try:
            # Calculate EMA9
            ema9 = self.indicators.ema(data["close"], 9)

            if ema9.empty:
                return None

            # Current values
            current_close = float(data["close"].iloc[-1])
            current_low = float(data["low"].iloc[-1])
            current_high = float(data["high"].iloc[-1])

            current_ema9 = float(ema9.iloc[-1])
            prev_ema9 = float(ema9.iloc[-2])
            prev2_ema9 = float(ema9.iloc[-3])

            # Calculate EMA slopes (inclinations)
            current_inclination = current_ema9 - prev_ema9
            previous_inclination = prev_ema9 - prev2_ema9

            # Setup 9.1 Sell conditions:
            # 1. EMA9 slope changed from positive to negative
            slope_reversal = previous_inclination > 0 and current_inclination < 0

            # 2. Price is below EMA9 (bearish context)
            price_below_ema = current_close < current_ema9

            if slope_reversal and price_below_ema:
                # Risk management
                entry_price = current_low
                stop_loss = current_high
                risk_amount = stop_loss - entry_price
                take_profit = entry_price - (risk_amount * 2)  # 1:2 risk/reward

                # Calculate confidence based on reversal strength
                slope_change_magnitude = abs(current_inclination - previous_inclination)
                price_distance_from_ema = (current_ema9 - current_close) / current_close

                # Normalize slope change relative to price
                normalized_slope_change = slope_change_magnitude / current_close

                confidence = min(
                    0.80,
                    0.55
                    + (normalized_slope_change * 50)
                    + (price_distance_from_ema * 10),  # Slope change strength
                )  # Distance from EMA

                return Signal(
                    symbol=data.attrs.get("symbol", "UNKNOWN"),
                    strategy=self.name,
                    signal_type=SignalType.SELL,
                    strength=SignalStrength.MEDIUM,
                    confidence=confidence,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timestamp=data.index[-1],
                    metadata={
                        "ema9": current_ema9,
                        "current_inclination": current_inclination,
                        "previous_inclination": previous_inclination,
                        "slope_change": slope_change_magnitude,
                        "price_distance_from_ema": price_distance_from_ema,
                        "normalized_slope_change": normalized_slope_change,
                        "risk_reward_ratio": 2.0,
                        "pattern": "ema9_slope_reversal_bearish",
                    },
                )

        except Exception as e:
            self.logger.error(f"Error in {self.name} analysis: {e}")
            return None

        return None
