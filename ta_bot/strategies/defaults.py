"""
Strategy default parameters registry.

This module contains all default parameter values for each strategy.
These defaults are used when no database configuration exists and are
automatically persisted to MongoDB on first use.
"""

from typing import Any

# =============================================================================
# STRATEGY DEFAULT PARAMETERS
# =============================================================================

STRATEGY_DEFAULTS: dict[str, dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # Quantzed-Adapted Strategies
    # -------------------------------------------------------------------------
    "rsi_extreme_reversal": {
        "rsi_period": 2,
        "oversold_threshold": 25,
        "extreme_threshold": 2,
        "min_data_points": 78,
        "base_confidence": 0.65,
        "extreme_confidence": 0.82,
        "oversold_confidence": 0.72,
        "momentum_adjustment_factor": 0.02,
        "momentum_threshold": -2,
        "momentum_boost": 0.08,
        "momentum_penalty": -0.05,
    },
    "bollinger_squeeze_alert": {
        "bb_period": 20,
        "bb_std": 2.0,
        "squeeze_threshold": 0.1,
        "min_data_points": 25,
        "base_confidence": 0.70,
        "strong_squeeze_threshold": 0.05,
        "strong_confidence": 0.80,
    },
    "ema_alignment_bullish": {
        "ema_fast": 8,
        "ema_medium": 21,
        "ema_slow": 55,
        "min_data_points": 60,
        "base_confidence": 0.75,
        "volume_multiplier_threshold": 1.5,
        "volume_confidence_boost": 0.10,
    },
    "ema_alignment_bearish": {
        "ema_fast": 8,
        "ema_medium": 21,
        "ema_slow": 55,
        "min_data_points": 60,
        "base_confidence": 0.75,
        "volume_multiplier_threshold": 1.5,
        "volume_confidence_boost": 0.10,
    },
    "bollinger_breakout_signals": {
        "bb_period": 20,
        "bb_std": 2.0,
        "volume_multiplier_threshold": 1.5,
        "min_data_points": 25,
        "base_confidence": 0.72,
        "strong_volume_confidence_boost": 0.10,
    },
    "inside_bar_breakout": {
        "min_data_points": 3,
        "base_confidence": 0.75,
        "volume_multiplier_threshold": 1.3,
        "volume_confidence_boost": 0.08,
        "pattern_lookback": 2,
    },
    "inside_bar_sell": {
        "min_data_points": 3,
        "base_confidence": 0.75,
        "volume_multiplier_threshold": 1.3,
        "volume_confidence_boost": 0.08,
        "pattern_lookback": 2,
    },
    "ema_pullback_continuation": {
        "ema_period": 21,
        "pullback_threshold": 0.02,
        "min_data_points": 25,
        "base_confidence": 0.73,
        "volume_confirmation_multiplier": 1.2,
    },
    "ema_momentum_reversal": {
        "ema_fast": 12,
        "ema_slow": 26,
        "momentum_threshold": 0.5,
        "min_data_points": 30,
        "base_confidence": 0.70,
        "strong_momentum_threshold": 1.0,
        "strong_confidence": 0.78,
    },
    "ema_slope_reversal_sell": {
        "ema_period": 21,
        "slope_threshold": 0.0,
        "min_data_points": 25,
        "base_confidence": 0.72,
        "steep_slope_threshold": -0.5,
        "steep_confidence_boost": 0.08,
    },
    "fox_trap_reversal": {
        "min_data_points": 10,
        "fake_breakout_threshold": 0.01,
        "reversal_threshold": 0.005,
        "base_confidence": 0.76,
        "volume_multiplier_threshold": 1.5,
    },
    "hammer_reversal_pattern": {
        "min_data_points": 5,
        "body_ratio_threshold": 0.3,
        "lower_shadow_ratio_threshold": 2.0,
        "base_confidence": 0.74,
        "volume_confirmation_multiplier": 1.2,
    },
    "shooting_star_reversal": {
        "min_data_points": 5,
        "body_ratio_threshold": 0.3,
        "upper_shadow_ratio_threshold": 2.0,
        "base_confidence": 0.74,
        "volume_confirmation_multiplier": 1.2,
    },
    "doji_reversal": {
        "min_data_points": 5,
        "body_size_threshold": 0.1,
        "shadow_ratio_threshold": 1.0,
        "base_confidence": 0.68,
        "trend_confirmation_periods": 5,
    },
    "bear_trap_buy": {
        "min_data_points": 10,
        "fake_breakdown_threshold": 0.02,
        "reversal_threshold": 0.01,
        "base_confidence": 0.77,
        "volume_multiplier_threshold": 1.4,
    },
    "bear_trap_sell": {
        "min_data_points": 10,
        "fake_breakout_threshold": 0.02,
        "reversal_threshold": 0.01,
        "base_confidence": 0.77,
        "volume_multiplier_threshold": 1.4,
    },
    "minervini_trend_template": {
        "sma_50_period": 50,
        "sma_150_period": 150,
        "sma_200_period": 200,
        "price_above_sma_50_min": 1.0,
        "price_above_sma_150_min": 1.0,
        "sma_50_above_sma_150_min": 1.0,
        "min_data_points": 210,
        "base_confidence": 0.80,
        "stage_2_uptrend_confidence": 0.85,
    },
    # -------------------------------------------------------------------------
    # Original Petrosa Strategies
    # -------------------------------------------------------------------------
    "momentum_pulse": {
        "rsi_period": 14,
        "rsi_overbought": 70,
        "rsi_oversold": 30,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "min_data_points": 30,
        "base_confidence": 0.72,
    },
    "band_fade_reversal": {
        "bb_period": 20,
        "bb_std": 2.0,
        "rsi_period": 14,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        "min_data_points": 25,
        "base_confidence": 0.70,
    },
    "golden_trend_sync": {
        "ema_fast": 50,
        "ema_slow": 200,
        "min_data_points": 210,
        "base_confidence": 0.78,
        "volume_confirmation_multiplier": 1.3,
    },
    "range_break_pop": {
        "range_period": 20,
        "breakout_threshold": 0.01,
        "volume_multiplier_threshold": 1.5,
        "min_data_points": 25,
        "base_confidence": 0.74,
    },
    "divergence_trap": {
        "rsi_period": 14,
        "price_lookback": 10,
        "divergence_threshold": 0.02,
        "min_data_points": 20,
        "base_confidence": 0.76,
    },
    "volume_surge_breakout": {
        "volume_sma_period": 20,
        "volume_surge_multiplier": 2.0,
        "price_move_threshold": 0.015,
        "min_data_points": 25,
        "base_confidence": 0.73,
    },
    "mean_reversion_scalper": {
        "bb_period": 20,
        "bb_std": 2.0,
        "rsi_period": 7,
        "rsi_oversold": 25,
        "rsi_overbought": 75,
        "min_data_points": 25,
        "base_confidence": 0.68,
    },
    "ichimoku_cloud_momentum": {
        "tenkan_period": 9,
        "kijun_period": 26,
        "senkou_b_period": 52,
        "displacement": 26,
        "min_data_points": 60,
        "base_confidence": 0.75,
    },
    "liquidity_grab_reversal": {
        "volume_spike_multiplier": 2.5,
        "price_rejection_threshold": 0.02,
        "lookback_periods": 10,
        "min_data_points": 15,
        "base_confidence": 0.77,
    },
    "multi_timeframe_trend_continuation": {
        "ema_period": 21,
        "higher_timeframe_multiplier": 4,
        "trend_alignment_threshold": 0.8,
        "min_data_points": 25,
        "base_confidence": 0.76,
    },
    "order_flow_imbalance": {
        "imbalance_threshold": 0.7,
        "volume_window": 10,
        "price_impact_threshold": 0.01,
        "min_data_points": 15,
        "base_confidence": 0.74,
    },
}


# =============================================================================
# PARAMETER SCHEMAS (for validation)
# =============================================================================

PARAMETER_SCHEMAS: dict[str, dict[str, dict[str, Any]]] = {
    "rsi_extreme_reversal": {
        "rsi_period": {
            "type": "int",
            "min": 2,
            "max": 50,
            "description": "RSI calculation period",
        },
        "oversold_threshold": {
            "type": "float",
            "min": 10,
            "max": 40,
            "description": "RSI threshold for oversold condition",
        },
        "extreme_threshold": {
            "type": "float",
            "min": 1,
            "max": 10,
            "description": "RSI threshold for extreme oversold condition",
        },
        "min_data_points": {
            "type": "int",
            "min": 50,
            "max": 200,
            "description": "Minimum required data points",
        },
        "base_confidence": {
            "type": "float",
            "min": 0.5,
            "max": 1.0,
            "description": "Base confidence level",
        },
    },
    # Add schemas for other strategies as needed
}


# =============================================================================
# STRATEGY METADATA
# =============================================================================

STRATEGY_METADATA: dict[str, dict[str, str]] = {
    "rsi_extreme_reversal": {
        "name": "RSI Extreme Reversal",
        "description": "Detects extreme RSI conditions that suggest potential mean reversion opportunities",
        "category": "Quantzed-Adapted",
        "timeframes": "5m, 15m, 30m, 1h",
    },
    "bollinger_squeeze_alert": {
        "name": "Bollinger Squeeze Alert",
        "description": "Identifies low volatility periods when Bollinger Bands are unusually narrow",
        "category": "Quantzed-Adapted",
        "timeframes": "15m, 30m, 1h, 4h",
    },
    "momentum_pulse": {
        "name": "Momentum Pulse",
        "description": "Tracks momentum using RSI and MACD for trend confirmation",
        "category": "Petrosa Original",
        "timeframes": "15m, 1h, 4h",
    },
    # Add metadata for all other strategies
}


def get_strategy_defaults(strategy_id: str) -> dict[str, Any]:
    """
    Get default parameters for a strategy.

    Args:
        strategy_id: Strategy identifier

    Returns:
        Dictionary of default parameters
    """
    return STRATEGY_DEFAULTS.get(strategy_id, {})


def get_parameter_schema(strategy_id: str) -> dict[str, dict[str, Any]]:
    """
    Get parameter schema for a strategy.

    Args:
        strategy_id: Strategy identifier

    Returns:
        Dictionary of parameter schemas
    """
    return PARAMETER_SCHEMAS.get(strategy_id, {})


def get_strategy_metadata(strategy_id: str) -> dict[str, str]:
    """
    Get metadata for a strategy.

    Args:
        strategy_id: Strategy identifier

    Returns:
        Dictionary of strategy metadata
    """
    return STRATEGY_METADATA.get(
        strategy_id,
        {
            "name": strategy_id.replace("_", " ").title(),
            "description": "No description available",
            "category": "Unknown",
            "timeframes": "All",
        },
    )


def list_all_strategies() -> list[str]:
    """Get list of all strategy IDs."""
    return list(STRATEGY_DEFAULTS.keys())


def validate_parameters(
    strategy_id: str, parameters: dict[str, Any]
) -> tuple[bool, list[str]]:
    """
    Validate parameters against schema.

    Args:
        strategy_id: Strategy identifier
        parameters: Parameters to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    schema = get_parameter_schema(strategy_id)
    if not schema:
        # No schema defined, accept all parameters
        return True, []

    errors = []

    for param_name, param_value in parameters.items():
        if param_name not in schema:
            errors.append(f"Unknown parameter: {param_name}")
            continue

        param_schema = schema[param_name]
        param_type = param_schema.get("type")

        # Type validation
        if param_type == "int" and not isinstance(param_value, int):
            errors.append(f"{param_name} must be an integer")
            continue
        elif param_type == "float" and not isinstance(param_value, (int, float)):
            errors.append(f"{param_name} must be a number")
            continue
        elif param_type == "bool" and not isinstance(param_value, bool):
            errors.append(f"{param_name} must be a boolean")
            continue
        elif param_type == "str" and not isinstance(param_value, str):
            errors.append(f"{param_name} must be a string")
            continue

        # Range validation for numeric types
        if param_type in ("int", "float"):
            if "min" in param_schema and param_value < param_schema["min"]:
                errors.append(
                    f"{param_name} must be >= {param_schema['min']}, got {param_value}"
                )
            if "max" in param_schema and param_value > param_schema["max"]:
                errors.append(
                    f"{param_name} must be <= {param_schema['max']}, got {param_value}"
                )

    return len(errors) == 0, errors
