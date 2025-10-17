"""
Liquidity Grab Reversal Strategy
Identifies when price "hunts" stop losses below/above key levels and enters on reversal.
"""

from typing import Any, Dict, Optional

import pandas as pd

from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class LiquidityGrabReversalStrategy(BaseStrategy):
    """
    Liquidity Grab Reversal Strategy

    Trigger: Price approaches key support/resistance, creates wick, then reverses
    Confirmations:
        - Large volume spike with quick rejection (wick formation)
        - Price returns above/below the level within 2-3 candles
        - RSI showing divergence
    """

    def analyze(
        self,
        df: pd.DataFrame,
        metadata: Dict[str, Any],
    ) -> Optional[Signal]:
        """Analyze for liquidity grab reversal signals."""
        if len(df) < 30:
            return None

        # Extract indicators from metadata (now passed directly)
        indicators = {
            k: v for k, v in metadata.items() if k not in ["symbol", "timeframe"]
        }
        symbol = metadata.get("symbol", "UNKNOWN")
        timeframe = metadata.get("timeframe", "15m")

        current = self._get_current_values(indicators, df)

        # Check if we have all required indicators
        required_indicators = ["close", "volume", "rsi"]
        if not all(indicator in current for indicator in required_indicators):
            return None

        # Look for liquidity grab patterns in recent candles
        liquidity_grab_up = self._detect_liquidity_grab_up(df)
        liquidity_grab_down = self._detect_liquidity_grab_down(df)

        if not liquidity_grab_up and not liquidity_grab_down:
            return None

        # Determine signal direction
        if liquidity_grab_up:
            action = "buy"
            confidence = 0.75
            signal_type = "liquidity_grab_bullish"
        else:
            action = "sell"
            confidence = 0.75
            signal_type = "liquidity_grab_bearish"

        # Volume confirmation
        if "volume_sma" in current:
            volume_ratio = current["volume"] / current["volume_sma"]
            if volume_ratio > 2.0:
                confidence += 0.05

        # RSI divergence check - pass RSI series from indicators
        rsi_divergence = self._check_rsi_divergence(df, action, indicators.get("rsi"))
        if rsi_divergence:
            confidence += 0.05

        # Calculate stop loss and take profit (reversal strategy)
        if action == "buy":
            # For bullish liquidity grab - SL below the grabbed level
            support_level = df["low"].iloc[-20:-5].min()
            stop_loss = support_level * 0.995  # 0.5% below support
            risk = abs(current["close"] - stop_loss)
            take_profit = current["close"] + (risk * 2.0)  # 2:1 R:R
        else:
            # For bearish liquidity grab - SL above the grabbed level
            resistance_level = df["high"].iloc[-20:-5].max()
            stop_loss = resistance_level * 1.005  # 0.5% above resistance
            risk = abs(current["close"] - stop_loss)
            take_profit = current["close"] - (risk * 2.0)  # 2:1 R:R

        # Prepare metadata for signal
        signal_metadata = {
            "rsi": current["rsi"],
            "volume_ratio": current.get("volume_sma", 0)
            and current["volume"] / current["volume_sma"],
            "signal_type": signal_type,
            "liquidity_grab": True,
            "rsi_divergence": rsi_divergence,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": 2.0,
        }

        # Create and return Signal object
        return Signal(
            strategy_id="liquidity_grab_reversal",
            symbol=symbol,
            action=action,
            confidence=min(confidence, 0.95),  # Cap at 95%
            current_price=current["close"],
            price=current["close"],
            timeframe=timeframe,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=signal_metadata,
        )

    def _detect_liquidity_grab_up(self, df: pd.DataFrame) -> bool:
        """Detect bullish liquidity grab pattern."""
        if len(df) < 5:
            return False

        # Look for the pattern in the last 5 candles
        recent_candles = df.iloc[-5:]

        # Find potential support level (lowest low in recent history)
        support_level = df["low"].iloc[-20:-5].min()

        # Check if price approached support and created a wick
        for i in range(len(recent_candles) - 2):
            candle = recent_candles.iloc[i]
            next_candle = recent_candles.iloc[i + 1]
            current_candle = recent_candles.iloc[i + 2]

            # Check if price approached support level
            approached_support = candle["low"] <= support_level * 1.005

            # Check for wick formation (long lower shadow)
            wick_ratio = (candle["close"] - candle["low"]) / (
                candle["high"] - candle["low"]
            )
            has_wick = wick_ratio > 0.3 and candle["close"] > candle["open"]

            # Check if price returned above support
            returned_above = (
                next_candle["close"] > support_level
                and current_candle["close"] > support_level
            )

            # Check for volume spike
            volume_spike = candle["volume"] > df["volume"].iloc[-20:-5].mean() * 1.5

            if approached_support and has_wick and returned_above and volume_spike:
                return True

        return False

    def _detect_liquidity_grab_down(self, df: pd.DataFrame) -> bool:
        """Detect bearish liquidity grab pattern."""
        if len(df) < 5:
            return False

        # Look for the pattern in the last 5 candles
        recent_candles = df.iloc[-5:]

        # Find potential resistance level (highest high in recent history)
        resistance_level = df["high"].iloc[-20:-5].max()

        # Check if price approached resistance and created a wick
        for i in range(len(recent_candles) - 2):
            candle = recent_candles.iloc[i]
            next_candle = recent_candles.iloc[i + 1]
            current_candle = recent_candles.iloc[i + 2]

            # Check if price approached resistance level
            approached_resistance = candle["high"] >= resistance_level * 0.995

            # Check for wick formation (long upper shadow)
            wick_ratio = (candle["high"] - candle["close"]) / (
                candle["high"] - candle["low"]
            )
            has_wick = wick_ratio > 0.3 and candle["close"] < candle["open"]

            # Check if price returned below resistance
            returned_below = (
                next_candle["close"] < resistance_level
                and current_candle["close"] < resistance_level
            )

            # Check for volume spike
            volume_spike = candle["volume"] > df["volume"].iloc[-20:-5].mean() * 1.5

            if approached_resistance and has_wick and returned_below and volume_spike:
                return True

        return False

    def _check_rsi_divergence(
        self, df: pd.DataFrame, action: str, rsi_series: Optional[pd.Series] = None
    ) -> bool:
        """Check for RSI divergence."""
        if len(df) < 10:
            return False

        # Check if RSI series is provided
        if rsi_series is None or not isinstance(rsi_series, pd.Series):
            return False

        # Ensure RSI series has enough data
        if len(rsi_series) < 10:
            return False

        # Get RSI values
        rsi_values = rsi_series.iloc[-10:]
        price_values = df["close"].iloc[-10:]

        # Find peaks and troughs
        if action == "buy":
            # Bullish divergence: price makes lower lows, RSI makes higher lows
            price_trend = price_values.iloc[-1] < price_values.iloc[-5]  # Lower low
            rsi_trend = rsi_values.iloc[-1] > rsi_values.iloc[-5]  # Higher low
        else:
            # Bearish divergence: price makes higher highs, RSI makes lower highs
            price_trend = price_values.iloc[-1] > price_values.iloc[-5]  # Higher high
            rsi_trend = rsi_values.iloc[-1] < rsi_values.iloc[-5]  # Lower high

        return price_trend and rsi_trend
