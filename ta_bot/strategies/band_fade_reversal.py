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
    """
    Band Fade Reversal strategy implementation.

    Trigger (BUY only, per issue #282 Design Decision 2 -- the lower-band /
    oversold framing is internally consistent and is kept; this strategy
    does NOT flip back to the pre-2025-08 SELL/upper-band variant):
        - Price fades to the lower Bollinger Band and shows an early 2-bar
          reversal off it.
    Confirmations:
        - RSI oversold (<= 30, per defaults.py rsi_oversold)
        - Breakout volume > 1.5x the 10-candle average
    """

    def __init__(self):
        """Initialize the strategy."""
        super().__init__()
        self.indicators = Indicators()

    def analyze(self, df: pd.DataFrame, metadata: dict[str, Any]) -> Signal | None:
        """Analyze candles for Band Fade Reversal signals."""
        # Get configuration (pre-loaded or use defaults). #283: resolution
        # order (see SignalEngine._resolve_strategy_config) is symbol
        # override -> global override -> defaults.py -> these hardcoded
        # literals, which are kept identical to defaults.py's values so a
        # missing/failed resolution never changes behavior.
        config = self._get_config(metadata)
        if config:
            params = config.get("parameters", {})
            min_data_points = params.get("min_data_points", 20)
            rsi_oversold_threshold = params.get("rsi_oversold", 30)
            base_confidence = params.get("base_confidence", 0.72)
        else:
            # Backward compatibility: use hardcoded defaults
            min_data_points = 20
            rsi_oversold_threshold = 30
            base_confidence = 0.72

        if len(df) < min_data_points:
            return None

        # Extract indicators from metadata (now passed directly)
        indicators = {
            k: v
            for k, v in metadata.items()
            if k not in ["symbol", "timeframe", "config"]
        }
        symbol = metadata.get("symbol", "UNKNOWN")
        timeframe = metadata.get("timeframe", "15m")

        # Get current values using base strategy methods
        current_values = self._get_current_values(indicators, df)

        # Debug logging
        logger.info(f"Available indicators: {list(indicators.keys())}")
        logger.info(f"Current values: {list(current_values.keys())}")

        # Check if we have all required indicators. `rsi` is required again
        # per issue #282 -- the RSI oversold gate honours the bound declared
        # in defaults.py (rsi_oversold: 30) that the loosened code never read.
        required_indicators = [
            "bb_lower",
            "bb_upper",
            "bb_middle",
            "rsi",
            "close",
            "volume",
        ]
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
        current_rsi = current_values["rsi"]
        volume = current_values["volume"]

        # Check if price is near the lower band
        near_lower_band = close <= current_bb_lower * 1.01

        # Check if price is below the middle band
        below_middle = close < current_bb_middle

        # RSI oversold confirmation (defaults.py rsi_oversold, #283)
        rsi_oversold = current_rsi <= rsi_oversold_threshold

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

        # Breakout volume confirmation, restored per issue #282. NOTE: the
        # pre-2025-08 code read `metadata.get("volume_ratio", 0) > 1.5`, but
        # `volume_ratio` was never populated by
        # `SignalEngine._calculate_indicators` in any commit (verified via
        # `git log --all -p -- ta_bot/core/signal_engine.py | grep
        # volume_ratio`) -- that gate was dead code that always evaluated to
        # False. Computed directly here instead, same pattern already used
        # by `range_break_pop`.
        avg_volume = df["volume"].iloc[-11:-1].mean()
        volume_ratio = volume / avg_volume if avg_volume > 0 else 0.0
        volume_ok = volume_ratio > 1.5

        if (
            near_lower_band
            and below_middle
            and reversal_pattern
            and rsi_oversold
            and volume_ok
        ):
            # Calculate stop loss and take profit (mean reversion strategy)
            # Stop loss below lower band
            stop_loss = current_bb_lower * 0.98  # 2% below lower band
            # Take profit at middle band (mean reversion target)
            take_profit = current_bb_middle

            # Create Signal object
            signal = Signal(
                strategy_id="band_fade_reversal",
                symbol=symbol,
                action="buy",
                confidence=base_confidence,  # Base confidence for band fade reversal
                current_price=close,
                price=close,
                timeframe=timeframe,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata={
                    "bb_lower": current_bb_lower,
                    "bb_middle": current_bb_middle,
                    "bb_upper": current_bb_upper,
                    "rsi": current_rsi,
                    "volume_ratio": volume_ratio,
                    "distance_from_lower": (close - current_bb_lower)
                    / current_bb_lower,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "target": "middle_band",
                },
            )

            # Add configuration metadata to signal for position tracking
            return self._add_config_to_signal(signal, config)

        return None
