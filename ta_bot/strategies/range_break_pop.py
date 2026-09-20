"""
Range Break Pop Strategy
Detects volatility breakout signals when price breaks above a tight range.
"""

from typing import Any, Optional

import pandas as pd

from ta_bot.core.indicators import Indicators
from ta_bot.models.signal import Signal
from ta_bot.strategies.base_strategy import BaseStrategy


class RangeBreakPopStrategy(BaseStrategy):
    """
    Range Break Pop Strategy

    Trigger: Price breaks above recent tight range (10 candles < 2.5% spread)
    Confirmations:
        - ATR(14) falling
        - RSI ~50
        - Breakout volume > 1.5x average
    """

    def __init__(self):
        """Initialize the strategy."""
        super().__init__()
        self.indicators = Indicators()

    def analyze(self, df: pd.DataFrame, metadata: dict[str, Any]) -> Signal | None:
        """Analyze candles for Range Break Pop signals."""
        # Get configuration (pre-loaded or use defaults). #283: resolution
        # order (see SignalEngine._resolve_strategy_config) is symbol
        # override -> global override -> defaults.py -> these hardcoded
        # literals, which are kept identical to defaults.py's values so a
        # missing/failed resolution never changes behavior.
        config = self._get_config(metadata)
        if config:
            params = config.get("parameters", {})
            min_data_points = params.get("min_data_points", 20)
            range_period = params.get("range_period", 10)
            breakout_threshold_pct = params.get("breakout_threshold", 2.5)
            volume_multiplier_threshold = params.get("volume_multiplier_threshold", 1.5)
            base_confidence = params.get("base_confidence", 0.75)
        else:
            # Backward compatibility: use hardcoded defaults
            min_data_points = 20
            range_period = 10
            breakout_threshold_pct = 2.5
            volume_multiplier_threshold = 1.5
            base_confidence = 0.75

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
        previous_values = self._get_previous_values(indicators, df)

        # Check if we have all required indicators (per issue #282 AC-A:
        # rsi is required again since the RSI ~50 gate is restored)
        required_indicators = ["atr", "rsi", "close", "high", "low", "volume"]
        if not all(indicator in current_values for indicator in required_indicators):
            return None

        close = current_values["close"]
        current_atr = current_values["atr"]
        current_rsi = current_values["rsi"]
        volume = current_values["volume"]
        previous_atr = previous_values.get("atr", current_atr)

        # Tight-range precondition: last `range_period` candles (excluding
        # current) must be within a `breakout_threshold_pct`% spread.
        # Restored per issue #282 (the loosened version dropped this
        # precondition entirely); made configurable per #283.
        recent_high = df["high"].iloc[-(range_period + 1) : -1].max()
        recent_low = df["low"].iloc[-(range_period + 1) : -1].min()

        # A zero/negative low makes the spread percentage undefined -- skip
        # signal generation instead of dividing by zero (see #302).
        if recent_low <= 0:
            return None
        range_spread = (recent_high - recent_low) / recent_low * 100

        if range_spread >= breakout_threshold_pct:
            return None

        # Trigger: current close breaks above the recent tight range
        breakout_trigger = close > recent_high
        if not breakout_trigger:
            return None

        # Confirmations (all restored to hard gates per issue #282)
        atr_falling = current_atr < previous_atr
        rsi_ok = 45 <= current_rsi <= 55

        avg_volume = df["volume"].iloc[-(range_period + 1) : -1].mean()
        volume_ratio = volume / avg_volume if avg_volume > 0 else 0.0
        volume_ok = volume_ratio > volume_multiplier_threshold

        if not (atr_falling and rsi_ok and volume_ok):
            return None

        # Calculate stop loss and take profit (breakout strategy)
        # Stop loss below the recent range low
        stop_loss = recent_low * 0.99  # 1% below range low
        risk = abs(close - stop_loss)
        take_profit = close + (risk * 2.0)  # 2:1 R:R for range breakouts

        # Create Signal object
        signal = Signal(
            strategy_id="range_break_pop",
            symbol=symbol,
            action="buy",
            confidence=base_confidence,  # Restored per issue #282 (was loosened to 0.68)
            current_price=close,
            price=close,
            timeframe=timeframe,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata={
                "atr": current_atr,
                "rsi": current_rsi,
                "range_spread": range_spread,
                "recent_high": recent_high,
                "volume_ratio": volume_ratio,
                "atr_falling": atr_falling,
                "rsi_neutral": rsi_ok,
                "volume_breakout": volume_ok,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk_reward_ratio": 2.0,
            },
        )

        # Add configuration metadata to signal for position tracking
        return self._add_config_to_signal(signal, config)
