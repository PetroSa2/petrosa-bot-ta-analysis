"""
Band Fade Reversal strategy for technical analysis.
"""

import logging
from typing import Any, Optional

import pandas as pd

from ta_bot.core.indicators import Indicators
from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class BandFadeReversalStrategy(BaseStrategy):
    """Band Fade Reversal strategy implementation."""

    def __init__(self):
        """Initialize the strategy."""
        super().__init__()
        self.indicators = Indicators()

    def analyze(self, df: pd.DataFrame, metadata: dict[str, Any]) -> Signal | None:
        """Analyze candles for Band Fade Reversal signals."""
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

        # Debug logging
        logger.info(f"Available indicators: {list(indicators.keys())}")
        logger.info(f"Current values: {list(current_values.keys())}")

        # Check if we have all required indicators
        required_indicators = ["bb_lower", "bb_upper", "bb_middle", "close"]
        missing_indicators = [
            ind for ind in required_indicators if ind not in current_values
        ]
        if missing_indicators:
            logger.info(f"Missing indicators: {missing_indicators}")
            return None

        close = current_values["close"]
        current_bb_lower = current_values["bb_lower"]
        current_bb_upper = current_values["bb_upper"]
        current_bb_middle = current_values["bb_middle"]

        # Check if price is near the lower band
        near_lower_band = close <= current_bb_lower * 1.01

        # Check if price is below the middle band
        below_middle = close < current_bb_middle

        # Check for reversal pattern (price was lower but now moving up)
        if len(df) >= 3:
            prev_close = df.iloc[-2]["close"]
            prev_prev_close = df.iloc[-3]["close"]

            # Price was declining but now showing signs of reversal
            was_declining = prev_close < prev_prev_close
            now_reversing = close > prev_close

            reversal_pattern = was_declining and now_reversing
        else:
            reversal_pattern = False

        if near_lower_band and below_middle and reversal_pattern:
            # Calculate stop loss and take profit (mean reversion strategy)
            # Stop loss below lower band
            stop_loss = current_bb_lower * 0.98  # 2% below lower band
            # Take profit at middle band (mean reversion target)
            take_profit = current_bb_middle

            # Create and return Signal object
            return Signal(
                strategy_id="band_fade_reversal",
                symbol=symbol,
                action="buy",
                confidence=0.72,  # Base confidence for band fade reversal
                current_price=close,
                price=close,
                timeframe=timeframe,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata={
                    "bb_lower": current_bb_lower,
                    "bb_middle": current_bb_middle,
                    "bb_upper": current_bb_upper,
                    "distance_from_lower": (close - current_bb_lower)
                    / current_bb_lower,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "target": "middle_band",
                },
            )

        return None
