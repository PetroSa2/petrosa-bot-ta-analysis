"""
Momentum Pulse Strategy
Detects trend entry signals based on MACD histogram crossovers.
"""

from typing import Dict, Any, Optional
import pandas as pd
from ta_bot.models.signal import SignalType
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
        indicators: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Analyze for momentum pulse signals."""
        if len(df) < 2:
            return None

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

        # Prepare metadata for signal
        signal_metadata = {
            "macd_hist": current["macd_hist"],
            "macd_signal": current.get("macd_signal", 0),
            "rsi": current["rsi"],
            "volume": current.get("volume", 0),
        }

        return {
            "signal_type": SignalType.BUY,
            "metadata": signal_metadata,
        }
