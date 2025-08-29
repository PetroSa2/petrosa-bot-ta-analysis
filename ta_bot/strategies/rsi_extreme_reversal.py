"""
RSI Extreme Reversal Strategy
Adapted from Quantzed Screenings 08 & 09: RSI extreme levels

Detects extreme RSI conditions that suggest potential mean reversion
opportunities in oversold/overbought markets.
"""

from typing import Any, Dict, Optional

import pandas as pd

from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class RSIExtremeReversalStrategy(BaseStrategy):
    """
    RSI Extreme Reversal Strategy

    Triggers:
        - RSI(2) < 2: Extremely oversold (very rare, high probability reversal)
        - RSI(2) < 25: Oversold condition (more common, good reversal probability)

    Logic from Quantzed:
        - Uses RSI(2) for more sensitive mean reversion signals
        - Extremely low RSI values suggest strong reversal potential
        - Avoids minute timeframes (too noisy)

    Adapted from Quantzed Brazilian market screening strategies.
    """

    def analyze(
        self,
        df: pd.DataFrame,
        metadata: Dict[str, Any],
    ) -> Optional[Signal]:
        """Analyze for RSI extreme reversal signals."""
        if len(df) < 78:  # Need sufficient data as per Quantzed requirement
            return None

        # Extract metadata
        symbol = metadata.get("symbol", "UNKNOWN")
        timeframe = metadata.get("timeframe", "15m")

        # Quantzed restriction: avoid minute timeframes (too noisy)
        if (
            timeframe.endswith("m")
            and timeframe != "15m"
            and timeframe != "30m"
            and timeframe != "60m"
        ):
            # Allow some minute timeframes but avoid very short ones
            if timeframe in ["1m", "3m", "5m"]:
                return None

        # Extract indicators from metadata
        indicators = {
            k: v for k, v in metadata.items() if k not in ["symbol", "timeframe"]
        }

        # Calculate RSI(2) if not provided - key difference from standard RSI(14)
        if "rsi_2" not in indicators:
            # Calculate RSI with 2-period (Quantzed specification)
            close_delta = df["close"].diff()

            # Separate gains and losses
            gains = close_delta.clip(lower=0)
            losses = -1 * close_delta.clip(upper=0)

            # Use exponential moving average as per Quantzed implementation
            avg_gains = gains.ewm(
                com=1, adjust=True, min_periods=2
            ).mean()  # com=1 for 2-period
            avg_losses = losses.ewm(com=1, adjust=True, min_periods=2).mean()

            # Calculate RSI
            rs = avg_gains / avg_losses
            rsi_2 = 100 - (100 / (1 + rs))
            indicators["rsi_2"] = rsi_2

        current = self._get_current_values(indicators, df)

        # Check if we have required indicators
        if "rsi_2" not in current or "close" not in current:
            return None

        rsi_value = current["rsi_2"]
        close = current["close"]

        # Quantzed conditions
        extremely_oversold = rsi_value < 2  # Screening 08: RSI(2) < 2
        oversold = rsi_value < 25  # Screening 09: RSI(2) < 25

        signal_action = None
        signal_strength = None
        base_confidence = 0.65  # Alert-level confidence

        if extremely_oversold:
            # Extremely rare condition - high probability reversal
            signal_action = "buy"
            signal_strength = "extreme"
            base_confidence = 0.82  # Higher confidence for extreme condition

        elif oversold:
            # More common oversold condition
            signal_action = "buy"
            signal_strength = "strong"
            base_confidence = 0.72
        else:
            return None

        # Calculate RSI momentum for additional confidence
        previous = self._get_previous_values(indicators, df)
        rsi_momentum = 0
        if "rsi_2" in previous:
            rsi_momentum = current["rsi_2"] - previous["rsi_2"]

        # Adjust confidence based on RSI momentum
        # If RSI is starting to turn up from extreme levels, higher confidence
        momentum_adjustment = 0
        if rsi_momentum > 0:  # RSI turning up
            momentum_adjustment = min(0.08, rsi_momentum * 0.02)
        elif rsi_momentum < -2:  # RSI still falling fast (reduce confidence)
            momentum_adjustment = -0.05

        final_confidence = max(0.55, min(0.90, base_confidence + momentum_adjustment))

        # Calculate how extreme the RSI reading is
        extremeness = max(0, (25 - rsi_value) / 25) if rsi_value < 25 else 0

        # Prepare metadata for signal
        signal_metadata = {
            "rsi_2": rsi_value,
            "rsi_momentum": rsi_momentum,
            "signal_strength": signal_strength,
            "extremeness": extremeness,
            "threshold_type": "extreme" if extremely_oversold else "oversold",
            "strategy_origin": f"quantzed_screening_{'08' if extremely_oversold else '09'}",
        }

        return Signal(
            strategy_id="rsi_extreme_reversal",
            symbol=symbol,
            action=signal_action,
            confidence=final_confidence,
            current_price=close,
            price=close,
            timeframe=timeframe,
            metadata=signal_metadata,
        )
