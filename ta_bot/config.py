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
    nats_subject_prefix_production: str = os.getenv("NATS_SUBJECT_PREFIX_PRODUCTION", "binance.extraction.production")

    # API Configuration
    api_endpoint: str = os.getenv("TA_BOT_API_ENDPOINT", "http://localhost:8080/signals")

    # Optional settings with defaults
    log_level: str = os.getenv("TA_BOT_LOG_LEVEL", "INFO")
    environment: str = os.getenv("TA_BOT_ENVIRONMENT", "production")
    health_check_interval: int = 30
    max_retries: int = 3
    timeout: int = 30

    # Strategy settings
    enabled_strategies: List[str] = field(
        default_factory=lambda: [
            "momentum_pulse",
            "band_fade_reversal",
            "golden_trend_sync",
            "range_break_pop",
            "divergence_trap",
        ]
    )

    # Technical analysis settings
    candle_periods: List[str] = field(
        default_factory=lambda: os.getenv("SUPPORTED_TIMEFRAMES", "15m,1h").split(",")
    )
    symbols: List[str] = field(
        default_factory=lambda: os.getenv("SUPPORTED_SYMBOLS", "BTCUSDT,ETHUSDT,ADAUSDT").split(",")
    )

    # Confidence thresholds
    min_confidence: float = 0.6
    max_confidence: float = 0.95

    # Risk management
    max_positions: int = 10
    position_sizes: List[int] = field(default_factory=lambda: [100, 200, 500, 1000])
