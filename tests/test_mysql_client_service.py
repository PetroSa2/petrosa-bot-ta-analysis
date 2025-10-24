"""
Comprehensive tests for MySQL client service.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from ta_bot.services.mysql_client import MySQLClient


@pytest.fixture
def mock_pymysql_connection():
    """Create a mock pymysql connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_conn.cursor.return_value.__exit__.return_value = None
    return mock_conn, mock_cursor


@pytest.mark.asyncio
class TestMySQLClient:
    """Test suite for MySQLClient."""

    def test_initialization_with_uri(self):
        """Test client initialization with URI."""
        with patch.dict(
            "os.environ",
            {"MYSQL_URI": "mysql+pymysql://user:pass@host:3306/database"},
        ):
            client = MySQLClient(use_data_manager=False)
            assert client.host == "host"
            assert client.port == 3306
            assert client.user == "user"
            assert client.password == "pass"
            assert client.database == "database"

    def test_initialization_with_individual_params(self):
        """Test client initialization with individual parameters."""
        client = MySQLClient(
            host="testhost",
            port=3307,
            user="testuser",
            password="testpass",
            database="testdb",
            use_data_manager=False,
        )

        assert client.host == "testhost"
        assert client.port == 3307
        assert client.user == "testuser"
        assert client.password == "testpass"
        assert client.database == "testdb"

    def test_initialization_with_data_manager(self):
        """Test client initialization with Data Manager enabled."""
        with patch("ta_bot.services.mysql_client.DataManagerClient"):
            client = MySQLClient(use_data_manager=True)
            assert client.use_data_manager is True
            assert client.connection is None

    async def test_connect_with_data_manager(self):
        """Test connecting with Data Manager."""
        with patch("ta_bot.services.mysql_client.DataManagerClient") as mock_dm:
            mock_dm_instance = AsyncMock()
            mock_dm.return_value = mock_dm_instance

            client = MySQLClient(use_data_manager=True)
            await client.connect()

            mock_dm_instance.connect.assert_called_once()

    async def test_connect_with_mysql(self, mock_pymysql_connection):
        """Test connecting directly to MySQL."""
        mock_conn, _ = mock_pymysql_connection

        with patch("pymysql.connect", return_value=mock_conn):
            client = MySQLClient(use_data_manager=False)
            await client.connect()

            assert client.connection is not None

    async def test_disconnect_with_data_manager(self):
        """Test disconnecting with Data Manager."""
        with patch("ta_bot.services.mysql_client.DataManagerClient") as mock_dm:
            mock_dm_instance = AsyncMock()
            mock_dm.return_value = mock_dm_instance

            client = MySQLClient(use_data_manager=True)
            await client.connect()
            await client.disconnect()

            mock_dm_instance.disconnect.assert_called_once()

    async def test_disconnect_with_mysql(self, mock_pymysql_connection):
        """Test disconnecting from MySQL."""
        mock_conn, _ = mock_pymysql_connection

        with patch("pymysql.connect", return_value=mock_conn):
            client = MySQLClient(use_data_manager=False)
            await client.connect()
            await client.disconnect()

            mock_conn.close.assert_called_once()

    async def test_fetch_candles_with_data_manager(self):
        """Test fetching candles via Data Manager."""
        with patch("ta_bot.services.mysql_client.DataManagerClient") as mock_dm:
            mock_dm_instance = AsyncMock()
            mock_df = pd.DataFrame(
                {
                    "timestamp": ["2025-10-24T00:00:00Z"],
                    "open": [50000.0],
                    "high": [51000.0],
                    "low": [49000.0],
                    "close": [50500.0],
                    "volume": [100.5],
                }
            )
            mock_dm_instance.fetch_candles.return_value = mock_df
            mock_dm.return_value = mock_dm_instance

            client = MySQLClient(use_data_manager=True)
            df = await client.fetch_candles("BTCUSDT", "15m", limit=1)

            assert len(df) == 1
            mock_dm_instance.fetch_candles.assert_called_once_with("BTCUSDT", "15m", 1)

    async def test_fetch_candles_with_mysql(self, mock_pymysql_connection):
        """Test fetching candles directly from MySQL."""
        mock_conn, mock_cursor = mock_pymysql_connection
        mock_cursor.fetchall.return_value = [
            {
                "timestamp": "2025-10-24 00:00:00",
                "open": 50000.0,
                "high": 51000.0,
                "low": 49000.0,
                "close": 50500.0,
                "volume": 100.5,
            }
        ]

        with patch("pymysql.connect", return_value=mock_conn):
            client = MySQLClient(use_data_manager=False)
            await client.connect()

            df = await client.fetch_candles("BTCUSDT", "15m", limit=1)

            assert len(df) == 1
            assert df.iloc[0]["close"] == 50500.0

    async def test_fetch_candles_unsupported_period(self, mock_pymysql_connection):
        """Test fetching candles with unsupported period."""
        mock_conn, _ = mock_pymysql_connection

        with patch("pymysql.connect", return_value=mock_conn):
            client = MySQLClient(use_data_manager=False)
            await client.connect()

            df = await client.fetch_candles("BTCUSDT", "invalid_period")

            assert len(df) == 0

    async def test_persist_signal_with_data_manager(self):
        """Test persisting signal via Data Manager."""
        with patch("ta_bot.services.mysql_client.DataManagerClient") as mock_dm:
            mock_dm_instance = AsyncMock()
            mock_dm_instance.persist_signal.return_value = True
            mock_dm.return_value = mock_dm_instance

            client = MySQLClient(use_data_manager=True)
            signal_data = {"symbol": "BTCUSDT", "confidence": 0.85}

            result = await client.persist_signal(signal_data)

            assert result is True
            mock_dm_instance.persist_signal.assert_called_once()

    async def test_persist_signal_with_mysql(self, mock_pymysql_connection):
        """Test persisting signal directly to MySQL."""
        mock_conn, mock_cursor = mock_pymysql_connection

        with patch("pymysql.connect", return_value=mock_conn):
            client = MySQLClient(use_data_manager=False)
            await client.connect()

            signal_data = {
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "confidence": 0.85,
                "timestamp": "2025-10-24T00:00:00Z",
                "metadata": {},
            }

            result = await client.persist_signal(signal_data)

            assert result is True
            mock_cursor.execute.assert_called_once()

    async def test_persist_signals_batch_with_data_manager(self):
        """Test persisting signal batch via Data Manager."""
        with patch("ta_bot.services.mysql_client.DataManagerClient") as mock_dm:
            mock_dm_instance = AsyncMock()
            mock_dm_instance.persist_signals_batch.return_value = True
            mock_dm.return_value = mock_dm_instance

            client = MySQLClient(use_data_manager=True)
            signals = [
                {"symbol": "BTCUSDT", "confidence": 0.85},
                {"symbol": "ETHUSDT", "confidence": 0.90},
            ]

            result = await client.persist_signals_batch(signals)

            assert result is True

    async def test_persist_signals_batch_with_mysql(self, mock_pymysql_connection):
        """Test persisting signal batch directly to MySQL."""
        mock_conn, mock_cursor = mock_pymysql_connection

        with patch("pymysql.connect", return_value=mock_conn):
            client = MySQLClient(use_data_manager=False)
            await client.connect()

            signals = [
                {
                    "symbol": "BTCUSDT",
                    "timeframe": "15m",
                    "confidence": 0.85,
                    "timestamp": "2025-10-24T00:00:00Z",
                    "metadata": {},
                },
                {
                    "symbol": "ETHUSDT",
                    "timeframe": "15m",
                    "confidence": 0.90,
                    "timestamp": "2025-10-24T00:00:00Z",
                    "metadata": {},
                },
            ]

            result = await client.persist_signals_batch(signals)

            assert result is True
            mock_cursor.executemany.assert_called_once()

    async def test_persist_signals_batch_empty(self, mock_pymysql_connection):
        """Test persisting empty signal batch."""
        mock_conn, _ = mock_pymysql_connection

        with patch("pymysql.connect", return_value=mock_conn):
            client = MySQLClient(use_data_manager=False)
            await client.connect()

            result = await client.persist_signals_batch([])

            assert result is True

    def test_deep_sanitize_for_json(self):
        """Test deep sanitization for JSON serialization."""
        client = MySQLClient(use_data_manager=False)

        # Test NaN
        assert client._deep_sanitize_for_json(float("nan")) is None

        # Test Infinity
        assert client._deep_sanitize_for_json(float("inf")) is None

        # Test -Infinity
        assert client._deep_sanitize_for_json(float("-inf")) is None

        # Test nested dict
        result = client._deep_sanitize_for_json(
            {"a": float("nan"), "b": {"c": float("inf")}}
        )
        assert result["a"] is None
        assert result["b"]["c"] is None

        # Test list
        result = client._deep_sanitize_for_json([1, float("nan"), 3])
        assert result == [1, None, 3]
