"""
Configuration module for the TA Bot.

This module provides startup configuration loaded from environment variables.
For runtime configuration changes, use the Application Configuration API:
- GET /api/v1/config/application - View current runtime config
- POST /api/v1/config/application - Update runtime config

Runtime configuration changes take effect within 60 seconds (cache TTL) and
apply on the next NATS message processed. Changes are persisted to MongoDB
and tracked in the audit trail.

Startup configuration (this file) is used when:
1. No runtime configuration exists in the database
2. Initializing the application for the first time
3. As fallback if database is unavailable
"""

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """
    Configuration settings for the TA Bot loaded at startup.

    These settings are loaded from environment variables when the application starts.
    Most of these settings can be overridden at runtime via the Application Configuration API.

    Runtime-configurable settings (via API):
    - enabled_strategies: Which trading strategies are active
    - symbols: Which trading pairs to monitor
    - candle_periods: Which timeframes to analyze
    - min_confidence/max_confidence: Signal confidence thresholds
    - max_positions: Maximum concurrent positions
    - position_sizes: Available position sizes

    Startup-only settings (require pod restart):
    - NATS connection settings
    - API endpoints
    - OpenTelemetry settings
    - Logging configuration
    """

    # NATS Configuration
    nats_url: str = os.getenv("NATS_URL", "nats://localhost:4222")
    nats_enabled: bool = os.getenv("NATS_ENABLED", "true").lower() == "true"
    nats_subject_prefix: str = os.getenv("NATS_SUBJECT_PREFIX", "binance.extraction")
    nats_subject_prefix_production: str = os.getenv(
        "NATS_SUBJECT_PREFIX_PRODUCTION", "binance.extraction.production"
    )

    # API Configuration
    # Prefer cluster-provided API_ENDPOINT, fallback to old var for local
    api_endpoint: str = os.getenv(
        "API_ENDPOINT",
        os.getenv("TA_BOT_API_ENDPOINT", "http://localhost:8080/signals"),
    )

    # Signal Publishing Configuration
    # Control whether to publish signals via REST API (disabled by default to prevent duplicates)
    # Signals are always published via NATS when nats_enabled is true
    enable_rest_publishing: bool = (
        os.getenv("ENABLE_REST_PUBLISHING", "false").lower() == "true"
    )

    # Optional settings with defaults
    log_level: str = os.getenv("LOG_LEVEL", os.getenv("TA_BOT_LOG_LEVEL", "INFO"))
    environment: str = os.getenv(
        "ENVIRONMENT", os.getenv("TA_BOT_ENVIRONMENT", "production")
    )
    health_check_interval: int = 30
    max_retries: int = 3
    timeout: int = 30

    # Strategy settings
    enabled_strategies: list[str] = field(
        default_factory=lambda: [
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
    )

    # Technical analysis settings
    candle_periods: list[str] = field(
        default_factory=lambda: os.getenv("SUPPORTED_TIMEFRAMES", "5m").split(",")
    )
    symbols: list[str] = field(
        default_factory=lambda: os.getenv(
            "SUPPORTED_SYMBOLS", "BTCUSDT,ETHUSDT,ADAUSDT"
        ).split(",")
    )

    # Confidence thresholds
    min_confidence: float = 0.6
    max_confidence: float = 0.95

    # Risk management
    max_positions: int = 10
    position_sizes: list[int] = field(default_factory=lambda: [100, 200, 500, 1000])

    # TP/SL Configuration (used when strategies don't define their own)
    # Default stop loss percentage (2% for buy, added for sell)
    default_stop_loss_pct: float = float(os.getenv("DEFAULT_STOP_LOSS_PCT", "0.02"))
    # Default take profit percentage (5% for buy, subtracted for sell)
    default_take_profit_pct: float = float(os.getenv("DEFAULT_TAKE_PROFIT_PCT", "0.05"))
    # ATR multiplier for stop loss (if ATR is available)
    atr_stop_loss_multiplier: float = float(
        os.getenv("ATR_STOP_LOSS_MULTIPLIER", "2.0")
    )
    # ATR multiplier for take profit (if ATR is available)
    atr_take_profit_multiplier: float = float(
        os.getenv("ATR_TAKE_PROFIT_MULTIPLIER", "3.0")
    )

    # OpenTelemetry Configuration
    otel_service_name: str = os.getenv("OTEL_SERVICE_NAME", "ta-bot")
    otel_service_version: str = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
    otel_exporter_otlp_endpoint: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    enable_metrics: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    enable_traces: bool = os.getenv("ENABLE_TRACES", "true").lower() == "true"
    enable_logs: bool = os.getenv("ENABLE_LOGS", "true").lower() == "true"
