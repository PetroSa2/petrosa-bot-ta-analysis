"""
Bollinger Squeeze Alert Strategy
Adapted from Quantzed Screening 02: "BANDAS DE BOLLINGER ESTREITAS"

Detects low volatility periods by identifying when Bollinger Bands
are unusually narrow, signaling potential breakout opportunities.
"""

from typing import Any, Optional

import pandas as pd

from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class BollingerSqueezeAlertStrategy(BaseStrategy):
    """
    Bollinger Squeeze Alert Strategy

    Trigger: Bollinger Bands width below threshold indicating low volatility
    Logic:
        - Calculate BB width: (Upper Band - Lower Band) / Middle Band
        - Signal when width < 0.1 (10% of middle band)
        - Indicates volatility compression before potential breakout

    Adapted from Quantzed Brazilian market screening strategy.
    """

    def analyze(
        self,
        df: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> Signal | None:
        """Analyze for Bollinger Band squeeze conditions."""
        if len(df) < 25:  # Need sufficient data for BB calculation
            return None

        # Extract indicators from metadata
        indicators = {
            k: v for k, v in metadata.items() if k not in ["symbol", "timeframe"]
        }
        symbol = metadata.get("symbol", "UNKNOWN")
        timeframe = metadata.get("timeframe", "15m")

        # Calculate Bollinger Bands if not provided (20-period, 2 std dev)
        if not all(key in indicators for key in ["bb_upper", "bb_lower", "bb_middle"]):
            bb_period = 20
            bb_std = 2.0

            # Calculate Simple Moving Average
            sma = df["close"].rolling(window=bb_period).mean()
            # Calculate standard deviation
            std = df["close"].rolling(window=bb_period).std()

            indicators["bb_upper"] = sma + (bb_std * std)
            indicators["bb_lower"] = sma - (bb_std * std)
            indicators["bb_middle"] = sma

        current = self._get_current_values(indicators, df)

        # Check if we have all required indicators
        required_indicators = ["bb_upper", "bb_lower", "bb_middle", "close"]
        if not all(indicator in current for indicator in required_indicators):
            return None

        # Core Quantzed logic: Calculate squeeze ratio
        upper_band = current["bb_upper"]
        lower_band = current["bb_lower"]
        middle_band = current["bb_middle"]
        close = current["close"]

        if middle_band <= 0:  # Avoid division by zero
            return None

        # Quantzed squeeze calculation: (Upper - Lower) / Middle < 0.1
        squeeze_ratio = (upper_band - lower_band) / middle_band
        squeeze_threshold = 0.1  # 10% threshold from Quantzed

        # Main condition: Bands are squeezed
        is_squeezed = squeeze_ratio < squeeze_threshold

        if not is_squeezed:
            return None

        # Additional context: How tight is the squeeze?
        # Lower ratio = tighter squeeze = higher potential
        squeeze_intensity = max(
            0, (squeeze_threshold - squeeze_ratio) / squeeze_threshold
        )

        # Position relative to bands for additional context
        band_position = (
            (close - lower_band) / (upper_band - lower_band)
            if (upper_band - lower_band) > 0
            else 0.5
        )

        # Base confidence adjusted by squeeze intensity
        base_confidence = 0.65  # Alert signal, not action signal
        intensity_adjustment = squeeze_intensity * 0.15  # Up to 15% boost
        final_confidence = min(0.85, base_confidence + intensity_adjustment)

        # Prepare metadata for signal
        signal_metadata = {
            "bb_upper": upper_band,
            "bb_lower": lower_band,
            "bb_middle": middle_band,
            "squeeze_ratio": squeeze_ratio,
            "squeeze_threshold": squeeze_threshold,
            "squeeze_intensity": squeeze_intensity,
            "band_position": band_position,
            "band_width_pct": squeeze_ratio,
            "strategy_origin": "quantzed_screening_02",
        }

        # This is an alert signal - suggests watching for breakout
        # Action would be determined by subsequent price movement
        return Signal(
            strategy_id="bollinger_squeeze_alert",
            symbol=symbol,
            action="hold",  # Alert signal - watch for breakout direction
            confidence=final_confidence,
            current_price=close,
            price=close,
            timeframe=timeframe,
            metadata=signal_metadata,
        )
