"""
Doji Reversal Strategy

Adapted from Quantzed's screening_28 'DOJI'.

This strategy identifies potential reversal opportunities when:
1. A doji candlestick pattern forms (open equals close)
2. Indicates market indecision and potential trend reversal
3. Most effective at key support/resistance levels

A doji represents equilibrium between buyers and sellers, often
signaling that the current trend may be losing momentum and
a reversal could be imminent.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from ta_bot.models.signal import Signal, SignalStrength
from ta_bot.strategies.base_strategy import BaseStrategy


class DojiReversalStrategy(BaseStrategy):
    """
    Doji Reversal Strategy

    Identifies potential reversal opportunities when doji candlestick
    patterns form, indicating market indecision and potential trend changes.
    """

    def __init__(self):
        super().__init__()
        self.name = "Doji Reversal"
        self.description = (
            "Identifies potential reversals using doji candlestick patterns"
        )
        self.min_periods = 20  # Need some context for trend determination
        self.logger = logging.getLogger(__name__)

    def analyze(self, data: pd.DataFrame, metadata: dict[str, Any]) -> Optional[Signal]:
        """
        Analyze market data for doji reversal opportunities.

        Args:
            data: OHLCV DataFrame with datetime index
            metadata: Dictionary containing symbol, timeframe, and technical indicators

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

            # Doji condition: open equals close (or very close)
            price_range = current_high - current_low
            if price_range < 0.0001:  # Avoid division by zero
                return None

            body_size = abs(current_close - current_open)
            body_percentage = body_size / price_range

            # Doji: body is very small relative to the total range
            is_doji = body_percentage <= 0.05  # Body is 5% or less of total range

            if is_doji:
                # Determine trend context for reversal signal
                sma10 = data["close"].rolling(10).mean()
                if sma10.empty:
                    return None

                current_sma10 = float(sma10.iloc[-1])

                # Determine trend direction
                trend_bullish = current_close > current_sma10
                trend_bearish = current_close < current_sma10

                if trend_bullish:
                    # In uptrend, doji suggests potential bearish reversal
                    action = "sell"
                    entry_price = current_low
                    stop_loss = current_high
                    risk_amount = stop_loss - entry_price
                    take_profit = entry_price - (risk_amount * 1.2)

                elif trend_bearish:
                    # In downtrend, doji suggests potential bullish reversal
                    action = "buy"
                    entry_price = current_high
                    stop_loss = current_low
                    risk_amount = entry_price - stop_loss
                    take_profit = entry_price + (risk_amount * 1.2)
                else:
                    # No clear trend, skip
                    return None

                # Calculate confidence based on doji quality and trend strength
                doji_quality = 1.0 - (
                    body_percentage / 0.05
                )  # Higher quality = smaller body
                trend_distance = abs(current_close - current_sma10) / current_close
                trend_strength = min(0.2, trend_distance * 10)  # Max 20% bonus

                confidence = min(0.70, 0.40 + (doji_quality * 0.20) + trend_strength)

                return Signal(
                    strategy_id="doji_reversal",
                    symbol=metadata.get("symbol", "UNKNOWN"),
                    action=action,
                    confidence=confidence,
                    current_price=current_close,
                    price=entry_price,
                    timeframe=metadata.get("timeframe", "15m"),
                    strength=SignalStrength.LOW,  # Doji is more of a warning than strong signal
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    timestamp=datetime.utcnow().isoformat(),
                    metadata={
                        "body_size": body_size,
                        "total_range": price_range,
                        "body_percentage": body_percentage,
                        "doji_quality": doji_quality,
                        "trend_context": "bullish" if trend_bullish else "bearish",
                        "sma10": current_sma10,
                        "risk_reward_ratio": 1.2,
                        "pattern": "doji_reversal",
                        "entry_price": entry_price,
                    },
                )

        except Exception as e:
            self.logger.error(f"Error in {self.name} analysis: {e}")
            return None

        return None
