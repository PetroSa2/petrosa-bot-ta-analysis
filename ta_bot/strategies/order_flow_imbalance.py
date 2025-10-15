"""
Order Flow Imbalance Strategy
Uses volume profile and price action to detect institutional accumulation/distribution.
"""

from typing import Any, Dict, Optional

import pandas as pd

from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class OrderFlowImbalanceStrategy(BaseStrategy):
    """
    Order Flow Imbalance Strategy

    Trigger: Detects institutional accumulation/distribution through volume analysis
    Confirmations:
        - Volume profile showing accumulation/distribution
        - Price holding above/below key levels despite pressure
        - Large volume with small price movement
    """

    def analyze(
        self,
        df: pd.DataFrame,
        metadata: Dict[str, Any],
    ) -> Optional[Signal]:
        """Analyze for order flow imbalance signals."""
        if len(df) < 20:
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

        # Detect accumulation pattern
        accumulation = self._detect_accumulation(df)

        # Detect distribution pattern
        distribution = self._detect_distribution(df)

        if not accumulation and not distribution:
            return None

        # Determine signal direction
        if accumulation:
            action = "buy"
            confidence = 0.75
            signal_type = "order_flow_accumulation"
        else:
            action = "sell"
            confidence = 0.75
            signal_type = "order_flow_distribution"

        # Volume confirmation
        volume_confirmed = self._check_volume_confirmation(current)
        if volume_confirmed:
            confidence += 0.05

        # RSI confirmation
        rsi_confirmed = self._check_rsi_confirmation(current, action)
        if rsi_confirmed:
            confidence += 0.05

        # Prepare metadata for signal
        # Calculate volume ratio safely
        volume_sma = current.get("volume_sma")
        if volume_sma and volume_sma > 0:
            volume_ratio = current["volume"] / volume_sma
        else:
            volume_ratio = None

        signal_metadata = {
            "rsi": current["rsi"],
            "volume_ratio": volume_ratio,
            "signal_type": signal_type,
            "order_flow_imbalance": True,
            "volume_confirmed": volume_confirmed,
            "rsi_confirmed": rsi_confirmed,
        }

        # Create and return Signal object
        return Signal(
            strategy_id="order_flow_imbalance",
            symbol=symbol,
            action=action,
            confidence=min(confidence, 0.95),  # Cap at 95%
            current_price=current["close"],
            price=current["close"],
            timeframe=timeframe,
            metadata=signal_metadata,
        )

    def _detect_accumulation(self, df: pd.DataFrame) -> bool:
        """Detect institutional accumulation pattern."""
        if len(df) < 10:
            return False

        # Look at recent candles for accumulation patterns
        recent_candles = df.iloc[-10:]

        # Check for high volume with small price movement (absorption)
        high_volume_small_move = False
        for i in range(len(recent_candles) - 2):
            candle = recent_candles.iloc[i]

            # High volume
            avg_volume = df["volume"].iloc[-20:-10].mean()
            volume_spike = candle["volume"] > avg_volume * 2

            # Small price movement (absorption)
            price_range = (candle["high"] - candle["low"]) / candle["low"]
            small_move = price_range < 0.02  # Less than 2% range

            # Price holds above support despite selling pressure
            support_level = df["low"].iloc[-20:-10].min()
            holds_support = candle["close"] > support_level

            if volume_spike and small_move and holds_support:
                high_volume_small_move = True
                break

        # Check for increasing volume trend
        volume_trend = self._check_volume_trend_increasing(df)

        # Check for price consolidation
        price_consolidation = self._check_price_consolidation(df)

        return high_volume_small_move and volume_trend and price_consolidation

    def _detect_distribution(self, df: pd.DataFrame) -> bool:
        """Detect institutional distribution pattern."""
        if len(df) < 10:
            return False

        # Look at recent candles for distribution patterns
        recent_candles = df.iloc[-10:]

        # Check for high volume with small price movement (distribution)
        high_volume_small_move = False
        for i in range(len(recent_candles) - 2):
            candle = recent_candles.iloc[i]

            # High volume
            avg_volume = df["volume"].iloc[-20:-10].mean()
            volume_spike = candle["volume"] > avg_volume * 2

            # Small price movement (distribution)
            price_range = (candle["high"] - candle["low"]) / candle["low"]
            small_move = price_range < 0.02  # Less than 2% range

            # Price holds below resistance despite buying pressure
            resistance_level = df["high"].iloc[-20:-10].max()
            holds_resistance = candle["close"] < resistance_level

            if volume_spike and small_move and holds_resistance:
                high_volume_small_move = True
                break

        # Check for decreasing volume trend
        volume_trend = self._check_volume_trend_decreasing(df)

        # Check for price consolidation
        price_consolidation = self._check_price_consolidation(df)

        return high_volume_small_move and volume_trend and price_consolidation

    def _check_volume_trend_increasing(self, df: pd.DataFrame) -> bool:
        """Check if volume trend is increasing."""
        if len(df) < 10:
            return False

        recent_volumes = df["volume"].iloc[-10:]
        # Simple trend: recent volumes > earlier volumes
        recent_avg = recent_volumes.iloc[-5:].mean()
        earlier_avg = recent_volumes.iloc[:5].mean()

        return recent_avg > earlier_avg * 1.2

    def _check_volume_trend_decreasing(self, df: pd.DataFrame) -> bool:
        """Check if volume trend is decreasing."""
        if len(df) < 10:
            return False

        recent_volumes = df["volume"].iloc[-10:]
        # Simple trend: recent volumes < earlier volumes
        recent_avg = recent_volumes.iloc[-5:].mean()
        earlier_avg = recent_volumes.iloc[:5].mean()

        return recent_avg < earlier_avg * 0.8

    def _check_price_consolidation(self, df: pd.DataFrame) -> bool:
        """Check if price is consolidating (sideways movement)."""
        if len(df) < 10:
            return False

        recent_prices = df["close"].iloc[-10:]
        price_range = (recent_prices.max() - recent_prices.min()) / recent_prices.mean()

        # Consolidation: price range less than 3%
        return price_range < 0.03

    def _check_volume_confirmation(self, current: Dict[str, float]) -> bool:
        """Check if volume confirms the order flow pattern."""
        if "volume_sma" not in current:
            return True  # Skip volume check if not available

        volume_ratio = current["volume"] / current["volume_sma"]
        return volume_ratio > 1.5  # Volume 50% above average

    def _check_rsi_confirmation(self, current: Dict[str, float], action: str) -> bool:
        """Check if RSI confirms the order flow pattern."""
        rsi = current["rsi"]

        if action == "buy":
            # For accumulation: RSI not overbought (room to accumulate)
            return rsi < 70
        else:
            # For distribution: RSI not oversold (room to distribute)
            return rsi > 30
