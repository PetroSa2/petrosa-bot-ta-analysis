"""
Inside Bar Sell Strategy

Adapted from Quantzed's screening_22 'VENDA POR INSIDE BAR'.

This strategy identifies bearish reversal opportunities when:
1. Price is in a bearish context (below EMAs)
2. An inside bar pattern forms (current bar contained within previous bar)
3. The setup suggests continuation of the downtrend

Inside bars represent consolidation and indecision, and when they occur
in a bearish context, they often precede further downward movement.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from ta_bot.core.indicators import Indicators
from ta_bot.models.signal import Signal, SignalStrength
from ta_bot.strategies.base_strategy import BaseStrategy


class InsideBarSellStrategy(BaseStrategy):
    """
    Inside Bar Sell Strategy

    Identifies bearish continuation setups when an inside bar pattern
    forms in a bearish market context, suggesting further downside.
    """

    def __init__(self):
        super().__init__()
        self.name = "Inside Bar Sell"
        self.description = (
            "Identifies bearish continuation when inside bar forms in downtrend context"
        )
        self.min_periods = 125  # Need sufficient data for EMAs
        self.logger = logging.getLogger(__name__)
        self.indicators = Indicators()

    def analyze(self, data: pd.DataFrame, metadata: dict[str, Any]) -> Optional[Signal]:
        """
        Analyze market data for inside bar sell opportunities.

        Args:
            data: OHLCV DataFrame with datetime index
            metadata: Dictionary containing symbol, timeframe, and technical indicators

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

            # Current and previous bar data
            current_close = float(data["close"].iloc[-1])
            current_low = float(data["low"].iloc[-1])
            current_high = float(data["high"].iloc[-1])

            prev_high = float(data["high"].iloc[-2])
            prev_low = float(data["low"].iloc[-2])

            current_ema8 = float(ema8.iloc[-1])
            current_ema80 = float(ema80.iloc[-1])

            # Inside bar pattern: current bar is completely within previous bar
            inside_bar_pattern = (
                current_high < prev_high
                and current_low  # Current high below previous high
                > prev_low  # Current low above previous low
            )

            # Bearish context: price below both EMAs
            bearish_context = (
                current_close < current_ema8 and current_close < current_ema80
            )

            if inside_bar_pattern and bearish_context:
                # Risk management
                entry_price = current_low
                stop_loss = current_high
                risk_amount = stop_loss - entry_price
                take_profit = entry_price - (risk_amount * 2)  # 1:2 risk/reward

                # Calculate confidence based on bearish strength
                ema_separation = abs(current_ema8 - current_ema80) / current_close
                bearish_strength = (current_ema80 - current_close) / current_close
                confidence = min(
                    0.80, 0.55 + (bearish_strength * 10) + (ema_separation * 5)
                )

                return Signal(
                    strategy_id="inside_bar_sell",
                    symbol=metadata.get("symbol", "UNKNOWN"),
                    action="sell",
                    confidence=confidence,
                    current_price=current_close,
                    price=entry_price,
                    timeframe=metadata.get("timeframe", "15m"),
                    strength=SignalStrength.MEDIUM,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timestamp=datetime.utcnow().isoformat(),
                    metadata={
                        "ema8": current_ema8,
                        "ema80": current_ema80,
                        "inside_bar_range": prev_high - prev_low,
                        "consolidation_size": current_high - current_low,
                        "bearish_context_strength": bearish_strength,
                        "risk_reward_ratio": 2.0,
                        "pattern": "inside_bar_bearish_continuation",
                        "entry_price": entry_price,
                    },
                )

        except Exception as e:
            self.logger.error(f"Error in {self.name} analysis: {e}")
            return None

        return None
