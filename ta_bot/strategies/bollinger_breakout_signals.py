"""
Bollinger Breakout Signals Strategy
Adapted from Quantzed Screenings 04 & 05: BB breakout signals

Detects when price breaks outside Bollinger Bands, indicating
potential reversal or continuation opportunities.
"""

from typing import Any, Dict, Optional

import pandas as pd

from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class BollingerBreakoutSignalsStrategy(BaseStrategy):
    """
    Bollinger Breakout Signals Strategy

    Triggers:
        - Buy: Price closes below lower Bollinger Band (oversold)
        - Sell: Price closes above upper Bollinger Band (overbought)

    Logic from Quantzed:
        - Lower breakout suggests mean reversion opportunity
        - Upper breakout suggests momentum or overbought condition

    Adapted from Quantzed Brazilian market screening strategies.
    """

    def analyze(
        self,
        df: pd.DataFrame,
        metadata: Dict[str, Any],
    ) -> Optional[Signal]:
        """Analyze for Bollinger Band breakout signals."""
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

        # Extract values
        close = current["close"]
        upper_band = current["bb_upper"]
        lower_band = current["bb_lower"]
        middle_band = current["bb_middle"]

        # Quantzed Logic 1: Close below lower band (Screening 04)
        below_lower_band = close < lower_band

        # Quantzed Logic 2: Close above upper band (Screening 05)
        above_upper_band = close > upper_band

        signal_action = None
        signal_type = None
        base_confidence = 0.68  # Alert-level confidence from Quantzed

        if below_lower_band:
            # Oversold condition - potential buy signal
            signal_action = "buy"
            signal_type = "lower_band_breakout"

            # Calculate how far below the band (intensity)
            distance_below = (lower_band - close) / lower_band if lower_band > 0 else 0
            intensity_adjustment = min(0.12, distance_below * 50)  # Max 12% boost
            final_confidence = min(0.85, base_confidence + intensity_adjustment)

        elif above_upper_band:
            # Overbought condition - potential sell signal or momentum continuation
            # In crypto, upper band breakouts can indicate strong momentum
            # We'll treat as a caution/sell signal for mean reversion
            signal_action = "sell"
            signal_type = "upper_band_breakout"

            # Calculate how far above the band
            distance_above = (close - upper_band) / upper_band if upper_band > 0 else 0
            intensity_adjustment = min(0.12, distance_above * 50)  # Max 12% boost
            final_confidence = min(0.85, base_confidence + intensity_adjustment)
        else:
            return None

        # Calculate additional context metrics
        band_width = (upper_band - lower_band) / middle_band if middle_band > 0 else 0
        position_in_bands = (
            (close - lower_band) / (upper_band - lower_band)
            if (upper_band - lower_band) > 0
            else 0.5
        )

        # Calculate stop loss and take profit (mean reversion strategy)
        if signal_action == "buy":
            # Buy at lower band - mean revert to middle
            stop_loss = lower_band * 0.98  # 2% below lower band
            take_profit = middle_band  # Target middle band (mean reversion)
        else:
            # Sell at upper band - mean revert to middle
            stop_loss = upper_band * 1.02  # 2% above upper band
            take_profit = middle_band  # Target middle band (mean reversion)

        # Prepare metadata for signal
        signal_metadata = {
            "bb_upper": upper_band,
            "bb_lower": lower_band,
            "bb_middle": middle_band,
            "band_width": band_width,
            "position_in_bands": position_in_bands,
            "breakout_type": signal_type,
            "distance_from_band": abs(
                close - (lower_band if below_lower_band else upper_band)
            )
            / close,
            "strategy_origin": f"quantzed_screening_{'04' if below_lower_band else '05'}",
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "target": "middle_band",
        }

        return Signal(
            strategy_id="bollinger_breakout_signals",
            symbol=symbol,
            action=signal_action,
            confidence=final_confidence,
            current_price=close,
            price=close,
            timeframe=timeframe,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=signal_metadata,
        )
