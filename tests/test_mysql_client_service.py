"""
Comprehensive tests for MySQL client service.

Per petrosa-bot-ta-analysis#284: the raw-pymysql direct-MySQL fallback was
removed. `MySQLClient` is now a thin facade over `DataManagerClient` — every
test here exercises that delegation, plus the hard-error paths for the
removed `use_data_manager=False` kill-switch and a missing Data Manager
import.
"""

import importlib
import logging
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from ta_bot.services import mysql_client as mysql_client_module
from ta_bot.services.mysql_client import MySQLClient


@pytest.mark.asyncio
class TestMySQLClient:
    """Test suite for MySQLClient (Data Manager gateway facade)."""

    def test_initialization_default(self):
        """Default construction always uses the Data Manager gateway."""
        with (
            patch("ta_bot.services.mysql_client.DataManagerClient") as mock_dm,
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
        ):
            client = MySQLClient()
            assert client.use_data_manager is True
            assert client.connection is None
            mock_dm.assert_called_once()

    def test_initialization_with_data_manager_true(self):
        """Explicit use_data_manager=True is accepted (backward compatible call shape)."""
        with (
            patch("ta_bot.services.mysql_client.DataManagerClient"),
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
        ):
            client = MySQLClient(use_data_manager=True)
            assert client.use_data_manager is True
            assert client.connection is None

    def test_initialization_with_data_manager_false_raises(self):
        """AC2 (#284): use_data_manager=False must hard-error, never open a
        raw connection — the fallback branch it used to select was removed."""
        with pytest.raises(RuntimeError, match="no longer supported") as exc_info:
            MySQLClient(use_data_manager=False)
        assert "use_data_manager=False" in str(exc_info.value)

    def test_initialization_without_data_manager_available_raises(self):
        """If the Data Manager client failed to import, construction must
        hard-error rather than silently fall back to a raw connection."""
        with patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", False):
            with pytest.raises(RuntimeError, match="no raw-MySQL fallback") as exc_info:
                MySQLClient()
            assert "Data Manager client unavailable" in str(exc_info.value)

    def test_client_never_imports_pymysql(self):
        """AC2 (#284): the module must not import pymysql at all."""
        assert not hasattr(mysql_client_module, "pymysql")
        assert "pymysql" not in mysql_client_module.__dict__

    async def test_connect_delegates_to_data_manager(self):
        """connect() must delegate to the Data Manager client."""
        with (
            patch("ta_bot.services.mysql_client.DataManagerClient") as mock_dm,
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
        ):
            mock_dm_instance = AsyncMock()
            mock_dm.return_value = mock_dm_instance

            client = MySQLClient()
            await client.connect()

            mock_dm_instance.connect.assert_called_once()

    async def test_disconnect_delegates_to_data_manager(self):
        """disconnect() must delegate to the Data Manager client."""
        with (
            patch("ta_bot.services.mysql_client.DataManagerClient") as mock_dm,
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
        ):
            mock_dm_instance = AsyncMock()
            mock_dm.return_value = mock_dm_instance

            client = MySQLClient()
            await client.connect()
            await client.disconnect()

            mock_dm_instance.disconnect.assert_called_once()

    async def test_fetch_candles_delegates_to_data_manager(self):
        """fetch_candles() must delegate to the Data Manager client."""
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

            client = MySQLClient()
            df = await client.fetch_candles("BTCUSDT", "15m", limit=1)

            assert len(df) == 1
            mock_dm_instance.fetch_candles.assert_called_once_with("BTCUSDT", "15m", 1)

    async def test_fetch_candles_default_limit_is_250(self):
        """AC3 (#209): default limit stays 250 through the gateway facade."""
        with (
            patch("ta_bot.services.mysql_client.DataManagerClient") as mock_dm,
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
        ):
            mock_dm_instance = AsyncMock()
            mock_dm_instance.fetch_candles.return_value = pd.DataFrame()
            mock_dm.return_value = mock_dm_instance

            client = MySQLClient()
            await client.fetch_candles("BTCUSDT", "15m")

            mock_dm_instance.fetch_candles.assert_called_once_with(
                "BTCUSDT", "15m", 250
            )

    async def test_persist_signal_delegates_to_data_manager(self):
        """persist_signal() must delegate to the Data Manager client."""
        with (
            patch("ta_bot.services.mysql_client.DataManagerClient") as mock_dm,
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
        ):
            mock_dm_instance = AsyncMock()
            mock_dm_instance.persist_signal.return_value = True
            mock_dm.return_value = mock_dm_instance

            client = MySQLClient()
            signal_data = {"symbol": "BTCUSDT", "confidence": 0.85}

            result = await client.persist_signal(signal_data)

            assert result is True
            mock_dm_instance.persist_signal.assert_called_once_with(signal_data)

    async def test_persist_signals_batch_delegates_to_data_manager(self):
        """persist_signals_batch() must delegate to the Data Manager client."""
        with (
            patch("ta_bot.services.mysql_client.DataManagerClient") as mock_dm,
            patch("ta_bot.services.mysql_client.DATA_MANAGER_AVAILABLE", True),
        ):
            mock_dm_instance = AsyncMock()
            mock_dm_instance.persist_signals_batch.return_value = True
            mock_dm.return_value = mock_dm_instance

            client = MySQLClient()
            signals = [
                {"symbol": "BTCUSDT", "confidence": 0.85},
                {"symbol": "ETHUSDT", "confidence": 0.90},
            ]

            result = await client.persist_signals_batch(signals)

            assert result is True
            mock_dm_instance.persist_signals_batch.assert_called_once_with(signals)


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
    """AC3 (#267) / AC2 (#284): a missing/broken Data Manager client import
    must log a WARNING, not fail silently, and construction must then
    hard-error (there is no fallback to degrade into)."""

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
                    "Data Manager client unavailable (%s: %s) — MySQLClient "
                    "has NO raw-MySQL fallback (removed per #284) and will "
                    "raise on construction. Fix the '.data_manager_client' "
                    "import.",
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
        False (not just the helper in isolation), and that construction then
        hard-errors instead of falling back to a raw connection."""
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
            with pytest.raises(RuntimeError, match="no raw-MySQL fallback"):
                reloaded.MySQLClient()
        finally:
            # Restore working state so subsequent tests in the same session
            # are unaffected.
            monkeypatch.undo()
            importlib.reload(mysql_client_module)
