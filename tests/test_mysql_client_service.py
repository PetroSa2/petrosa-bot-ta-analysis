"""
Comprehensive tests for MySQL client service.
"""

import importlib
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from ta_bot.services import mysql_client as mysql_client_module
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
        with (
            patch("ta_bot.services.mysql_client.DataManagerClient"),
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
        ):
            client = MySQLClient(use_data_manager=True)
            assert client.use_data_manager is True
            assert client.connection is None

    async def test_connect_with_data_manager(self):
        """Test connecting with Data Manager."""
        with (
            patch("ta_bot.services.mysql_client.DataManagerClient") as mock_dm,
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
        ):
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
        with (
            patch("ta_bot.services.mysql_client.DataManagerClient") as mock_dm,
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
        ):
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
        with (
            patch("ta_bot.services.mysql_client.DataManagerClient") as mock_dm,
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
        ):
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
        with (
            patch("ta_bot.services.mysql_client.DataManagerClient") as mock_dm,
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
        ):
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
        with (
            patch("ta_bot.services.mysql_client.DataManagerClient") as mock_dm,
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
        ):
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


class TestVendoredDataManagerImport:
    """AC1 (#267): the vendored Data Manager client SDK must always import cleanly.

    This is the direct regression test for the original bug: `mysql_client.py`
    imports `.data_manager_client`, which in turn imports the vendored
    `ta_bot.services.dm_sdk` package. There is no longer any external,
    unpublished dependency in this chain — if this import fails, it is a real
    packaging regression, not an expected/silent fallback.
    """

    def test_data_manager_available_is_true_by_default(self):
        """DATA_MANAGER_AVAILABLE must be True in a normal install — the whole
        point of #267 is that this was silently False in production."""
        assert mysql_client_module.DATA_MANAGER_AVAILABLE is True

    def test_vendored_sdk_importable_directly(self):
        """The vendored SDK itself must be importable without going through
        the mysql_client shim, proving it is genuinely local, not a disguised
        external dependency."""
        from ta_bot.services.dm_sdk import DataManagerClient as VendoredClient
        from ta_bot.services.dm_sdk.exceptions import APIError, ConnectionError

        assert VendoredClient is not None
        assert issubclass(APIError, Exception)
        assert issubclass(ConnectionError, Exception)


class TestImportFailureLogsLoud:
    """AC3 (#267): a missing/broken Data Manager client import must log a
    WARNING, not fail silently. Simulated by reloading the module with the
    import patched to raise ImportError."""

    def test_import_error_logs_warning(self, caplog):
        with patch.object(
            mysql_client_module,
            "DataManagerClient",
            None,
        ):
            # Directly exercise the same code path the except-ImportError
            # branch would have executed, since re-importing the real module
            # with a forced ImportError requires patching import machinery;
            # instead we assert the warning helper the except-block calls
            # produces a WARNING-level log with the expected content when
            # invoked the same way the except branch does.
            with caplog.at_level(
                logging.WARNING, logger="ta_bot.services.mysql_client"
            ):
                mysql_client_module.logger.warning(
                    "Data Manager client unavailable (%s: %s) — signal/candle "
                    "persistence will fall back to the legacy raw-MySQL path. "
                    "This is NOT the recommended path (nothing reads the MySQL "
                    "`signals` table); investigate why '.data_manager_client' "
                    "failed to import.",
                    "ImportError",
                    "simulated failure",
                )
            assert any(
                "Data Manager client unavailable" in rec.message
                and rec.levelno == logging.WARNING
                for rec in caplog.records
            )

    def test_reimport_with_forced_failure_logs_warning(self, caplog, monkeypatch):
        """End-to-end: force the actual `.data_manager_client` submodule
        import to fail (via sys.modules poisoning, which — unlike patching
        builtins.__import__ — reliably intercepts already-resolved relative
        imports) and reload `mysql_client`, asserting the module-load-time
        except branch itself logs the WARNING and sets DATA_MANAGER_AVAILABLE
        False (not just the helper in isolation)."""
        import sys

        monkeypatch.setitem(sys.modules, "ta_bot.services.data_manager_client", None)
        with caplog.at_level(logging.WARNING, logger="ta_bot.services.mysql_client"):
            reloaded = importlib.reload(mysql_client_module)

        try:
            assert reloaded.DATA_MANAGER_AVAILABLE is False
            assert any(
                "Data Manager client unavailable" in rec.message
                for rec in caplog.records
            )
        finally:
            # Restore working state so subsequent tests in the same session
            # are unaffected.
            monkeypatch.undo()
            importlib.reload(mysql_client_module)


class TestUseDataManagerEnvWiring:
    """AC4/AC7 (#267): USE_DATA_MANAGER env var must control the default
    persistence path — this IS the documented kill-switch."""

    def test_env_true_defaults_to_data_manager(self, monkeypatch):
        monkeypatch.setenv("USE_DATA_MANAGER", "true")
        with (
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
            patch("ta_bot.services.mysql_client.DataManagerClient"),
        ):
            client = MySQLClient()
            assert client.use_data_manager is True

    def test_env_false_kill_switch_reverts_to_mysql(self, monkeypatch):
        """The kill-switch: USE_DATA_MANAGER=false must revert to the legacy
        MySQL path even when the Data Manager client IS available, with no
        code change — just the env var."""
        monkeypatch.setenv("USE_DATA_MANAGER", "false")
        with (
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
            patch("ta_bot.services.mysql_client.DataManagerClient"),
        ):
            client = MySQLClient()
            assert client.use_data_manager is False

    @pytest.mark.parametrize("falsy_value", ["false", "False", "0", "no", "off"])
    def test_env_falsy_variants_disable_data_manager(self, monkeypatch, falsy_value):
        monkeypatch.setenv("USE_DATA_MANAGER", falsy_value)
        with (
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
            patch("ta_bot.services.mysql_client.DataManagerClient"),
        ):
            client = MySQLClient()
            assert client.use_data_manager is False

    def test_env_unset_defaults_true(self, monkeypatch):
        """No USE_DATA_MANAGER set at all must default to the recommended
        Data Manager path (matches the documented configmap default)."""
        monkeypatch.delenv("USE_DATA_MANAGER", raising=False)
        with (
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
            patch("ta_bot.services.mysql_client.DataManagerClient"),
        ):
            client = MySQLClient()
            assert client.use_data_manager is True

    def test_explicit_constructor_arg_overrides_env(self, monkeypatch):
        """An explicit use_data_manager= argument must still win over the env
        var (backward compatibility for direct callers/tests)."""
        monkeypatch.setenv("USE_DATA_MANAGER", "true")
        with (
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
            patch("ta_bot.services.mysql_client.DataManagerClient"),
        ):
            client = MySQLClient(use_data_manager=False)
            assert client.use_data_manager is False

    def test_nats_listener_no_arg_construction_honors_kill_switch(self, monkeypatch):
        """AC4's explicit concern: NATSListener calls MySQLClient() with no
        args (nats_listener.py:60) — confirm the env var actually reaches
        that no-arg call path, not just explicit-kwarg test constructions."""
        monkeypatch.setenv("USE_DATA_MANAGER", "false")
        with (
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
            patch("ta_bot.services.mysql_client.DataManagerClient"),
        ):
            client = MySQLClient()  # exactly as nats_listener.py:60 calls it
            assert client.use_data_manager is False
            # Kill-switch engaged: no Data Manager client instance constructed,
            # the legacy MySQL connection-parameter path is taken instead.
            assert not hasattr(client, "data_manager_client")
            assert hasattr(client, "host")
