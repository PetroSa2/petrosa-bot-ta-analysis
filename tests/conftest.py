"""
Shared pytest fixtures and configuration for TA Bot tests.
"""

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

# Disable OpenTelemetry auto-initialization during tests (must be set first)
os.environ["OTEL_NO_AUTO_INIT"] = "1"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED"] = "false"


def pytest_configure(config):
    """Setup before any tests are run."""
    os.environ["OTEL_NO_AUTO_INIT"] = "1"
    os.environ["OTEL_SDK_DISABLED"] = "true"


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

    volatility = 0.005  # 0.5%
    data = []
    for i, price in enumerate(prices):
        high = price * (1 + volatility)
        low = price * (1 - volatility)
        open_price = price * (1 + np.random.normal(0, volatility * 0.5))
        close_price = price
        volume = np.random.uniform(1000, 5000)

        data.append(
            {
                "timestamp": timestamps[i],
                "open": open_price,
                "high": high,
                "low": low,
                "close": close_price,
                "volume": volume,
            }
        )

    return pd.DataFrame(data)


@pytest.fixture
def mock_signal_engine():
    """Create a mock signal engine."""
    engine = MagicMock()
    return engine


@pytest.fixture
def mock_data_manager_client():
    """Create a mock data manager client."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_nats_listener():
    """Create a mock NATS listener."""
    listener = MagicMock()
    return listener


@pytest.fixture
def mock_mongodb_client():
    """Create a mock MongoDB client."""
    client = MagicMock()
    return client


# Function-level version of sample_candles_data if needed
@pytest.fixture
def candles_df():
    """Generate a sample DataFrame for indicator testing."""
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

    volatility = 0.005  # 0.5%
    data = []
    for i, price in enumerate(prices):
        high = price * (1 + volatility)
        low = price * (1 - volatility)
        open_price = price * (1 + np.random.normal(0, volatility * 0.5))
        close_price = price
        volume = np.random.uniform(1000, 5000)

        data.append(
            {
                "timestamp": timestamps[i],
                "open": open_price,
                "high": high,
                "low": low,
                "close": close_price,
                "volume": volume,
            }
        )

    return pd.DataFrame(data)
