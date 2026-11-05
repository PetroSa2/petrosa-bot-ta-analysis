"""
Base strategy class for technical analysis strategies.
"""

import logging
import math
from typing import Any, Optional

import pandas as pd

from ta_bot.models.signal import Signal

logger = logging.getLogger(__name__)

# A stop that cannot sit at the strategy's own level is placed this many ATRs from
# the entry: the same 2 x ATR distance SignalEngine._calculate_risk_management uses
# for signals without a stop (petrosa-bot-ta-analysis#375).
ATR_STOP_MULTIPLE = 2.0


class BaseStrategy:
    """
    Base class for all trading strategies.

    Supports runtime configuration management while maintaining
    backward compatibility with existing implementations.
    """

    def __init__(self, config_manager=None):
        """
        Initialize the strategy.

        Args:
            config_manager: Optional StrategyConfigManager for runtime configuration.
                           If None, strategies use hardcoded defaults (backward compatible).
        """
        self.config_manager = config_manager
        self.strategy_id = self.__class__.__name__.lower().replace("strategy", "")

    def analyze(self, df: pd.DataFrame, metadata: dict[str, Any]) -> Signal | None:
        """
        Analyze candles and return a trading signal.

        This method maintains backward compatibility. Strategies can optionally
        use self.config_manager to load runtime configuration if available.

        Args:
            df: DataFrame with OHLCV data
            metadata: Additional metadata (symbol, period, etc.)
                     May include 'config' key with pre-loaded configuration

        Returns:
            Signal object if conditions are met, None otherwise
        """
        raise NotImplementedError("Subclasses must implement analyze method")

    def _get_config(self, metadata: dict[str, Any]) -> dict[str, Any] | None:
        """
        Get configuration for this strategy.

        Checks metadata['config'] first (pre-loaded), then returns None
        if not available. This allows backward compatibility.

        Args:
            metadata: Strategy metadata that may contain config

        Returns:
            Configuration dict or None if not available
        """
        return metadata.get("config")

    def _add_config_to_signal(
        self, signal: Signal, config: dict[str, Any] | None
    ) -> Signal:
        """
        Add configuration metadata to signal for position tracking.

        Args:
            signal: Signal to enhance
            config: Configuration used to generate signal

        Returns:
            Enhanced signal with config metadata
        """
        if config and signal:
            if not signal.metadata:
                signal.metadata = {}

            signal.metadata["strategy_config"] = {
                "version": config.get("version", 1),
                "parameters": config.get("parameters", {}),
                "source": config.get("source", "default"),
                "is_override": config.get("is_override", False),
            }

        return signal

    def _get_current_values(
        self, indicators: dict[str, Any], df: pd.DataFrame
    ) -> dict[str, float]:
        """Get current values of indicators for the latest candle."""
        current_values = {}

        for indicator_name, indicator_series in indicators.items():
            # Handle pandas Series
            if isinstance(indicator_series, pd.Series):
                if not indicator_series.empty and len(indicator_series) > 0:
                    try:
                        current_values[indicator_name] = float(
                            indicator_series.iloc[-1]
                        )
                    except (ValueError, IndexError) as e:
                        logger.debug(
                            f"Failed to get current value for {indicator_name}: {e}"
                        )
                        continue
            # Handle list type
            elif isinstance(indicator_series, list) and len(indicator_series) > 0:
                try:
                    current_values[indicator_name] = float(indicator_series[-1])
                except (ValueError, IndexError) as e:
                    logger.debug(
                        f"Failed to get current value for {indicator_name}: {e}"
                    )
                    continue
            # Handle scalar values
            elif indicator_series is not None:
                try:
                    current_values[indicator_name] = float(indicator_series)
                except (ValueError, TypeError) as e:
                    logger.debug(
                        f"Failed to get current value for {indicator_name}: {e}"
                    )
                    continue

        # Add current price data
        if len(df) > 0:
            try:
                current_values["open"] = float(df["open"].iloc[-1])
                current_values["high"] = float(df["high"].iloc[-1])
                current_values["low"] = float(df["low"].iloc[-1])
                current_values["close"] = float(df["close"].iloc[-1])
                current_values["volume"] = float(df["volume"].iloc[-1])
            except (ValueError, IndexError) as e:
                logger.debug(f"Failed to get current price data: {e}")

        return current_values

    @staticmethod
    def _volatility_stop_distance(current: dict[str, float]) -> float | None:
        """The measured-volatility distance for a stop: ATR_STOP_MULTIPLE x ATR.

        Without a usable ATR, half the Bollinger band width (about two standard
        deviations of the close) is the measured fallback. None when neither exists.
        """
        atr = current.get("atr")
        if atr is not None and math.isfinite(atr) and atr > 0:
            return ATR_STOP_MULTIPLE * atr
        upper, lower = current.get("bb_upper"), current.get("bb_lower")
        if upper is not None and lower is not None:
            half_width = (upper - lower) / 2
            if math.isfinite(half_width) and half_width > 0:
                return half_width
        return None

    @classmethod
    def _protective_stop(
        cls,
        action: str,
        level_stop: float | None,
        entry: float,
        current: dict[str, float],
    ) -> tuple[float | None, str]:
        """The stop to emit, always on the protective side of ``entry`` (#375).

        ``level_stop`` (the strategy's own band, level or average) is kept unchanged
        whenever it is below the entry for a buy or above it for a sell. Otherwise the
        entry has already crossed that level, and the stop is placed a measured
        volatility distance from the entry instead. Returns ``(stop, source)``, where
        source is "level" or "volatility", or ``(None, "none")`` when no valid stop
        exists, in which case the strategy emits no signal.
        """
        if not math.isfinite(entry) or entry <= 0:
            return None, "none"
        if level_stop is not None and math.isfinite(level_stop) and level_stop > 0:
            if (action == "buy" and level_stop < entry) or (
                action == "sell" and level_stop > entry
            ):
                return level_stop, "level"
        distance = cls._volatility_stop_distance(current)
        if distance is None:
            return None, "none"
        stop = entry - distance if action == "buy" else entry + distance
        if not math.isfinite(stop) or stop <= 0:
            return None, "none"
        return stop, "volatility"

    def _get_previous_values(
        self, indicators: dict[str, Any], df: pd.DataFrame
    ) -> dict[str, float]:
        """Get previous values of indicators for the previous candle."""
        previous_values = {}

        for indicator_name, indicator_series in indicators.items():
            # Handle pandas Series
            if isinstance(indicator_series, pd.Series):
                if not indicator_series.empty and len(indicator_series) > 1:
                    try:
                        previous_values[indicator_name] = float(
                            indicator_series.iloc[-2]
                        )
                    except (ValueError, IndexError) as e:
                        logger.debug(
                            f"Failed to get previous value for {indicator_name}: {e}"
                        )
                        continue
            # Handle list type
            elif isinstance(indicator_series, list) and len(indicator_series) > 1:
                try:
                    previous_values[indicator_name] = float(indicator_series[-2])
                except (ValueError, IndexError) as e:
                    logger.debug(
                        f"Failed to get previous value for {indicator_name}: {e}"
                    )
                    continue
            # Handle scalar values (use same value for previous)
            elif indicator_series is not None:
                try:
                    previous_values[indicator_name] = float(indicator_series)
                except (ValueError, TypeError) as e:
                    logger.debug(
                        f"Failed to get previous value for {indicator_name}: {e}"
                    )
                    continue

        # Add previous price data
        if len(df) > 1:
            try:
                previous_values["open"] = float(df["open"].iloc[-2])
                previous_values["high"] = float(df["high"].iloc[-2])
                previous_values["low"] = float(df["low"].iloc[-2])
                previous_values["close"] = float(df["close"].iloc[-2])
                previous_values["volume"] = float(df["volume"].iloc[-2])
            except (ValueError, IndexError) as e:
                logger.debug(f"Failed to get previous price data: {e}")

        return previous_values

    def _check_cross_above(
        self, current: float, previous: float, threshold: float = 0
    ) -> bool:
        """Check if a value crossed above a threshold."""
        return previous <= threshold and current > threshold

    def _check_cross_below(
        self, current: float, previous: float, threshold: float = 0
    ) -> bool:
        """Check if a value crossed below a threshold."""
        return previous >= threshold and current < threshold

    def _check_between(self, value: float, min_val: float, max_val: float) -> bool:
        """Check if a value is between min and max (inclusive)."""
        return min_val <= value <= max_val
