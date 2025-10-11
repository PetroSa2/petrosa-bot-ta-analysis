"""
EMA Alignment Bearish Strategy

Adapted from Quantzed's screening_29 'ALINHAMENTO DE MÉDIAS (BAIXA)'.

This strategy identifies strong bearish trend confirmation when:
1. Price is below both EMA8 and EMA80
2. Both EMAs show negative inclination (declining trend)
3. Sustained bearish momentum over recent periods

This is the bearish counterpart to the EMA Alignment Bullish strategy,
confirming strong downtrend conditions with multiple EMA confirmations.
"""

from typing import Optional

import pandas as pd

from ta_bot.models.signal import Signal, SignalStrength, SignalType
from ta_bot.strategies.base_strategy import BaseStrategy


class EMAAlignmentBearishStrategy(BaseStrategy):
    """
    EMA Alignment Bearish Strategy

    Identifies strong bearish trend confirmation when price and multiple
    EMAs are aligned in a bearish configuration with declining momentum.
    """

    def __init__(self):
        super().__init__()
        self.name = "EMA Alignment Bearish"
        self.description = (
            "Confirms strong bearish trends using EMA alignment and slope analysis"
        )
        self.min_periods = 125  # Need sufficient data for EMA80

    def analyze(self, data: pd.DataFrame, metadata: dict) -> Optional[Signal]:
        """
        Analyze market data for bearish EMA alignment opportunities.

        Args:
            data: OHLCV DataFrame with datetime index
            metadata: Dictionary containing symbol, timeframe, and technical indicators

        Returns:
            Signal object if conditions are met, None otherwise
        """
        if len(data) < self.min_periods:
            return None

        try:
            # Extract symbol from metadata
            symbol = metadata.get("symbol", "UNKNOWN")

            # Calculate EMAs
            ema8 = self.indicators.ema(data["close"], 8)
            ema80 = self.indicators.ema(data["close"], 80)

            if ema8.empty or ema80.empty:
                return None

            # Current values
            current_close = float(data["close"].iloc[-1])
            current_high = float(data["high"].iloc[-1])

            current_ema8 = float(ema8.iloc[-1])
            current_ema80 = float(ema80.iloc[-1])

            # Calculate EMA inclinations (slopes)
            ema8_slope_1 = ema8.iloc[-1] - ema8.iloc[-2]
            ema8_slope_2 = ema8.iloc[-2] - ema8.iloc[-3]
            ema80_slope_1 = ema80.iloc[-1] - ema80.iloc[-2]
            ema80_slope_2 = ema80.iloc[-2] - ema80.iloc[-3]

            # Bearish alignment conditions:
            # 1. Price below both EMAs
            price_below_emas = (
                current_close < current_ema8 and current_close < current_ema80
            )

            # 2. Both EMAs showing negative inclination for last 2 periods
            ema8_declining = ema8_slope_1 < 0 and ema8_slope_2 < 0
            ema80_declining = ema80_slope_1 < 0 and ema80_slope_2 < 0

            if price_below_emas and ema8_declining and ema80_declining:
                # This is primarily a trend confirmation signal
                # Entry at current level with tight risk management
                entry_price = current_close
                stop_loss = max(
                    current_ema8, current_high
                )  # Stop above EMAs or current high
                risk_amount = stop_loss - entry_price
                take_profit = entry_price - (risk_amount * 1.5)  # 1:1.5 risk/reward

                # Calculate confidence based on alignment strength
                price_distance_from_ema8 = (
                    current_ema8 - current_close
                ) / current_close
                price_distance_from_ema80 = (
                    current_ema80 - current_close
                ) / current_close
                ema_separation = abs(current_ema8 - current_ema80) / current_close

                # Stronger slopes indicate stronger trend
                slope_strength = (
                    abs(ema8_slope_1) + abs(ema80_slope_1)
                ) / current_close

                confidence = min(
                    0.85,
                    0.60
                    + (price_distance_from_ema8 * 10)
                    + (price_distance_from_ema80 * 5)
                    + (slope_strength * 20),
                )

                return Signal(
                    symbol=symbol,
                    strategy=self.name,
                    signal_type=SignalType.SELL,
                    strength=SignalStrength.HIGH,  # Strong trend confirmation
                    confidence=confidence,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timestamp=data.index[-1],
                    metadata={
                        "ema8": current_ema8,
                        "ema80": current_ema80,
                        "ema8_slope_1": ema8_slope_1,
                        "ema8_slope_2": ema8_slope_2,
                        "ema80_slope_1": ema80_slope_1,
                        "ema80_slope_2": ema80_slope_2,
                        "price_distance_ema8": price_distance_from_ema8,
                        "price_distance_ema80": price_distance_from_ema80,
                        "ema_separation": ema_separation,
                        "risk_reward_ratio": 1.5,
                        "pattern": "bearish_ema_alignment",
                    },
                )

        except Exception as e:
            self.logger.error(f"Error in {self.name} analysis: {e}")
            return None

        return None
