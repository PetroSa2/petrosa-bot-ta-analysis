"""
Bear Trap Buy Strategy

Adapted from Quantzed's screening_21 'TRAP URSO COMPRA'.

This strategy identifies bullish reversal opportunities when:
1. Price dips below EMA80 (creating the "trap")
2. Price closes back above EMA80 (breaking out of the trap)
3. Recent closes show strength above EMA80
4. Clear risk management with stop loss and take profit levels

The "bear trap" occurs when bears get trapped in short positions
as the price quickly reverses upward.
"""

from typing import Optional

import pandas as pd

from ta_bot.models.signal import Signal, SignalStrength, SignalType
from ta_bot.strategies.base_strategy import BaseStrategy


class BearTrapBuyStrategy(BaseStrategy):
    """
    Bear Trap Buy Strategy

    Identifies bullish reversal setups where price briefly breaks below
    a key moving average (EMA80) but quickly recovers, trapping bears
    in losing short positions.
    """

    def __init__(self):
        super().__init__()
        self.name = "Bear Trap Buy"
        self.description = "Identifies bullish reversals when price breaks back above EMA80 after brief dip"
        self.min_periods = 125  # Need sufficient data for EMA80

    def analyze(self, data: pd.DataFrame) -> Optional[Signal]:
        """
        Analyze market data for bear trap buy opportunities.

        Args:
            data: OHLCV DataFrame with datetime index

        Returns:
            Signal object if conditions are met, None otherwise
        """
        if len(data) < self.min_periods:
            return None

        try:
            # Calculate EMAs
            ema8 = self.indicators.ema(data["close"], 8)
            ema80 = self.indicators.ema(data["close"], 80)

            if ema8.empty or ema80.empty:
                return None

            # Current values
            current_close = float(data["close"].iloc[-1])
            current_low = float(data["low"].iloc[-1])
            current_high = float(data["high"].iloc[-1])
            current_ema80 = float(ema80.iloc[-1])

            # Check recent strength above EMA80 (last 4 periods)
            recent_closes = data["close"].iloc[-4:].astype(float)
            recent_ema80 = ema80.iloc[-4:].astype(float)
            strength_above_ema80 = all(recent_closes > recent_ema80)

            # Bear trap conditions:
            # 1. Low touched below EMA80 (the "trap")
            # 2. Close is back above EMA80 (escaping the trap)
            # 3. Recent closes show strength above EMA80
            bear_trap_condition = (
                current_low < current_ema80
                and current_close > current_ema80  # Low dipped below EMA80
                and strength_above_ema80  # Close back above EMA80  # Recent strength confirmation
            )

            if bear_trap_condition:
                # Risk management
                entry_price = current_high
                stop_loss = current_low
                risk_amount = entry_price - stop_loss
                take_profit = entry_price + (risk_amount * 2)  # 1:2 risk/reward

                # Calculate confidence based on strength of reversal
                reversal_strength = (current_close - current_low) / (
                    current_high - current_low
                )
                confidence = min(0.85, 0.60 + (reversal_strength * 0.25))

                return Signal(
                    symbol=data.attrs.get("symbol", "UNKNOWN"),
                    strategy=self.name,
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.MEDIUM,
                    confidence=confidence,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timestamp=data.index[-1],
                    metadata={
                        "ema80": current_ema80,
                        "trap_depth": abs(current_low - current_ema80),
                        "recovery_strength": reversal_strength,
                        "risk_reward_ratio": 2.0,
                        "pattern": "bear_trap_reversal",
                    },
                )

        except Exception as e:
            self.logger.error(f"Error in {self.name} analysis: {e}")
            return None

        return None
