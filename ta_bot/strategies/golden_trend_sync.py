"""
Golden Trend Sync strategy for technical analysis.
"""

from typing import Any, Dict, Optional

import pandas as pd

from ta_bot.core.indicators import Indicators
from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class GoldenTrendSyncStrategy(BaseStrategy):
    """Golden Trend Sync strategy implementation."""

    def __init__(self):
        """Initialize the strategy."""
        super().__init__()
        self.indicators = Indicators()

    def analyze(self, df: pd.DataFrame, metadata: Dict[str, Any]) -> Optional[Signal]:
        """Analyze candles for Golden Trend Sync signals."""
        if len(df) < 50:
            return None

        # Extract indicators from metadata (now passed directly)
        indicators = {
            k: v for k, v in metadata.items() if k not in ["symbol", "timeframe"]
        }
        symbol = metadata.get("symbol", "UNKNOWN")
        timeframe = metadata.get("timeframe", "15m")

        # Get current values using base strategy methods
        current_values = self._get_current_values(indicators, df)

        # Check if we have all required indicators
        required_indicators = ["ema21", "ema50", "close", "open"]
        if not all(indicator in current_values for indicator in required_indicators):
            return None

        close = current_values["close"]
        current_ema21 = current_values["ema21"]
        current_ema50 = current_values["ema50"]

        # Check for golden cross (EMA21 > EMA50)
        golden_cross = current_ema21 > current_ema50

        # Check for pullback to EMA21 (price near EMA21)
        pullback_distance = abs(close - current_ema21) / current_ema21
        pullback_to_ema21 = pullback_distance <= 0.02  # Within 2%

        # Check for bullish candle (close > open)
        bullish_candle = close > current_values["open"]

        if golden_cross and pullback_to_ema21 and bullish_candle:
            # Calculate stop loss and take profit
            # Stop loss at EMA50 (as per strategy documentation)
            stop_loss = current_ema50
            # Take profit at 2:1 risk-reward ratio
            risk = abs(close - stop_loss)
            take_profit = close + (risk * 2.0)

            # Create and return Signal object
            return Signal(
                strategy_id="golden_trend_sync",
                symbol=symbol,
                action="buy",
                confidence=0.70,  # Base confidence for golden trend sync
                current_price=close,
                price=close,
                timeframe=timeframe,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata={
                    "ema21": current_ema21,
                    "ema50": current_ema50,
                    "pullback_distance": abs(close - current_ema21) / current_ema21,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "risk_reward_ratio": 2.0,
                },
            )

        return None

    def _calculate_volume_rank(self, df: pd.DataFrame) -> int:
        """Calculate volume rank of current candle compared to last 3 candles."""
        if len(df) < 4:
            return 0

        current_volume = df["volume"].iloc[-1]
        recent_volumes = df["volume"].iloc[-4:-1]

        # Count how many recent candles have higher volume
        higher_volume_count = sum(1 for vol in recent_volumes if vol > current_volume)

        return higher_volume_count
