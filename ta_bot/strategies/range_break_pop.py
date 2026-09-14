"""
Range Break Pop Strategy
Detects volatility breakout signals when price breaks above a tight range.
"""

from typing import Any, Optional

import pandas as pd

from ta_bot.core.indicators import Indicators
from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class RangeBreakPopStrategy(BaseStrategy):
    """
    Range Break Pop Strategy

    Trigger: Price breaks above recent tight range (10 candles < 2.5% spread)
    Confirmations:
        - ATR(14) falling
        - RSI ~50
        - Breakout volume > 1.5x average
    """

    def __init__(self):
        """Initialize the strategy."""
        super().__init__()
        self.indicators = Indicators()

    def analyze(self, df: pd.DataFrame, metadata: dict[str, Any]) -> Signal | None:
        """Analyze candles for Range Break Pop signals."""
        if len(df) < 20:
            return None

        # Extract indicators from metadata (now passed directly)
        indicators = {
            k: v for k, v in metadata.items() if k not in ["symbol", "timeframe"]
        }
        symbol = metadata.get("symbol", "UNKNOWN")
        timeframe = metadata.get("timeframe", "15m")

        # Get current values using base strategy methods
        current_values = self._get_current_values(indicators, df)
        previous_values = self._get_previous_values(indicators, df)

        # Check if we have all required indicators (per issue #282 AC-A:
        # rsi is required again since the RSI ~50 gate is restored)
        required_indicators = ["atr", "rsi", "close", "high", "low", "volume"]
        if not all(indicator in current_values for indicator in required_indicators):
            return None

        close = current_values["close"]
        current_atr = current_values["atr"]
        current_rsi = current_values["rsi"]
        volume = current_values["volume"]
        previous_atr = previous_values.get("atr", current_atr)

        # Tight-range precondition: last 10 candles (excluding current) must
        # be within a 2.5% spread. Restored per issue #282 (the loosened
        # version dropped this precondition entirely).
        recent_high = df["high"].iloc[-11:-1].max()
        recent_low = df["low"].iloc[-11:-1].min()
        range_spread = (recent_high - recent_low) / recent_low * 100

        if range_spread >= 2.5:
            return None

        # Trigger: current close breaks above the recent tight range
        breakout_trigger = close > recent_high
        if not breakout_trigger:
            return None

        # Confirmations (all restored to hard gates per issue #282)
        atr_falling = current_atr < previous_atr
        rsi_ok = 45 <= current_rsi <= 55

        avg_volume = df["volume"].iloc[-11:-1].mean()
        volume_ratio = volume / avg_volume if avg_volume > 0 else 0.0
        volume_ok = volume_ratio > 1.5

        if not (atr_falling and rsi_ok and volume_ok):
            return None

        # Calculate stop loss and take profit (breakout strategy)
        # Stop loss below the recent range low
        stop_loss = recent_low * 0.99  # 1% below range low
        risk = abs(close - stop_loss)
        take_profit = close + (risk * 2.0)  # 2:1 R:R for range breakouts

        # Create and return Signal object
        return Signal(
            strategy_id="range_break_pop",
            symbol=symbol,
            action="buy",
            confidence=0.75,  # Restored per issue #282 (was loosened to 0.68)
            current_price=close,
            price=close,
            timeframe=timeframe,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata={
                "atr": current_atr,
                "rsi": current_rsi,
                "range_spread": range_spread,
                "recent_high": recent_high,
                "volume_ratio": volume_ratio,
                "atr_falling": atr_falling,
                "rsi_neutral": rsi_ok,
                "volume_breakout": volume_ok,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk_reward_ratio": 2.0,
            },
        )
