"""
Divergence Trap strategy for technical analysis.
"""

from typing import Any, Optional

import pandas as pd

from ta_bot.core.indicators import Indicators
from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class DivergenceTrapStrategy(BaseStrategy):
    """Divergence Trap strategy implementation."""

    def __init__(self):
        """Initialize the strategy."""
        super().__init__()
        self.indicators = Indicators()

    def _find_recent_lows(self, data: Any, window: int = 10) -> list[float]:
        """Find local-minima swing lows within the most recent `window` values.

        `_find_recent_lows` was referenced by the pre-2025-08-18 divergence
        detection (commit `ada4c964`, carried into `e8751d7c^`) but was never
        defined anywhere in this repo's git history -- verified via
        `git grep -n _find_recent_lows <sha> -- '*.py'` across every commit
        from `35fa6fd` (initial implementation) through `c966c04` (latest
        type-hint modernization). Calling it would have raised
        `AttributeError` had that code path ever executed, so a literal
        revert is not possible.

        This is a from-scratch implementation of the documented intent
        (issue #282, AC-A): distinct swing lows, rather than the fixed
        5-bar-offset index comparison the loosened code used. A point is a
        swing low if it is <= both of its immediate neighbours within the
        window. If fewer than two swing lows are found (e.g. a monotonic
        window), falls back to the lowest point in each half of the window
        so a lower-low comparison remains well-defined.
        """
        if isinstance(data, pd.DataFrame):
            values = data["low"].iloc[-window:].tolist()
        elif isinstance(data, pd.Series):
            values = data.iloc[-window:].tolist()
        else:
            values = list(data[-window:]) if data else []

        if len(values) < 3:
            return values

        lows = [
            values[i]
            for i in range(1, len(values) - 1)
            if values[i] <= values[i - 1] and values[i] <= values[i + 1]
        ]

        if len(lows) < 2:
            mid = len(values) // 2
            first_half = values[:mid] or [values[0]]
            second_half = values[mid:] or [values[-1]]
            lows = [min(first_half), min(second_half)]

        return lows

    def analyze(self, df: pd.DataFrame, metadata: dict[str, Any]) -> Signal | None:
        """Analyze candles for Divergence Trap signals."""
        if len(df) < 30:
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
        required_indicators = ["rsi", "close"]
        if not all(indicator in current_values for indicator in required_indicators):
            return None

        close = current_values["close"]
        current_rsi = current_values["rsi"]

        # Get RSI series for divergence analysis
        rsi = indicators.get("rsi", [])
        # Properly check if RSI series is valid
        if (isinstance(rsi, pd.Series) and (rsi.empty or len(rsi) < 10)) or (
            not isinstance(rsi, pd.Series) and (not rsi or len(rsi) < 10)
        ):
            return None

        # Check for hidden bullish divergence
        # Price making lower lows but RSI making higher lows. Restored per
        # issue #282 AC-A: distinct swing lows via `_find_recent_lows`
        # instead of a fixed 5-bar-offset index comparison (the latter
        # fires on any 5-bar drift and is not divergence detection).
        if len(df) >= 10:
            try:
                recent_lows = self._find_recent_lows(df, 10)
                recent_rsi_lows = self._find_recent_lows(rsi, 10)

                if len(recent_lows) >= 2 and len(recent_rsi_lows) >= 2:
                    price_lower_low = recent_lows[-1] < recent_lows[-2]
                    rsi_higher_low = recent_rsi_lows[-1] > recent_rsi_lows[-2]
                    hidden_bullish_divergence = price_lower_low and rsi_higher_low
                else:
                    hidden_bullish_divergence = False
            except (IndexError, ValueError):
                hidden_bullish_divergence = False
        else:
            hidden_bullish_divergence = False

        # Check for oversold conditions. Design Decision 3 (issue #282):
        # keep `current_rsi < 30` (current behaviour) rather than the
        # `e8751d7c^` form (`rsi_oversold = current_rsi > 30`), which reads
        # as a bug in the original -- this is a deliberate deviation from
        # the pre-`e8751d7c` code, not an oversight.
        oversold = current_rsi < 30

        # Check for price momentum
        if len(df) >= 3:
            prev_close = df.iloc[-2]["close"]
            momentum = close > prev_close
        else:
            momentum = False

        if hidden_bullish_divergence and oversold and momentum:
            # Calculate stop loss and take profit (reversal strategy)
            # Stop loss at recent swing low
            recent_low_window = df["low"].iloc[-10:]
            swing_low = recent_low_window.min()
            stop_loss = swing_low * 0.99  # 1% below swing low
            risk = abs(close - stop_loss)
            take_profit = close + (risk * 2.0)  # 2:1 R:R for divergence reversals

            # Create and return Signal object
            return Signal(
                strategy_id="divergence_trap",
                symbol=symbol,
                action="buy",
                confidence=0.66,  # Base confidence for divergence trap
                current_price=close,
                price=close,
                timeframe=timeframe,
                stop_loss=stop_loss,
                take_profit=take_profit,
                metadata={
                    "rsi": current_rsi,
                    "divergence_type": "hidden_bullish",
                    "oversold": oversold,
                    "momentum": momentum,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "risk_reward_ratio": 2.0,
                },
            )

        return None

    def _calculate_trend_percent(self, df: pd.DataFrame) -> float:
        """Calculate trend percentage based on price movement."""
        if len(df) < 10:
            return 0.0

        # Calculate simple trend percentage
        start_price = df["close"].iloc[-10]
        end_price = df["close"].iloc[-1]

        trend_percent = ((end_price - start_price) / start_price) * 100
        return trend_percent
