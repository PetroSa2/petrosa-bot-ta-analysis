"""
Configuration module for the TA Bot.
"""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    """Configuration settings for the TA Bot."""

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
    enabled_strategies: List[str] = field(
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
    candle_periods: List[str] = field(
        default_factory=lambda: os.getenv("SUPPORTED_TIMEFRAMES", "5m").split(",")
    )
    symbols: List[str] = field(
        default_factory=lambda: os.getenv(
            "SUPPORTED_SYMBOLS", "BTCUSDT,ETHUSDT,ADAUSDT"
        ).split(",")
    )

    # Confidence thresholds
    min_confidence: float = 0.6
    max_confidence: float = 0.95

    # Risk management
    max_positions: int = 10
    position_sizes: List[int] = field(default_factory=lambda: [100, 200, 500, 1000])

    # OpenTelemetry Configuration
    otel_service_name: str = os.getenv("OTEL_SERVICE_NAME", "ta-bot")
    otel_service_version: str = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
    otel_exporter_otlp_endpoint: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    enable_metrics: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    enable_traces: bool = os.getenv("ENABLE_TRACES", "true").lower() == "true"
    enable_logs: bool = os.getenv("ENABLE_LOGS", "true").lower() == "true"
