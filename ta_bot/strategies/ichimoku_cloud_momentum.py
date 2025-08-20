"""
Ichimoku Cloud Momentum Strategy
Uses Ichimoku Cloud for trend identification and momentum.
"""

from typing import Any, Dict, Optional

import pandas as pd

from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class IchimokuCloudMomentumStrategy(BaseStrategy):
    """
    Ichimoku Cloud Momentum Strategy

    Trigger: Price breaks above/below Kumo (cloud) with momentum
    Confirmations:
        - Tenkan-sen crosses above/below Kijun-sen
        - Price > Senkou Span A and B (bullish) or vice versa
        - Volume confirms the breakout
    """

    def analyze(
        self,
        df: pd.DataFrame,
        metadata: Dict[str, Any],
    ) -> Optional[Signal]:
        """Analyze for Ichimoku cloud momentum signals."""
        if len(df) < 52:  # Need at least 52 candles for Ichimoku
            return None

        # Extract indicators from metadata (now passed directly)
        indicators = {
            k: v for k, v in metadata.items() if k not in ["symbol", "timeframe"]
        }
        symbol = metadata.get("symbol", "UNKNOWN")
        timeframe = metadata.get("timeframe", "15m")

        current = self._get_current_values(indicators, df)

        # Check if we have all required indicators
        required_indicators = ["close", "volume"]
        if not all(indicator in current for indicator in required_indicators):
            return None

        # Calculate Ichimoku components
        ichimoku_data = self._calculate_ichimoku(df)
        if ichimoku_data is None:
            return None

        # Extract current and previous Ichimoku values
        current_ichimoku = ichimoku_data.iloc[-1]
        previous_ichimoku = ichimoku_data.iloc[-2]

        # Check for bullish setup
        bullish_signal = self._check_bullish_ichimoku(
            current_ichimoku, previous_ichimoku, current["close"]
        )

        # Check for bearish setup
        bearish_signal = self._check_bearish_ichimoku(
            current_ichimoku, previous_ichimoku, current["close"]
        )

        if not bullish_signal and not bearish_signal:
            return None

        # Determine signal direction and confidence
        if bullish_signal:
            action = "buy"
            confidence = 0.70
            signal_type = "bullish_ichimoku"
        else:
            action = "sell"
            confidence = 0.70
            signal_type = "bearish_ichimoku"

        # Volume confirmation
        if "volume_sma" in current:
            volume_ratio = current["volume"] / current["volume_sma"]
            if volume_ratio > 1.5:
                confidence += 0.05

        # Prepare metadata for signal
        signal_metadata = {
            "tenkan_sen": current_ichimoku["tenkan_sen"],
            "kijun_sen": current_ichimoku["kijun_sen"],
            "senkou_span_a": current_ichimoku["senkou_span_a"],
            "senkou_span_b": current_ichimoku["senkou_span_b"],
            "chikou_span": current_ichimoku["chikou_span"],
            "signal_type": signal_type,
            "ichimoku_momentum": True,
        }

        # Create and return Signal object
        return Signal(
            strategy_id="ichimoku_cloud_momentum",
            symbol=symbol,
            action=action,
            confidence=min(confidence, 0.90),  # Cap at 90%
            current_price=current["close"],
            price=current["close"],
            timeframe=timeframe,
            metadata=signal_metadata,
        )

    def _calculate_ichimoku(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Calculate Ichimoku Cloud components."""
        try:
            # Tenkan-sen (Conversion Line): (9-period high + 9-period low)/2
            high_9 = df["high"].rolling(window=9).max()
            low_9 = df["low"].rolling(window=9).min()
            tenkan_sen = (high_9 + low_9) / 2

            # Kijun-sen (Base Line): (26-period high + 26-period low)/2
            high_26 = df["high"].rolling(window=26).max()
            low_26 = df["low"].rolling(window=26).min()
            kijun_sen = (high_26 + low_26) / 2

            # Senkou Span A (Leading Span A): (Tenkan-sen + Kijun-sen)/2
            senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)

            # Senkou Span B (Leading Span B): (52-period high + 52-period low)/2
            high_52 = df["high"].rolling(window=52).max()
            low_52 = df["low"].rolling(window=52).min()
            senkou_span_b = ((high_52 + low_52) / 2).shift(26)

            # Chikou Span (Lagging Span): Close price shifted back 26 periods
            chikou_span = df["close"].shift(-26)

            # Create DataFrame with all components
            ichimoku_df = pd.DataFrame(
                {
                    "tenkan_sen": tenkan_sen,
                    "kijun_sen": kijun_sen,
                    "senkou_span_a": senkou_span_a,
                    "senkou_span_b": senkou_span_b,
                    "chikou_span": chikou_span,
                }
            )

            return ichimoku_df

        except Exception:
            return None

    def _check_bullish_ichimoku(
        self, current: pd.Series, previous: pd.Series, close: float
    ) -> bool:
        """Check for bullish Ichimoku setup."""
        # Price above cloud
        price_above_cloud = (
            close > current["senkou_span_a"] and close > current["senkou_span_b"]
        )

        # Tenkan-sen crosses above Kijun-sen
        tenkan_cross = (
            current["tenkan_sen"] > current["kijun_sen"]
            and previous["tenkan_sen"] <= previous["kijun_sen"]
        )

        # Cloud is bullish (Senkou Span A > Senkou Span B)
        cloud_bullish = current["senkou_span_a"] > current["senkou_span_b"]

        return price_above_cloud and (tenkan_cross or cloud_bullish)

    def _check_bearish_ichimoku(
        self, current: pd.Series, previous: pd.Series, close: float
    ) -> bool:
        """Check for bearish Ichimoku setup."""
        # Price below cloud
        price_below_cloud = (
            close < current["senkou_span_a"] and close < current["senkou_span_b"]
        )

        # Tenkan-sen crosses below Kijun-sen
        tenkan_cross = (
            current["tenkan_sen"] < current["kijun_sen"]
            and previous["tenkan_sen"] >= previous["kijun_sen"]
        )

        # Cloud is bearish (Senkou Span A < Senkou Span B)
        cloud_bearish = current["senkou_span_a"] < current["senkou_span_b"]

        return price_below_cloud and (tenkan_cross or cloud_bearish)
