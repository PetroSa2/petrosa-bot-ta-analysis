"""
Configuration module for the TA Bot.
"""

import os
from dataclasses import dataclass
from typing import List


@dataclass
class Config:
    """Configuration settings for the TA Bot."""
    
    # NATS Configuration
    nats_url: str = os.getenv("NATS_URL", "nats://localhost:4222")
    
    # API Configuration
    api_endpoint: str = os.getenv("API_ENDPOINT", "http://localhost:8080/signals")
    
    # Trading Configuration
    supported_symbols: List[str] = None
    supported_timeframes: List[str] = None
    
    # Technical Analysis Configuration
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    adx_period: int = 14
    bb_period: int = 20
    bb_std: float = 2.0
    ema_periods: List[int] = None
    atr_period: int = 14
    
    def __post_init__(self):
        """Initialize default values after dataclass creation."""
        if self.supported_symbols is None:
            self.supported_symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
        
        if self.supported_timeframes is None:
            self.supported_timeframes = ["15m", "1h"]
        
        if self.ema_periods is None:
            self.ema_periods = [21, 50, 200] 