"""
Comprehensive tests for Data Manager client service.
"""

import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pandas as pd
import pytest

# Mock the data_manager_client module before importing DataManagerClient
sys.modules["data_manager_client"] = Mock()
sys.modules["data_manager_client.exceptions"] = Mock()

from ta_bot.services.data_manager_client import DataManagerClient  # noqa: E402


@pytest.fixture
def mock_base_client():
    """Create a mock base Data Manager client."""
    with patch(
        "ta_bot.services.data_manager_client.BaseDataManagerClient"
    ) as mock_class:
        mock_instance = AsyncMock()
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
async def data_manager_client(mock_base_client):
    """Create a Data Manager client with mocked base client."""
    client = DataManagerClient(
        base_url="http://test-dm:8000",
        timeout=30,
        max_retries=3,
    )
    return client


@pytest.mark.asyncio
class TestDataManagerClient:
    """Test suite for DataManagerClient."""

    async def test_initialization(self):
        """Test client initialization."""
        client = DataManagerClient(
            base_url="http://test:8000",
            timeout=60,
            max_retries=5,
        )

        assert client.base_url == "http://test:8000"
        assert client.timeout == 60
        assert client.max_retries == 5

    async def test_initialization_with_defaults(self):
        """Test client initialization with default values."""
        with patch.dict("os.environ", {"DATA_MANAGER_URL": "http://env-dm:8000"}):
            client = DataManagerClient()
            assert client.base_url == "http://env-dm:8000"
            assert client.timeout == 30
            assert client.max_retries == 3

    async def test_connect_success(self, data_manager_client, mock_base_client):
        """Test successful connection to Data Manager."""
        mock_base_client.health.return_value = {"status": "healthy"}

        await data_manager_client.connect()

        mock_base_client.health.assert_called_once()

    async def test_connect_unhealthy(self, data_manager_client, mock_base_client):
        """Test connection when Data Manager is unhealthy."""
        mock_base_client.health.return_value = {"status": "unhealthy"}

        with pytest.raises(Exception):
            await data_manager_client.connect()

    async def test_disconnect(self, data_manager_client, mock_base_client):
        """Test disconnecting from Data Manager."""
        await data_manager_client.disconnect()
        mock_base_client.close.assert_called_once()

    async def test_fetch_candles_success(self, data_manager_client, mock_base_client):
        """Test successfully fetching candle data."""
        mock_candles = {
            "data": [
                {
                    "timestamp": "2025-10-24T00:00:00Z",
                    "open": 50000.0,
                    "high": 51000.0,
                    "low": 49000.0,
                    "close": 50500.0,
                    "volume": 100.5,
                },
                {
                    "timestamp": "2025-10-24T00:15:00Z",
                    "open": 50500.0,
                    "high": 51500.0,
                    "low": 50000.0,
                    "close": 51000.0,
                    "volume": 150.2,
                },
            ]
        }
        mock_base_client.get_candles.return_value = mock_candles

        df = await data_manager_client.fetch_candles("BTCUSDT", "15m", limit=2)

        assert len(df) == 2
        assert "timestamp" in df.columns
        assert "open" in df.columns
        assert df.iloc[0]["close"] == 50500.0
        mock_base_client.get_candles.assert_called_once_with(
            pair="BTCUSDT",
            period="15m",
            limit=2,
            sort_order="desc",
        )

    async def test_fetch_candles_no_data(self, data_manager_client, mock_base_client):
        """Test fetching candles when no data is returned."""
        mock_base_client.get_candles.return_value = {"data": []}

        df = await data_manager_client.fetch_candles("BTCUSDT", "15m")

        assert len(df) == 0
        assert isinstance(df, pd.DataFrame)

    async def test_fetch_candles_missing_columns(
        self, data_manager_client, mock_base_client
    ):
        """Test fetching candles with missing required columns."""
        mock_candles = {
            "data": [{"timestamp": "2025-10-24T00:00:00Z"}]
        }  # Missing OHLCV
        mock_base_client.get_candles.return_value = mock_candles

        df = await data_manager_client.fetch_candles("BTCUSDT", "15m")

        assert len(df) == 0

    async def test_fetch_candles_api_error(self, data_manager_client, mock_base_client):
        """Test fetching candles with API error."""
        # Create a mock APIError exception
        mock_api_error = Exception("API error")
        mock_api_error.__class__.__name__ = "APIError"

        mock_base_client.get_candles.side_effect = mock_api_error

        df = await data_manager_client.fetch_candles("BTCUSDT", "15m")

        assert len(df) == 0

    async def test_persist_signal_success(self, data_manager_client, mock_base_client):
        """Test successfully persisting a signal."""
        signal_data = {
            "symbol": "BTCUSDT",
            "action": "buy",
            "confidence": 0.85,
        }
        mock_base_client.insert.return_value = {"inserted_count": 1}

        result = await data_manager_client.persist_signal(signal_data)

        assert result is True
        mock_base_client.insert.assert_called_once_with(
            database="mongodb",
            collection="signals",
            data=signal_data,
            validate=True,
        )

    async def test_persist_signal_failure(self, data_manager_client, mock_base_client):
        """Test persisting signal failure."""
        signal_data = {"symbol": "BTCUSDT"}
        mock_base_client.insert.return_value = {"inserted_count": 0}

        result = await data_manager_client.persist_signal(signal_data)

        assert result is False

    async def test_persist_signals_batch_success(
        self, data_manager_client, mock_base_client
    ):
        """Test successfully persisting signal batch."""
        signals = [
            {"symbol": "BTCUSDT", "action": "buy"},
            {"symbol": "ETHUSDT", "action": "sell"},
        ]
        mock_base_client.insert.return_value = {"inserted_count": 2}

        result = await data_manager_client.persist_signals_batch(signals)

        assert result is True

    async def test_persist_signals_batch_empty(
        self, data_manager_client, mock_base_client
    ):
        """Test persisting empty signal batch."""
        result = await data_manager_client.persist_signals_batch([])
        assert result is True

    async def test_persist_signals_batch_partial_success(
        self, data_manager_client, mock_base_client
    ):
        """Test persisting signal batch with partial success."""
        signals = [
            {"symbol": "BTCUSDT"},
            {"symbol": "ETHUSDT"},
        ]
        mock_base_client.insert.return_value = {"inserted_count": 1}  # Only 1 of 2

        result = await data_manager_client.persist_signals_batch(signals)

        assert result is False

    async def test_health_check_success(self, data_manager_client, mock_base_client):
        """Test successful health check."""
        mock_base_client.health.return_value = {"status": "healthy"}

        health = await data_manager_client.health_check()

        assert health["status"] == "healthy"

    async def test_health_check_failure(self, data_manager_client, mock_base_client):
        """Test health check failure."""
        mock_base_client.health.side_effect = Exception("Connection error")

        health = await data_manager_client.health_check()

        assert health["status"] == "unhealthy"
        assert "error" in health

    async def test_async_context_manager(self, mock_base_client):
        """Test using client as async context manager."""
        mock_base_client.health.return_value = {"status": "healthy"}

        async with DataManagerClient() as client:
            assert client is not None

        mock_base_client.health.assert_called_once()
        mock_base_client.close.assert_called_once()
