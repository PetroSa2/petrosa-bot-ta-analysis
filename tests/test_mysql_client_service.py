"""
Tests for MySQL client service (Data Manager API only).

These tests verify that MySQLClient correctly uses Data Manager API
for all database operations. Direct MySQL connection has been removed.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from ta_bot.services.mysql_client import MySQLClient


@pytest.fixture
def mock_data_manager_client():
    """Create a mock Data Manager client."""
    mock_client = AsyncMock()
    mock_client.connect = AsyncMock()
    mock_client.disconnect = AsyncMock()
    mock_client.fetch_candles = AsyncMock()
    mock_client.persist_signal = AsyncMock()
    mock_client.persist_signals_batch = AsyncMock()
    mock_client._client = AsyncMock()
    mock_client._client.health = AsyncMock(return_value={"status": "healthy"})
    return mock_client


@pytest.mark.asyncio
class TestMySQLClientDataManager:
    """Test suite for MySQLClient with Data Manager enforcement."""

    def test_initialization(self):
        """Test that client always initializes with Data Manager."""
        with patch("ta_bot.services.mysql_client.DataManagerClient"):
            client = MySQLClient()
            assert hasattr(client, "data_manager_client")

    async def test_connect(self, mock_data_manager_client):
        """Test connecting via Data Manager."""
        with patch(
            "ta_bot.services.mysql_client.DataManagerClient",
            return_value=mock_data_manager_client,
        ):
            client = MySQLClient()
            await client.connect()

            mock_data_manager_client.connect.assert_called_once()

    async def test_connect_failure_raises_runtime_error(self, mock_data_manager_client):
        """Test that connection failure raises RuntimeError."""
        mock_data_manager_client.connect.side_effect = Exception("Connection failed")

        with patch(
            "ta_bot.services.mysql_client.DataManagerClient",
            return_value=mock_data_manager_client,
        ):
            client = MySQLClient()

            with pytest.raises(RuntimeError, match="Data Manager connection required"):
                await client.connect()

    async def test_disconnect(self, mock_data_manager_client):
        """Test disconnecting from Data Manager."""
        with patch(
            "ta_bot.services.mysql_client.DataManagerClient",
            return_value=mock_data_manager_client,
        ):
            client = MySQLClient()
            await client.connect()
            await client.disconnect()

            mock_data_manager_client.disconnect.assert_called_once()

    async def test_health_check_healthy(self, mock_data_manager_client):
        """Test health check when Data Manager is healthy."""
        with patch(
            "ta_bot.services.mysql_client.DataManagerClient",
            return_value=mock_data_manager_client,
        ):
            client = MySQLClient()
            result = await client.health_check()

            assert result is True
            mock_data_manager_client._client.health.assert_called_once()

    async def test_health_check_unhealthy(self, mock_data_manager_client):
        """Test health check when Data Manager is unhealthy."""
        mock_data_manager_client._client.health.return_value = {"status": "error"}

        with patch(
            "ta_bot.services.mysql_client.DataManagerClient",
            return_value=mock_data_manager_client,
        ):
            client = MySQLClient()
            result = await client.health_check()

            assert result is False

    async def test_health_check_exception(self, mock_data_manager_client):
        """Test health check when exception occurs."""
        mock_data_manager_client._client.health.side_effect = Exception(
            "Health check failed"
        )

        with patch(
            "ta_bot.services.mysql_client.DataManagerClient",
            return_value=mock_data_manager_client,
        ):
            client = MySQLClient()
            result = await client.health_check()

            assert result is False

    async def test_fetch_candles(self, mock_data_manager_client):
        """Test fetching candles via Data Manager."""
        # Create sample candle data
        expected_df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=5, freq="5min"),
                "open": [100.0, 101.0, 102.0, 103.0, 104.0],
                "high": [101.0, 102.0, 103.0, 104.0, 105.0],
                "low": [99.0, 100.0, 101.0, 102.0, 103.0],
                "close": [101.0, 102.0, 103.0, 104.0, 105.0],
                "volume": [1000.0, 1100.0, 1200.0, 1300.0, 1400.0],
            }
        )

        mock_data_manager_client.fetch_candles.return_value = expected_df

        with patch(
            "ta_bot.services.mysql_client.DataManagerClient",
            return_value=mock_data_manager_client,
        ):
            client = MySQLClient()
            df = await client.fetch_candles("BTCUSDT", "5m", limit=100)

            assert not df.empty
            assert len(df) == 5
            mock_data_manager_client.fetch_candles.assert_called_once_with(
                "BTCUSDT", "5m", 100
            )

    async def test_persist_signal(self, mock_data_manager_client):
        """Test persisting a single signal via Data Manager."""
        mock_data_manager_client.persist_signal.return_value = True

        signal_data = {
            "symbol": "BTCUSDT",
            "timeframe": "5m",
            "action": "buy",
            "confidence": 0.85,
            "strategy": "rsi_strategy",
            "metadata": {"rsi": 30},
            "timestamp": "2024-01-01T00:00:00Z",
        }

        with patch(
            "ta_bot.services.mysql_client.DataManagerClient",
            return_value=mock_data_manager_client,
        ):
            client = MySQLClient()
            result = await client.persist_signal(signal_data)

            assert result is True
            mock_data_manager_client.persist_signal.assert_called_once_with(signal_data)

    async def test_persist_signals_batch(self, mock_data_manager_client):
        """Test persisting multiple signals via Data Manager."""
        mock_data_manager_client.persist_signals_batch.return_value = True

        signals = [
            {
                "symbol": "BTCUSDT",
                "timeframe": "5m",
                "action": "buy",
                "confidence": 0.85,
                "strategy": "rsi_strategy",
                "metadata": {},
                "timestamp": "2024-01-01T00:00:00Z",
            },
            {
                "symbol": "ETHUSDT",
                "timeframe": "15m",
                "action": "sell",
                "confidence": 0.75,
                "strategy": "macd_strategy",
                "metadata": {},
                "timestamp": "2024-01-01T00:00:00Z",
            },
        ]

        with patch(
            "ta_bot.services.mysql_client.DataManagerClient",
            return_value=mock_data_manager_client,
        ):
            client = MySQLClient()
            result = await client.persist_signals_batch(signals)

            assert result is True
            mock_data_manager_client.persist_signals_batch.assert_called_once_with(
                signals
            )


@pytest.mark.asyncio
class TestMySQLClientFailFast:
    """Test suite for fail-fast behavior when Data Manager is unavailable."""

    async def test_connect_fails_when_data_manager_unavailable(self):
        """Test that connect fails fast when Data Manager is unavailable."""
        mock_dm = AsyncMock()
        mock_dm.connect.side_effect = ConnectionError("Data Manager not available")

        with patch(
            "ta_bot.services.mysql_client.DataManagerClient", return_value=mock_dm
        ):
            client = MySQLClient()

            with pytest.raises(RuntimeError, match="Data Manager connection required"):
                await client.connect()

    async def test_health_check_returns_false_on_error(self):
        """Test that health check returns False on error."""
        mock_dm = AsyncMock()
        mock_dm._client.health.side_effect = Exception("Health check failed")

        with patch(
            "ta_bot.services.mysql_client.DataManagerClient", return_value=mock_dm
        ):
            client = MySQLClient()
            result = await client.health_check()

            assert result is False
