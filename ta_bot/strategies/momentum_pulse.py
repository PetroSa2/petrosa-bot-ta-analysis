"""
Momentum Pulse Strategy
Detects trend entry signals based on MACD histogram crossovers.
"""

from typing import Any, Dict, Optional

import pandas as pd

from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class MomentumPulseStrategy(BaseStrategy):
    """
    Momentum Pulse Strategy

    Trigger: MACD Histogram crosses from negative to positive
    Confirmations:
        - RSI(14) between 50–65
        - ADX(14) > 20
        - Price above EMA21 and EMA50
    """

    def analyze(
        self,
        df: pd.DataFrame,
        metadata: Dict[str, Any],
    ) -> Optional[Signal]:
        """Analyze for momentum pulse signals."""
        if len(df) < 2:
            return None

        # Extract indicators from metadata (now passed directly)
        indicators = {
            k: v for k, v in metadata.items() if k not in ["symbol", "timeframe"]
        }
        symbol = metadata.get("symbol", "UNKNOWN")
        timeframe = metadata.get("timeframe", "15m")

        current = self._get_current_values(indicators, df)
        previous = self._get_previous_values(indicators, df)

        # Check if we have all required indicators
        required_indicators = ["macd_hist", "rsi", "adx", "ema21", "ema50", "close"]
        if not all(indicator in current for indicator in required_indicators):
            return None

        # Trigger: MACD Histogram crosses from negative to positive
        macd_hist_cross = self._check_cross_above(
            current["macd_hist"], previous["macd_hist"]
        )

        if not macd_hist_cross:
            return None

        # Confirmations
        confirmations = []

        # RSI between 50-65
        rsi_ok = self._check_between(current["rsi"], 50, 65)
        confirmations.append(("rsi_range", rsi_ok))

        # ADX > 20
        adx_ok = current["adx"] > 20
        confirmations.append(("adx_trend", adx_ok))

        # Price above EMA21 and EMA50
        price_above_emas = (
            current["close"] > current["ema21"] and current["close"] > current["ema50"]
        )
        confirmations.append(("price_above_emas", price_above_emas))

        # Check if all confirmations are met
        all_confirmations = all(confirmation[1] for confirmation in confirmations)

        if not all_confirmations:
            return None

        # Calculate stop loss and take profit (momentum/trend strategy)
        # Stop loss at EMA50 (key support in uptrend)
        stop_loss = current["ema50"]
        risk = abs(current["close"] - stop_loss)
        take_profit = current["close"] + (risk * 2.5)  # 2.5:1 R:R for momentum trades

        # Prepare metadata for signal
        signal_metadata = {
            "macd_hist": current["macd_hist"],
            "macd_signal": current.get("macd_signal", 0),
            "rsi": current["rsi"],
            "volume": current.get("volume", 0),
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": 2.5,
        }

        # Create and return Signal object
        return Signal(
            strategy_id="momentum_pulse",
            symbol=symbol,
            action="buy",
            confidence=0.74,  # Base confidence for momentum pulse
            current_price=current["close"],
            price=current["close"],
            timeframe=timeframe,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=signal_metadata,
        )
