"""
Validation module for application configuration.

Provides comprehensive validation for all application-level settings
including strategies, symbols, timeframes, confidence, and risk management.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Valid timeframe formats for Binance
VALID_TIMEFRAMES = {
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "6h",
    "8h",
    "12h",
    "1d",
    "3d",
    "1w",
    "1M",
}

# Valid quote currencies for symbols
VALID_QUOTE_CURRENCIES = {"USDT", "BUSD", "BTC", "ETH", "BNB", "USDC"}

# All available strategies (should match SignalEngine.strategies)
AVAILABLE_STRATEGIES = {
    # Original Petrosa strategies
    "momentum_pulse",
    "band_fade_reversal",
    "golden_trend_sync",
    "range_break_pop",
    "divergence_trap",
    "volume_surge_breakout",
    "mean_reversion_scalper",
    "ichimoku_cloud_momentum",
    "liquidity_grab_reversal",
    "multi_timeframe_trend_continuation",
    "order_flow_imbalance",
    # Quantzed-adapted strategies
    "ema_alignment_bullish",
    "bollinger_squeeze_alert",
    "bollinger_breakout_signals",
    "rsi_extreme_reversal",
    "inside_bar_breakout",
    "ema_pullback_continuation",
    "ema_momentum_reversal",
    "fox_trap_reversal",
    "hammer_reversal_pattern",
    # Additional Quantzed-adapted strategies
    "bear_trap_buy",
    "inside_bar_sell",
    "shooting_star_reversal",
    "doji_reversal",
    "ema_alignment_bearish",
    "ema_slope_reversal_sell",
    "minervini_trend_template",
    "bear_trap_sell",
}


def validate_app_config(config: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate complete application configuration.

    Args:
        config: Configuration dictionary containing all app settings

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Validate enabled_strategies
    if "enabled_strategies" in config:
        strategy_errors = validate_enabled_strategies(config["enabled_strategies"])
        errors.extend(strategy_errors)

    # Validate symbols
    if "symbols" in config:
        symbol_errors = validate_symbols(config["symbols"])
        errors.extend(symbol_errors)

    # Validate candle_periods
    if "candle_periods" in config:
        timeframe_errors = validate_candle_periods(config["candle_periods"])
        errors.extend(timeframe_errors)

    # Validate confidence thresholds
    if "min_confidence" in config or "max_confidence" in config:
        min_conf = config.get("min_confidence")
        max_conf = config.get("max_confidence")
        confidence_errors = validate_confidence_thresholds(min_conf, max_conf)
        errors.extend(confidence_errors)

    # Validate risk management
    if "max_positions" in config:
        max_pos_errors = validate_max_positions(config["max_positions"])
        errors.extend(max_pos_errors)

    if "position_sizes" in config:
        pos_size_errors = validate_position_sizes(config["position_sizes"])
        errors.extend(pos_size_errors)

    return len(errors) == 0, errors


def validate_enabled_strategies(strategies: Any) -> list[str]:
    """
    Validate enabled_strategies configuration.

    Args:
        strategies: List of strategy identifiers

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Must be a list
    if not isinstance(strategies, list):
        errors.append("enabled_strategies must be a list")
        return errors

    # Must not be empty
    if len(strategies) == 0:
        errors.append("enabled_strategies must contain at least one strategy")
        return errors

    # Check for duplicates
    if len(strategies) != len(set(strategies)):
        errors.append("enabled_strategies contains duplicate entries")

    # Validate each strategy exists
    for strategy in strategies:
        if not isinstance(strategy, str):
            errors.append(f"Strategy identifier must be a string: {strategy}")
            continue

        if strategy not in AVAILABLE_STRATEGIES:
            errors.append(
                f"Unknown strategy '{strategy}'. Available strategies: {sorted(AVAILABLE_STRATEGIES)}"
            )

    # Warn if list is very short (optional, not blocking)
    if len(strategies) < 3 and len(errors) == 0:
        logger.warning(
            f"Only {len(strategies)} strategies enabled. Consider enabling more for diversification."
        )

    return errors


def validate_symbols(symbols: Any) -> list[str]:
    """
    Validate symbols configuration.

    Args:
        symbols: List of trading symbols

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Must be a list
    if not isinstance(symbols, list):
        errors.append("symbols must be a list")
        return errors

    # Must not be empty
    if len(symbols) == 0:
        errors.append("symbols must contain at least one trading symbol")
        return errors

    # Check for duplicates
    if len(symbols) != len(set(symbols)):
        errors.append("symbols contains duplicate entries")

    # Validate each symbol
    symbol_pattern = re.compile(r"^[A-Z]{2,10}(USDT|BUSD|BTC|ETH|BNB|USDC)$")
    for symbol in symbols:
        if not isinstance(symbol, str):
            errors.append(f"Symbol must be a string: {symbol}")
            continue

        # Check if uppercase
        if symbol != symbol.upper():
            errors.append(f"Symbol must be uppercase: {symbol}")
            continue

        # Check format
        if not symbol_pattern.match(symbol):
            errors.append(
                f"Invalid symbol format '{symbol}'. Expected format: BASEQUOTE (e.g., BTCUSDT, ETHUSDT)"
            )

        # Check length
        if len(symbol) < 6 or len(symbol) > 12:
            errors.append(f"Symbol length must be between 6-12 characters: {symbol}")

    return errors


def validate_candle_periods(periods: Any) -> list[str]:
    """
    Validate candle_periods (timeframes) configuration.

    Args:
        periods: List of timeframe identifiers

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Must be a list
    if not isinstance(periods, list):
        errors.append("candle_periods must be a list")
        return errors

    # Must not be empty
    if len(periods) == 0:
        errors.append("candle_periods must contain at least one timeframe")
        return errors

    # Check for duplicates
    if len(periods) != len(set(periods)):
        errors.append("candle_periods contains duplicate entries")

    # Validate each period
    for period in periods:
        if not isinstance(period, str):
            errors.append(f"Timeframe must be a string: {period}")
            continue

        if period not in VALID_TIMEFRAMES:
            errors.append(
                f"Invalid timeframe '{period}'. Valid timeframes: {sorted(VALID_TIMEFRAMES)}"
            )

    return errors


def validate_confidence_thresholds(
    min_confidence: Any, max_confidence: Any
) -> list[str]:
    """
    Validate confidence threshold configuration.

    Args:
        min_confidence: Minimum confidence value
        max_confidence: Maximum confidence value

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Validate types
    if min_confidence is not None and not isinstance(min_confidence, (int, float)):
        errors.append("min_confidence must be a number")

    if max_confidence is not None and not isinstance(max_confidence, (int, float)):
        errors.append("max_confidence must be a number")

    # If type validation failed, return early
    if errors:
        return errors

    # Validate ranges
    if min_confidence is not None:
        if min_confidence < 0.0 or min_confidence > 1.0:
            errors.append("min_confidence must be between 0.0 and 1.0")

    if max_confidence is not None:
        if max_confidence < 0.0 or max_confidence > 1.0:
            errors.append("max_confidence must be between 0.0 and 1.0")

    # Validate relationship
    if (
        min_confidence is not None
        and max_confidence is not None
        and min_confidence >= max_confidence
    ):
        errors.append("min_confidence must be less than max_confidence")

    return errors


def validate_max_positions(max_positions: Any) -> list[str]:
    """
    Validate max_positions configuration.

    Args:
        max_positions: Maximum number of positions

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Must be an integer
    if not isinstance(max_positions, int):
        errors.append("max_positions must be an integer")
        return errors

    # Must be positive
    if max_positions < 1:
        errors.append("max_positions must be at least 1")

    # Warn if very high
    if max_positions > 100:
        logger.warning(
            f"max_positions is very high ({max_positions}). Consider risk management implications."
        )

    return errors


def validate_position_sizes(position_sizes: Any) -> list[str]:
    """
    Validate position_sizes configuration.

    Args:
        position_sizes: List of available position sizes

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Must be a list
    if not isinstance(position_sizes, list):
        errors.append("position_sizes must be a list")
        return errors

    # Must not be empty
    if len(position_sizes) == 0:
        errors.append("position_sizes must contain at least one size")
        return errors

    # Validate each size
    for size in position_sizes:
        if not isinstance(size, int):
            errors.append(f"Position size must be an integer: {size}")
            continue

        if size <= 0:
            errors.append(f"Position size must be positive: {size}")

    return errors
