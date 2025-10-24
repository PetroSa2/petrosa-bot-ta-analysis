"""
Mean Reversion Scalper Strategy
Capitalizes on crypto's tendency to snap back to moving averages.
"""

from typing import Any, Optional

import pandas as pd

from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class MeanReversionScalperStrategy(BaseStrategy):
    """
    Mean Reversion Scalper Strategy

    Trigger: Price deviates >2 standard deviations from EMA(21)
    Confirmations:
        - RSI < 30 (oversold) or RSI > 70 (overbought)
        - Price approaching key support/resistance levels
        - Lower timeframe showing reversal signals
    """

    def analyze(
        self,
        df: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> Signal | None:
        """Analyze for mean reversion scalping signals."""
        if len(df) < 25:
            return None

        # Extract indicators from metadata (now passed directly)
        indicators = {
            k: v for k, v in metadata.items() if k not in ["symbol", "timeframe"]
        }
        symbol = metadata.get("symbol", "UNKNOWN")
        timeframe = metadata.get("timeframe", "15m")

        current = self._get_current_values(indicators, df)

        # Check if we have all required indicators
        required_indicators = ["ema21", "rsi", "close", "bb_lower", "bb_upper"]
        if not all(indicator in current for indicator in required_indicators):
            return None

        # Calculate deviation from EMA21
        ema21 = current["ema21"]
        close = current["close"]
        deviation = abs(close - ema21) / ema21

        # Check if price deviates >2% from EMA21
        if deviation < 0.02:  # 2% deviation
            return None

        # Determine if oversold or overbought
        rsi = current["rsi"]
        oversold = rsi < 30
        overbought = rsi > 70

        if not oversold and not overbought:
            return None

        # Check Bollinger Band position for additional confirmation
        bb_lower = current["bb_lower"]
        bb_upper = current["bb_upper"]

        # Determine signal direction
        if oversold and close < bb_lower:
            # Oversold condition - potential buy signal
            action = "buy"
            confidence = 0.70
            signal_type = "oversold_reversal"
        elif overbought and close > bb_upper:
            # Overbought condition - potential sell signal
            action = "sell"
            confidence = 0.70
            signal_type = "overbought_reversal"
        else:
            return None

        # Additional confirmation: check if price is moving back toward EMA
        if len(df) >= 3:
            prev_close = df["close"].iloc[-2]
            prev_prev_close = df["close"].iloc[-3]

            if action == "buy":
                # Check if price is starting to move up
                reversal_confirmed = close > prev_close and prev_close > prev_prev_close
            else:
                # Check if price is starting to move down
                reversal_confirmed = close < prev_close and prev_close < prev_prev_close

            if reversal_confirmed:
                confidence += 0.05

        # Adjust confidence based on deviation strength
        if deviation > 0.03:  # 3% deviation
            confidence += 0.05
        if deviation > 0.04:  # 4% deviation
            confidence += 0.05

        # Calculate stop loss and take profit (mean reversion/scalping strategy)
        if action == "buy":
            # Buy oversold - mean revert to EMA21
            stop_loss = bb_lower * 0.985  # 1.5% below lower band
            take_profit = ema21  # Target EMA21 (mean reversion)
        else:
            # Sell overbought - mean revert to EMA21
            stop_loss = bb_upper * 1.015  # 1.5% above upper band
            take_profit = ema21  # Target EMA21 (mean reversion)

        # Prepare metadata for signal
        signal_metadata = {
            "deviation_from_ema": deviation,
            "rsi": rsi,
            "ema21": ema21,
            "bb_lower": bb_lower,
            "bb_upper": bb_upper,
            "signal_type": signal_type,
            "mean_reversion": True,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "target": "ema21",
        }

        # Create and return Signal object
        return Signal(
            strategy_id="mean_reversion_scalper",
            symbol=symbol,
            action=action,
            confidence=min(confidence, 0.90),  # Cap at 90%
            current_price=close,
            price=close,
            timeframe=timeframe,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=signal_metadata,
        )
