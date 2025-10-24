"""
Comprehensive tests for application configuration validator.
"""

import pytest

from ta_bot.services.app_config_validator import (
    validate_app_config,
    validate_candle_periods,
    validate_confidence_thresholds,
    validate_enabled_strategies,
    validate_max_positions,
    validate_position_sizes,
    validate_symbols,
)


class TestValidateAppConfig:
    """Test suite for validate_app_config function."""

    def test_validate_valid_config(self):
        """Test validating a complete valid configuration."""
        config = {
            "enabled_strategies": ["momentum_pulse", "rsi_extreme_reversal"],
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "candle_periods": ["5m", "15m"],
            "min_confidence": 0.6,
            "max_confidence": 0.95,
            "max_positions": 10,
            "position_sizes": [100, 200, 500],
        }

        is_valid, errors = validate_app_config(config)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_config_with_invalid_strategy(self):
        """Test validating config with invalid strategy."""
        config = {
            "enabled_strategies": ["invalid_strategy"],
            "symbols": ["BTCUSDT"],
            "candle_periods": ["15m"],
        }

        is_valid, errors = validate_app_config(config)
        assert is_valid is False
        assert any("Unknown strategy" in error for error in errors)

    def test_validate_config_with_multiple_errors(self):
        """Test validating config with multiple errors."""
        config = {
            "enabled_strategies": [],  # Empty
            "symbols": ["btcusdt"],  # Lowercase
            "candle_periods": ["invalid"],  # Invalid timeframe
            "min_confidence": 1.5,  # Out of range
            "max_confidence": 0.5,  # Less than min
        }

        is_valid, errors = validate_app_config(config)
        assert is_valid is False
        assert len(errors) > 0


class TestValidateEnabledStrategies:
    """Test suite for validate_enabled_strategies function."""

    def test_validate_valid_strategies(self):
        """Test validating valid strategies."""
        strategies = ["momentum_pulse", "rsi_extreme_reversal"]
        errors = validate_enabled_strategies(strategies)
        assert len(errors) == 0

    def test_validate_empty_strategies(self):
        """Test validating empty strategies list."""
        errors = validate_enabled_strategies([])
        assert len(errors) == 1
        assert "at least one strategy" in errors[0]

    def test_validate_non_list_strategies(self):
        """Test validating non-list strategies."""
        errors = validate_enabled_strategies("not_a_list")
        assert len(errors) == 1
        assert "must be a list" in errors[0]

    def test_validate_duplicate_strategies(self):
        """Test validating duplicate strategies."""
        strategies = ["momentum_pulse", "momentum_pulse"]
        errors = validate_enabled_strategies(strategies)
        assert any("duplicate" in error for error in errors)

    def test_validate_unknown_strategy(self):
        """Test validating unknown strategy."""
        strategies = ["unknown_strategy"]
        errors = validate_enabled_strategies(strategies)
        assert any("Unknown strategy" in error for error in errors)

    def test_validate_non_string_strategy(self):
        """Test validating non-string strategy."""
        strategies = [123, "momentum_pulse"]
        errors = validate_enabled_strategies(strategies)
        assert any("must be a string" in error for error in errors)


class TestValidateSymbols:
    """Test suite for validate_symbols function."""

    def test_validate_valid_symbols(self):
        """Test validating valid symbols."""
        symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
        errors = validate_symbols(symbols)
        assert len(errors) == 0

    def test_validate_empty_symbols(self):
        """Test validating empty symbols list."""
        errors = validate_symbols([])
        assert len(errors) == 1
        assert "at least one trading symbol" in errors[0]

    def test_validate_non_list_symbols(self):
        """Test validating non-list symbols."""
        errors = validate_symbols("not_a_list")
        assert len(errors) == 1
        assert "must be a list" in errors[0]

    def test_validate_lowercase_symbol(self):
        """Test validating lowercase symbol."""
        symbols = ["btcusdt"]
        errors = validate_symbols(symbols)
        assert any("must be uppercase" in error for error in errors)

    def test_validate_invalid_format_symbol(self):
        """Test validating invalid format symbol."""
        symbols = ["BTC"]
        errors = validate_symbols(symbols)
        assert any("Invalid symbol format" in error for error in errors)

    def test_validate_duplicate_symbols(self):
        """Test validating duplicate symbols."""
        symbols = ["BTCUSDT", "BTCUSDT"]
        errors = validate_symbols(symbols)
        assert any("duplicate" in error for error in errors)

    def test_validate_non_string_symbol(self):
        """Test validating non-string symbol."""
        symbols = [123]
        errors = validate_symbols(symbols)
        assert any("must be a string" in error for error in errors)


class TestValidateCandlePeriods:
    """Test suite for validate_candle_periods function."""

    def test_validate_valid_periods(self):
        """Test validating valid timeframes."""
        periods = ["5m", "15m", "1h", "4h"]
        errors = validate_candle_periods(periods)
        assert len(errors) == 0

    def test_validate_empty_periods(self):
        """Test validating empty periods list."""
        errors = validate_candle_periods([])
        assert len(errors) == 1
        assert "at least one timeframe" in errors[0]

    def test_validate_non_list_periods(self):
        """Test validating non-list periods."""
        errors = validate_candle_periods("not_a_list")
        assert len(errors) == 1
        assert "must be a list" in errors[0]

    def test_validate_invalid_period(self):
        """Test validating invalid timeframe."""
        periods = ["5min", "invalid"]
        errors = validate_candle_periods(periods)
        assert any("Invalid timeframe" in error for error in errors)

    def test_validate_duplicate_periods(self):
        """Test validating duplicate periods."""
        periods = ["15m", "15m"]
        errors = validate_candle_periods(periods)
        assert any("duplicate" in error for error in errors)

    def test_validate_non_string_period(self):
        """Test validating non-string period."""
        periods = [15]
        errors = validate_candle_periods(periods)
        assert any("must be a string" in error for error in errors)


class TestValidateConfidenceThresholds:
    """Test suite for validate_confidence_thresholds function."""

    def test_validate_valid_thresholds(self):
        """Test validating valid confidence thresholds."""
        errors = validate_confidence_thresholds(0.6, 0.95)
        assert len(errors) == 0

    def test_validate_min_out_of_range(self):
        """Test validating min confidence out of range."""
        errors = validate_confidence_thresholds(-0.1, 0.95)
        assert any("between 0.0 and 1.0" in error for error in errors)

        errors = validate_confidence_thresholds(1.5, 0.95)
        assert any("between 0.0 and 1.0" in error for error in errors)

    def test_validate_max_out_of_range(self):
        """Test validating max confidence out of range."""
        errors = validate_confidence_thresholds(0.6, -0.1)
        assert any("between 0.0 and 1.0" in error for error in errors)

        errors = validate_confidence_thresholds(0.6, 1.5)
        assert any("between 0.0 and 1.0" in error for error in errors)

    def test_validate_min_greater_than_max(self):
        """Test validating min >= max."""
        errors = validate_confidence_thresholds(0.9, 0.6)
        assert any("must be less than" in error for error in errors)

    def test_validate_min_equals_max(self):
        """Test validating min == max."""
        errors = validate_confidence_thresholds(0.7, 0.7)
        assert any("must be less than" in error for error in errors)

    def test_validate_non_numeric_values(self):
        """Test validating non-numeric confidence values."""
        errors = validate_confidence_thresholds("not_a_number", 0.95)
        assert any("must be a number" in error for error in errors)

        errors = validate_confidence_thresholds(0.6, "not_a_number")
        assert any("must be a number" in error for error in errors)

    def test_validate_none_values(self):
        """Test validating None values."""
        errors = validate_confidence_thresholds(None, None)
        assert len(errors) == 0  # None values are allowed


class TestValidateMaxPositions:
    """Test suite for validate_max_positions function."""

    def test_validate_valid_max_positions(self):
        """Test validating valid max positions."""
        errors = validate_max_positions(10)
        assert len(errors) == 0

    def test_validate_zero_max_positions(self):
        """Test validating zero max positions."""
        errors = validate_max_positions(0)
        assert any("must be at least 1" in error for error in errors)

    def test_validate_negative_max_positions(self):
        """Test validating negative max positions."""
        errors = validate_max_positions(-5)
        assert any("must be at least 1" in error for error in errors)

    def test_validate_non_integer_max_positions(self):
        """Test validating non-integer max positions."""
        errors = validate_max_positions(10.5)
        assert any("must be an integer" in error for error in errors)

        errors = validate_max_positions("10")
        assert any("must be an integer" in error for error in errors)


class TestValidatePositionSizes:
    """Test suite for validate_position_sizes function."""

    def test_validate_valid_position_sizes(self):
        """Test validating valid position sizes."""
        sizes = [100, 200, 500, 1000]
        errors = validate_position_sizes(sizes)
        assert len(errors) == 0

    def test_validate_empty_position_sizes(self):
        """Test validating empty position sizes."""
        errors = validate_position_sizes([])
        assert any("at least one size" in error for error in errors)

    def test_validate_non_list_position_sizes(self):
        """Test validating non-list position sizes."""
        errors = validate_position_sizes("not_a_list")
        assert any("must be a list" in error for error in errors)

    def test_validate_non_integer_position_size(self):
        """Test validating non-integer position size."""
        sizes = [100, 200.5, 500]
        errors = validate_position_sizes(sizes)
        assert any("must be an integer" in error for error in errors)

    def test_validate_negative_position_size(self):
        """Test validating negative position size."""
        sizes = [100, -200, 500]
        errors = validate_position_sizes(sizes)
        assert any("must be positive" in error for error in errors)

    def test_validate_zero_position_size(self):
        """Test validating zero position size."""
        sizes = [100, 0, 500]
        errors = validate_position_sizes(sizes)
        assert any("must be positive" in error for error in errors)
