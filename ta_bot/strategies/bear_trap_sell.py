"""
Bear Trap Sell Strategy

Adapted from Quantzed's screening_34 'TRAP URSO VENDA'.

This strategy identifies bearish reversal opportunities when:
1. Price briefly breaks above EMA80 (creating false bullish hope)
2. Price closes back below EMA80 (failing the breakout)
3. Recent closes show weakness below EMA80
4. Clear risk management with stop loss and take profit levels

This is the opposite of the Bear Trap Buy - here bulls get trapped
in long positions as the price fails to sustain above key resistance.
"""

from datetime import datetime
from typing import Optional

import pandas as pd

from ta_bot.models.signal import Signal, SignalStrength, SignalType
from ta_bot.strategies.base_strategy import BaseStrategy


class BearTrapSellStrategy(BaseStrategy):
    """
    Bear Trap Sell Strategy

    Identifies bearish reversal setups where price briefly breaks above
    a key moving average (EMA80) but fails to sustain, trapping bulls
    in losing long positions.
    """

    def __init__(self):
        super().__init__()
        self.name = "Bear Trap Sell"
        self.description = "Identifies bearish reversals when price fails to sustain above EMA80 after brief breakout"
        self.min_periods = 125  # Need sufficient data for EMA80

    def analyze(self, data: pd.DataFrame, metadata: dict) -> Optional[Signal]:
        """
        Analyze market data for bear trap sell opportunities.

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
            current_low = float(data["low"].iloc[-1])
            current_high = float(data["high"].iloc[-1])
            current_ema80 = float(ema80.iloc[-1])

            prev_close = float(data["close"].iloc[-2])
            prev_ema80 = float(ema80.iloc[-2])

            # Check recent weakness below EMA80 (last 4 periods)
            recent_closes = data["close"].iloc[-4:].astype(float)
            recent_ema80 = ema80.iloc[-4:].astype(float)
            weakness_below_ema80 = all(recent_closes < recent_ema80)

            # Bear trap sell conditions:
            # 1. High touched above EMA80 (the false breakout)
            # 2. Close is back below EMA80 (failed breakout)
            # 3. Previous close was also below previous EMA80 (confirming failure)
            # 4. Recent closes show weakness below EMA80
            bear_trap_sell_condition = (
                current_high > current_ema80
                and current_close < current_ema80  # High broke above EMA80
                and prev_close < prev_ema80  # Close back below EMA80
                and weakness_below_ema80  # Previous close also below EMA80  # Recent weakness confirmation
            )

            if bear_trap_sell_condition:
                # Risk management
                entry_price = current_low
                stop_loss = current_high
                risk_amount = stop_loss - entry_price
                take_profit = entry_price - (risk_amount * 2)  # 1:2 risk/reward

                # Calculate confidence based on failure strength
                breakout_failure_distance = current_ema80 - current_close
                false_breakout_height = current_high - current_ema80
                failure_ratio = (
                    breakout_failure_distance / false_breakout_height
                    if false_breakout_height > 0
                    else 1.0
                )

                confidence = min(0.85, 0.60 + (failure_ratio * 0.25))

                return Signal(
                    symbol=symbol,
                    strategy=self.name,
                    signal_type=SignalType.SELL,
                    strength=SignalStrength.MEDIUM,
                    confidence=confidence,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timestamp=datetime.utcnow().isoformat(),
                    metadata={
                        "ema80": current_ema80,
                        "false_breakout_height": false_breakout_height,
                        "breakout_failure_distance": breakout_failure_distance,
                        "failure_ratio": failure_ratio,
                        "risk_reward_ratio": 2.0,
                        "pattern": "bear_trap_sell_reversal",
                    },
                )

        except Exception as e:
            self.logger.error(f"Error in {self.name} analysis: {e}")
            return None

        return None
