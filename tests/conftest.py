"""
Shared pytest fixtures and configuration for TA Bot tests.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture(scope="session")
def sample_candles_data():
    """Create sample OHLCV data for testing across all tests."""
    # Generate sample price data with some trend
    base_price = 50000
    num_candles = 100

    # Create timestamps
    end_time = datetime.now()
    interval = timedelta(minutes=15)
    timestamps = [end_time - interval * i for i in range(num_candles, 0, -1)]

    # Generate price data with some volatility and trend
    np.random.seed(42)  # For reproducible results

    # Create a trend with some volatility
    trend = np.linspace(0, 0.1, num_candles)  # 10% upward trend
    noise = np.random.normal(0, 0.02, num_candles)  # 2% volatility
    price_changes = trend + noise

    # Calculate OHLCV
    prices = [base_price]
    for change in price_changes[1:]:
        prices.append(prices[-1] * (1 + change))

    data = []
    for i, (timestamp, price) in enumerate(zip(timestamps, prices)):
        # Create realistic OHLCV data
        volatility = abs(price_changes[i]) * 2
        high = price * (1 + volatility)
        low = price * (1 - volatility)
        open_price = price * (1 + np.random.normal(0, volatility * 0.5))
        close_price = price
        volume = np.random.uniform(1000, 5000)

        data.append(
            {
                "timestamp": timestamp.isoformat(),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close_price,
                "volume": volume,
            }
        )

    return pd.DataFrame(data)


@pytest.fixture
def mock_nats_message():
    """Create a mock NATS message for testing."""
    return {
        "symbol": "BTCUSDT",
        "period": "15m",
        "candles": [
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "open": 50000.0,
                "high": 50100.0,
                "low": 49900.0,
                "close": 50050.0,
                "volume": 1000.0,
            }
        ],
    }


@pytest.fixture
def mock_signal_data():
    """Create mock signal data for testing."""
    return {
        "symbol": "BTCUSDT",
        "period": "15m",
        "signal": "BUY",
        "confidence": 0.74,
        "strategy": "momentum_pulse",
        "metadata": {
            "rsi": 58.3,
            "macd_hist": 0.0012,
            "adx": 27,
            "ema21": 50025.0,
            "ema50": 49980.0,
            "close": 50050.0,
        },
        "timestamp": "2024-01-01T00:00:00Z",
    }
