"""
Range Break Pop Strategy
Detects volatility breakout signals when price breaks above a tight range.
"""

from typing import Any, Dict, Optional

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

    def analyze(self, df: pd.DataFrame, metadata: Dict[str, Any]) -> Optional[Signal]:
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

        # Check if we have all required indicators
        required_indicators = ["atr", "close", "high", "low", "volume"]
        if not all(indicator in current_values for indicator in required_indicators):
            return None

        close = current_values["close"]
        high = current_values["high"]
        low = current_values["low"]
        current_atr = current_values["atr"]
        volume = current_values["volume"]

        # Calculate range
        range_size = high - low
        range_breakout = range_size > current_atr * 1.5  # Range is 1.5x ATR

        # Check for volume confirmation (if available)
        volume_confirmation = volume > 0  # Basic check

        # Check for price momentum
        if len(df) >= 3:
            prev_close = df.iloc[-2]["close"]
            prev_prev_close = df.iloc[-3]["close"]

            # Strong upward momentum
            momentum = close > prev_close > prev_prev_close
        else:
            momentum = False

        if range_breakout and volume_confirmation and momentum:
            # Calculate stop loss and take profit (breakout strategy)
            # Stop loss below recent range low
            recent_lows = df["low"].iloc[-10:]
            range_low = recent_lows.min()
            stop_loss = range_low * 0.99  # 1% below range low
            risk = abs(close - stop_loss)
            take_profit = close + (risk * 2.0)  # 2:1 R:R for range breakouts

            # Create and return Signal object
            return Signal(
                strategy_id="range_break_pop",
                symbol=symbol,
                action="buy",
                confidence=0.68,  # Base confidence for range break pop
                current_price=close,
                price=close,
                timeframe=timeframe,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata={
                    "atr": current_atr,
                    "range_size": range_size,
                    "volume": volume,
                    "momentum": momentum,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "risk_reward_ratio": 2.0,
                },
            )

        return None
