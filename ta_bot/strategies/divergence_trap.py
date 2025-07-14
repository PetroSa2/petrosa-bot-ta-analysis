"""
Divergence Trap Strategy
Detects hidden bullish divergence signals when RSI shows hidden bullish divergence.
"""

from typing import Dict, Any, Optional
import pandas as pd
from ta_bot.models.signal import SignalType
from ta_bot.strategies.base_strategy import BaseStrategy


class DivergenceTrapStrategy(BaseStrategy):
    """
    Divergence Trap Strategy

    Trigger: RSI hidden bullish divergence (Price HL, RSI LL)
    Confirmations:
        - Price > EMA50
        - MACD Histogram turning up
    """

    def analyze(
        self, df: pd.DataFrame, indicators: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Analyze for divergence trap signals."""
        if len(df) < 20:
            return None

        current = self._get_current_values(indicators, df)
        previous = self._get_previous_values(indicators, df)

        # Check if we have all required indicators
        required_indicators = ["rsi", "ema50", "macd_hist", "close"]
        if not all(indicator in current for indicator in required_indicators):
            return None

        # Trigger: RSI hidden bullish divergence
        # Look for price making higher lows while RSI makes lower lows
        divergence_detected = self._detect_hidden_bullish_divergence(df, indicators)

        if not divergence_detected:
            return None

        # Confirmations
        confirmations = []

        # Price > EMA50
        price_above_ema50 = current["close"] > current["ema50"]
        confirmations.append(("price_above_ema50", price_above_ema50))

        # MACD Histogram turning up
        macd_turning_up = current["macd_hist"] > previous["macd_hist"]
        confirmations.append(("macd_turning_up", macd_turning_up))

        # Check if all confirmations are met
        all_confirmations = all(confirmation[1] for confirmation in confirmations)

        if not all_confirmations:
            return None

        # Calculate trend percent for confidence
        trend_percent = self._calculate_trend_percent(df)

        # Calculate lower wick strength
        lower_wick = self._calculate_lower_wick_strength(df)

        # Prepare metadata
        metadata = {
            "rsi": current["rsi"],
            "ema50": current["ema50"],
            "macd_hist": current["macd_hist"],
            "close": current["close"],
            "trend_percent": trend_percent,
            "lower_wick": lower_wick,
            "confirmations": dict(confirmations),
        }

        return {"signal_type": SignalType.BUY, "metadata": metadata}

    def _detect_hidden_bullish_divergence(
        self, df: pd.DataFrame, indicators: Dict[str, Any]
    ) -> bool:
        """Detect hidden bullish divergence (Price HL, RSI LL)."""
        # Look for the last 10-15 candles for divergence patterns
        lookback = min(15, len(df) - 1)

        # Find local lows in price and RSI
        price_lows = []
        rsi_lows = []

        for i in range(lookback - 5, lookback):
            if i < 2 or i >= len(df) - 2:
                continue

            # Check if this is a local low in price
            if (
                df["low"].iloc[i] < df["low"].iloc[i - 1]
                and df["low"].iloc[i] < df["low"].iloc[i + 1]
            ):
                price_lows.append((i, df["low"].iloc[i]))

            # Check if this is a local low in RSI
            rsi_series = indicators["rsi"]
            if (
                rsi_series.iloc[i] < rsi_series.iloc[i - 1]
                and rsi_series.iloc[i] < rsi_series.iloc[i + 1]
            ):
                rsi_lows.append((i, rsi_series.iloc[i]))

        # Need at least 2 lows in each series
        if len(price_lows) < 2 or len(rsi_lows) < 2:
            return False

        # Check for hidden bullish divergence
        # Price makes lower low, but RSI makes higher low
        price_lower_low = current_low < previous_low
        rsi_higher_low = current_rsi > previous_rsi

        if price_lower_low and rsi_higher_low:
            # Calculate divergence strength
            price_change = (current_low - previous_low) / previous_low
            rsi_change = (current_rsi - previous_rsi) / previous_rsi

            # Strong divergence if RSI change is significant
            strong_divergence = abs(rsi_change) > 0.1  # 10% RSI change

            if strong_divergence:
                return Signal(
                    symbol=metadata.get("symbol", "UNKNOWN"),
                    period=metadata.get("period", "15m"),
                    signal_type=SignalType.BUY,
                    strategy="divergence_trap",
                    confidence=0.7,
                    metadata={
                        "rsi": current_rsi,
                        "price_low": current_low,
                        "divergence_strength": abs(rsi_change),
                        "trend_percent": metadata.get("trend_percent", 0),
                    },
                )

    def _calculate_trend_percent(self, df: pd.DataFrame) -> float:
        """Calculate trend percentage over the last 7 days (assuming 1h candles)."""
        if len(df) < 7 * 24:  # 7 days of hourly candles
            return 0.0

        # Get price 7 days ago and current price
        old_price = df["close"].iloc[-7 * 24]
        current_price = df["close"].iloc[-1]

        return ((current_price - old_price) / old_price) * 100

    def _calculate_lower_wick_strength(self, df: pd.DataFrame) -> float:
        """Calculate the strength of the lower wick of the current candle."""
        if len(df) < 1:
            return 0.0

        current = df.iloc[-1]
        body = abs(current["close"] - current["open"])
        total_range = current["high"] - current["low"]

        if total_range == 0:
            return 0.0

        # Calculate lower wick
        if current["close"] > current["open"]:  # Bullish candle
            lower_wick = current["open"] - current["low"]
        else:  # Bearish candle
            lower_wick = current["close"] - current["low"]

        return lower_wick / total_range
