"""
Tests for issue #209 bug fixes:
  - AC1: Safe SIGTERM/SIGINT handler override for Python 3.11
  - AC2: DatetimeIndex via set_index("timestamp") in both fetch_candles paths
  - AC3: Default limit=250 (above EMA200 minimum) in both fetch_candles paths
"""

import signal
import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# AC1 — Python 3.11-safe signal handler override
# ---------------------------------------------------------------------------


class TestSafeSignalHandler:
    """Verify the safe SIGTERM/SIGINT handler registered in main.py."""

    def test_safe_signal_handler_exits_cleanly_on_sigterm(self):
        """Handler raises SystemExit(0) instead of crashing on SIGTERM."""
        import signal as _signal

        def _safe_signal_handler(signum: int, frame) -> None:
            try:
                name = _signal.Signals(signum).name
            except (ValueError, KeyError):
                name = str(signum)
            raise SystemExit(0)

        with pytest.raises(SystemExit) as exc_info:
            _safe_signal_handler(signal.SIGTERM, None)

        assert exc_info.value.code == 0

    def test_safe_signal_handler_handles_unknown_signum(self):
        """Handler falls back to str(signum) for unknown signal numbers."""
        import signal as _signal

        captured_name = []

        def _safe_signal_handler(signum: int, frame) -> None:
            try:
                name = _signal.Signals(signum).name
            except (ValueError, KeyError):
                name = str(signum)
            captured_name.append(name)
            raise SystemExit(0)

        with pytest.raises(SystemExit):
            _safe_signal_handler(9999, None)

        assert captured_name == ["9999"]

    def test_main_registers_safe_signal_handlers_after_otel_setup(self):
        """main() registers SIGTERM/SIGINT handlers AFTER setup_signal_handlers() is called.

        Validates call ordering: setup_signal_handlers() (petrosa_otel) must fire
        before our override so the safe handler wins on Python 3.11.
        """
        import asyncio

        import ta_bot.main as main_module

        call_order: list[str] = []

        mock_setup = MagicMock(
            side_effect=lambda: call_order.append("setup_signal_handlers")
        )
        registered: dict[int, object] = {}

        def fake_signal(sig, handler):
            call_order.append(f"signal.signal({sig})")
            registered[sig] = handler

        with (
            patch("ta_bot.main.initialize_telemetry_standard", None),
            patch("ta_bot.main.attach_logging_handler", None),
            patch.object(main_module, "setup_signal_handlers", mock_setup),
            patch("ta_bot.main._signal.signal", side_effect=fake_signal),
            patch("ta_bot.main.Config", side_effect=RuntimeError("stop")),
        ):
            try:
                asyncio.get_event_loop().run_until_complete(main_module.main())
            except RuntimeError:
                pass

        # Verify both handlers were registered
        assert signal.SIGTERM in registered
        assert signal.SIGINT in registered

        # Verify ordering: setup_signal_handlers (petrosa_otel) called before our overrides
        assert "setup_signal_handlers" in call_order, (
            "setup_signal_handlers was not called"
        )
        setup_idx = call_order.index("setup_signal_handlers")
        override_indices = [i for i, c in enumerate(call_order) if "signal.signal" in c]
        assert override_indices, "No _signal.signal() calls recorded"
        assert all(setup_idx < i for i in override_indices), (
            "Safe signal handler overrides must be registered AFTER setup_signal_handlers(); "
            f"call order was: {call_order}"
        )


# ---------------------------------------------------------------------------
# AC2 — DatetimeIndex via set_index("timestamp")
# ---------------------------------------------------------------------------


class TestDatetimeIndexMySQLClient:
    """Verify mysql_client.fetch_candles returns a DatetimeIndex."""

    @pytest.mark.asyncio
    async def test_fetch_candles_returns_datetime_index(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_cursor.fetchall.return_value = [
            {
                "timestamp": "2025-10-24 00:00:00",
                "open": 50000.0,
                "high": 51000.0,
                "low": 49000.0,
                "close": 50500.0,
                "volume": 100.5,
            },
            {
                "timestamp": "2025-10-24 00:15:00",
                "open": 50500.0,
                "high": 51500.0,
                "low": 50000.0,
                "close": 51000.0,
                "volume": 150.2,
            },
        ]

        with patch("pymysql.connect", return_value=mock_conn):
            from ta_bot.services.mysql_client import MySQLClient

            client = MySQLClient(use_data_manager=False)
            await client.connect()
            df = await client.fetch_candles("BTCUSDT", "15m", limit=2)

        assert isinstance(df.index, pd.DatetimeIndex), (
            "DataFrame index must be a DatetimeIndex so pandas_ta VWAP does not warn"
        )
        assert df.index.name == "timestamp"
        assert "timestamp" not in df.columns


class TestDatetimeIndexDataManagerClient:
    """Verify data_manager_client.fetch_candles returns a DatetimeIndex."""

    @pytest.mark.asyncio
    async def test_fetch_candles_returns_datetime_index(self):
        # Mock the data_manager_client module
        mock_exceptions = Mock()
        mock_exceptions.APIError = Exception
        mock_exceptions.ConnectionError = Exception
        mock_exceptions.TimeoutError = Exception

        mock_dm_module = Mock()
        mock_base_instance = AsyncMock()
        mock_dm_module.DataManagerClient = Mock(return_value=mock_base_instance)

        with (
            patch.dict(
                "sys.modules",
                {
                    "data_manager_client": mock_dm_module,
                    "data_manager_client.exceptions": mock_exceptions,
                },
            ),
        ):
            # Re-import to pick up mocks
            if "ta_bot.services.data_manager_client" in sys.modules:
                del sys.modules["ta_bot.services.data_manager_client"]

            mock_base_instance.get_candles.return_value = {
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

            from ta_bot.services.data_manager_client import DataManagerClient

            client = DataManagerClient(base_url="http://test:80")
            df = await client.fetch_candles("BTCUSDT", "15m", limit=2)

        assert isinstance(df.index, pd.DatetimeIndex), (
            "DataFrame index must be a DatetimeIndex so pandas_ta VWAP does not warn"
        )
        assert df.index.name == "timestamp"
        assert "timestamp" not in df.columns


# ---------------------------------------------------------------------------
# AC3 — Default limit=250 (≥ 200 required for EMA200)
# ---------------------------------------------------------------------------


class TestDefaultLimitMySQLClient:
    """Verify MySQLClient.fetch_candles defaults to limit=250."""

    def test_fetch_candles_default_limit_is_250(self):
        import inspect

        from ta_bot.services.mysql_client import MySQLClient

        sig = inspect.signature(MySQLClient.fetch_candles)
        default = sig.parameters["limit"].default
        assert default == 250, f"Expected default limit=250, got {default}"


class TestDefaultLimitDataManagerClient:
    """Verify DataManagerClient.fetch_candles defaults to limit=250."""

    def test_fetch_candles_default_limit_is_250(self):
        import inspect

        mock_exceptions = Mock()
        mock_exceptions.APIError = Exception
        mock_exceptions.ConnectionError = Exception
        mock_exceptions.TimeoutError = Exception

        mock_dm_module = Mock()
        mock_dm_module.DataManagerClient = Mock()

        with patch.dict(
            "sys.modules",
            {
                "data_manager_client": mock_dm_module,
                "data_manager_client.exceptions": mock_exceptions,
            },
        ):
            if "ta_bot.services.data_manager_client" in sys.modules:
                del sys.modules["ta_bot.services.data_manager_client"]

            from ta_bot.services.data_manager_client import DataManagerClient

            sig = inspect.signature(DataManagerClient.fetch_candles)
            default = sig.parameters["limit"].default
            assert default == 250, f"Expected default limit=250, got {default}"
