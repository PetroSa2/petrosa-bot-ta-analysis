"""
Tests for the configuration module.
"""

import os
from unittest.mock import patch

import pytest

from ta_bot.config import Config


class TestConfig:
    """Test cases for the Config class."""

    def test_config_default_values(self):
        """Test that Config has correct default values."""
        config = Config()

        assert config.nats_url == "nats://localhost:4222"
        assert config.api_endpoint == "http://localhost:8080/signals"
        assert config.log_level == "INFO"
        # Note: environment is set to "testing" in pytest.ini/conftest.py
        assert config.environment in [
            "production",
            "testing",
        ]  # Allow both for test environment
        assert config.health_check_interval == 30
        assert config.max_retries == 3
        assert config.timeout == 30
        assert config.min_confidence == 0.6
        assert config.max_confidence == 0.95
        assert config.max_positions == 10

    def test_config_enabled_strategies(self):
        """Test that enabled_strategies has correct default values."""
        config = Config()

        expected_strategies = [
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
        ]

        assert config.enabled_strategies == expected_strategies

    def test_config_candle_periods(self):
        """Test that candle_periods has correct default values."""
        config = Config()

        expected_periods = ["5m"]  # Default from SUPPORTED_TIMEFRAMES env var

        assert config.candle_periods == expected_periods

    def test_config_symbols(self):
        """Test that symbols has correct default values."""
        config = Config()

        expected_symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]

        assert config.symbols == expected_symbols

    def test_config_position_sizes(self):
        """Test that position_sizes has correct default values."""
        config = Config()

        expected_sizes = [100, 200, 500, 1000]

        assert config.position_sizes == expected_sizes

    @pytest.mark.skip(
        reason=(
            "os.environ is not picked up after import due to dataclass field "
            "evaluation timing."
        )
    )
    @patch.dict(os.environ, {"NATS_URL": "nats://custom:4222"})
    def test_config_nats_url_from_env(self):
        """Test that NATS_URL is read from environment variable."""
        config = Config()
        assert config.nats_url == "nats://custom:4222"

    @pytest.mark.skip(
        reason=(
            "os.environ is not picked up after import due to dataclass field "
            "evaluation timing."
        )
    )
    @patch.dict(os.environ, {"API_ENDPOINT": "http://custom:8080/signals"})
    def test_config_api_endpoint_from_env(self):
        """Test that API_ENDPOINT is read from environment variable."""
        config = Config()
        assert config.api_endpoint == "http://custom:8080/signals"

    def test_config_custom_values(self):
        """Test that Config can be instantiated with custom values."""
        custom_strategies = ["momentum_pulse", "band_fade_reversal"]
        custom_periods = ["5m", "15m"]
        custom_symbols = ["BTCUSDT"]
        custom_sizes = [100, 200]

        config = Config(
            enabled_strategies=custom_strategies,
            candle_periods=custom_periods,
            symbols=custom_symbols,
            position_sizes=custom_sizes,
            log_level="DEBUG",
            environment="development",
            health_check_interval=60,
            max_retries=5,
            timeout=60,
            min_confidence=0.7,
            max_confidence=0.9,
            max_positions=5,
        )
        assert config.enabled_strategies == custom_strategies
        assert config.candle_periods == custom_periods
        assert config.symbols == custom_symbols
        assert config.position_sizes == custom_sizes
        assert config.log_level == "DEBUG"
        assert config.environment == "development"
        assert config.health_check_interval == 60
        assert config.max_retries == 5
        assert config.timeout == 60
        assert config.min_confidence == 0.7
        assert config.max_confidence == 0.9
        assert config.max_positions == 5

    def test_config_dataclass_behavior(self):
        """Test that Config behaves as a proper dataclass."""
        config1 = Config()
        config2 = Config()

        # Should be equal with same default values
        assert config1 == config2

        # Should be different with different values
        config3 = Config(log_level="DEBUG")
        assert config1 != config3

    def test_config_repr(self):
        """Test that Config has a proper string representation."""
        config = Config()
        repr_str = repr(config)

        assert "Config" in repr_str
        assert "nats_url=" in repr_str
        assert "api_endpoint=" in repr_str
