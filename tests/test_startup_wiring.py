import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure petrosa_otel is mocked globally for this test session
if "petrosa_otel" not in sys.modules:
    sys.modules["petrosa_otel"] = MagicMock()


def reload_ta_bot_modules():
    """Force reload of ta_bot modules to respect environmental changes."""
    for m in ["ta_bot.main", "ta_bot.config"]:
        if m in sys.modules:
            del sys.modules[m]


@pytest.mark.asyncio
async def test_main_startup_wiring():
    """
    Test that the main() entry point correctly initializes components,
    specifically verifying that MongoDBClient is called with use_data_manager=False.
    """
    reload_ta_bot_modules()
    with patch.dict(
        os.environ,
        {
            "NATS_ENABLED": "True",
            "CONFIG_RATE_LIMIT_PER_AGENT": "10",
            "CONFIG_RATE_LIMIT_COOLDOWN": "300",
            "OTEL_NO_AUTO_INIT": "",
        },
    ):
        with (
            patch("ta_bot.main.initialize_telemetry_standard") as mock_init_otel,
            patch("ta_bot.main.attach_logging_handler") as mock_attach_log,
            patch("ta_bot.main.setup_signal_handlers") as mock_sig,
            patch("ta_bot.main.MongoDBClient") as mock_mongo_cls,
            patch("ta_bot.main.AppConfigManager") as mock_acm_cls,
            patch("ta_bot.main.SignalPublisher") as mock_pub_cls,
            patch("ta_bot.main.NATSListener") as mock_nats_cls,
            patch("ta_bot.main.start_health_server") as mock_health_fn,
            patch("ta_bot.main.asyncio.gather", new_callable=AsyncMock) as mock_gather,
            patch("ta_bot.main.asyncio.sleep", new_callable=AsyncMock),
            patch(
                "ta_bot.services.data_manager_config_client.DataManagerConfigClient"
            ) as mock_dm_cls,
        ):
            # Configure mocks
            mock_mongo = mock_mongo_cls.return_value
            mock_mongo.connect = AsyncMock(return_value=True)

            mock_dm = mock_dm_cls.return_value
            mock_dm.connect = AsyncMock(return_value=True)

            mock_acm = mock_acm_cls.return_value
            mock_acm.start = AsyncMock()
            mock_acm.get_config = AsyncMock(
                return_value={"version": 1, "symbols": [], "candle_periods": []}
            )
            mock_acm.set_config = AsyncMock(return_value=(True, "ok", []))

            # Publisher health
            mock_pub = mock_pub_cls.return_value
            mock_pub.nats_client = MagicMock()

            # Health server
            mock_health_server = MagicMock()
            mock_health_server.start = AsyncMock(return_value=asyncio.sleep(0))
            mock_health_fn.return_value = mock_health_server

            # NATS Listener
            mock_nats = mock_nats_cls.return_value
            mock_nats.start = AsyncMock(return_value=asyncio.sleep(0))

            from ta_bot.main import main

            # Run main
            mock_gather.return_value = []
            await main()

            # VERIFICATIONS
            mock_init_otel.assert_called_once()
            assert mock_mongo_cls.call_count >= 2
            assert any(
                c.kwargs.get("use_data_manager") is False
                for c in mock_mongo_cls.call_args_list
            )
            mock_dm.connect.assert_called_once()
            mock_acm.start.assert_called_once()
            mock_health_fn.assert_called_once()


@pytest.mark.asyncio
async def test_main_startup_mongodb_failure():
    """
    Test that main() raises RuntimeError when direct MongoDB connection fails.
    """
    reload_ta_bot_modules()
    with (
        patch("ta_bot.main.initialize_telemetry_standard"),
        patch("ta_bot.main.attach_logging_handler"),
        patch("ta_bot.main.setup_signal_handlers"),
        patch("ta_bot.main.MongoDBClient") as mock_mongo_cls,
        patch("ta_bot.main.AppConfigManager"),
        patch("ta_bot.main.SignalPublisher"),
        patch("ta_bot.main.NATSListener"),
        patch("ta_bot.main.start_health_server"),
        patch("ta_bot.main.asyncio.gather", new_callable=AsyncMock),
        patch("ta_bot.main.asyncio.sleep", new_callable=AsyncMock),
        patch(
            "ta_bot.services.data_manager_config_client.DataManagerConfigClient"
        ) as mock_dm_cls,
    ):
        mock_mongo = mock_mongo_cls.return_value
        mock_mongo.connect = AsyncMock()
        mock_mongo.connect.side_effect = [True, False]

        mock_dm = mock_dm_cls.return_value
        mock_dm.connect = AsyncMock(return_value=True)

        from ta_bot.main import main

        with patch.dict(os.environ, {"NATS_ENABLED": "False"}):
            with pytest.raises(
                RuntimeError, match="Direct MongoDB connection for rate limiter failed"
            ):
                await main()


@pytest.mark.asyncio
async def test_main_startup_no_runtime_config():
    """
    Test that main() handles missing runtime configuration and falls back to defaults.
    """
    reload_ta_bot_modules()
    with patch.dict(os.environ, {"NATS_ENABLED": "False"}):
        with (
            patch("ta_bot.main.initialize_telemetry_standard"),
            patch("ta_bot.main.attach_logging_handler"),
            patch("ta_bot.main.setup_signal_handlers"),
            patch("ta_bot.main.MongoDBClient") as mock_mongo_cls,
            patch("ta_bot.main.AppConfigManager") as mock_acm_cls,
            patch("ta_bot.main.SignalPublisher"),
            patch("ta_bot.main.NATSListener") as mock_nats_cls,
            patch("ta_bot.main.start_health_server") as mock_health_fn,
            patch("ta_bot.main.asyncio.gather", new_callable=AsyncMock),
            patch("ta_bot.main.asyncio.sleep", new_callable=AsyncMock),
            patch(
                "ta_bot.services.data_manager_config_client.DataManagerConfigClient"
            ) as mock_dm_cls,
        ):
            mock_mongo = mock_mongo_cls.return_value
            mock_mongo.connect = AsyncMock(return_value=True)

            mock_dm = mock_dm_cls.return_value
            mock_dm.connect = AsyncMock(return_value=True)

            mock_acm = mock_acm_cls.return_value
            mock_acm.start = AsyncMock()
            mock_acm.get_config = AsyncMock(return_value={"version": 0})
            mock_acm.set_config = AsyncMock(return_value=(True, "ok", []))

            mock_nats = mock_nats_cls.return_value
            mock_nats.start = AsyncMock(return_value=asyncio.sleep(0))

            mock_health_server = MagicMock()
            mock_health_server.start = AsyncMock(return_value=asyncio.sleep(0))
            mock_health_fn.return_value = mock_health_server

            from ta_bot.main import main

            await main()

            # Verify fallback logic was called
            mock_acm.get_config.assert_called_once()
            mock_acm.set_config.assert_called_once()


@pytest.mark.asyncio
async def test_main_startup_persist_config_failure():
    """
    Test that main() handles persistence failure gracefully.
    """
    reload_ta_bot_modules()
    with (
        patch("ta_bot.main.initialize_telemetry_standard"),
        patch("ta_bot.main.attach_logging_handler"),
        patch("ta_bot.main.setup_signal_handlers"),
        patch("ta_bot.main.MongoDBClient") as mock_mongo_cls,
        patch("ta_bot.main.AppConfigManager") as mock_acm_cls,
        patch("ta_bot.main.SignalPublisher"),
        patch("ta_bot.main.NATSListener") as mock_nats_cls,
        patch("ta_bot.main.start_health_server") as mock_health_fn,
        patch("ta_bot.main.asyncio.gather", new_callable=AsyncMock),
        patch("ta_bot.main.asyncio.sleep", new_callable=AsyncMock),
        patch(
            "ta_bot.services.data_manager_config_client.DataManagerConfigClient"
        ) as mock_dm_cls,
    ):
        mock_mongo = mock_mongo_cls.return_value
        mock_mongo.connect = AsyncMock(return_value=True)

        mock_dm = mock_dm_cls.return_value
        mock_dm.connect = AsyncMock(return_value=True)

        mock_acm = mock_acm_cls.return_value
        mock_acm.start = AsyncMock()
        mock_acm.get_config = AsyncMock(return_value={"version": 0})
        mock_acm.set_config = AsyncMock(return_value=(False, "error", ["reason"]))

        mock_nats = mock_nats_cls.return_value
        mock_nats.start = AsyncMock(return_value=asyncio.sleep(0))

        mock_health_server = MagicMock()
        mock_health_server.start = AsyncMock(return_value=asyncio.sleep(0))
        mock_health_fn.return_value = mock_health_server

        from ta_bot.main import main

        with patch.dict(os.environ, {"NATS_ENABLED": "False"}):
            await main()
            mock_acm.set_config.assert_called_once()


@pytest.mark.asyncio
async def test_main_startup_nats_connection_failure():
    """
    Test that main() raises RuntimeError when NATS connection fails.
    """
    reload_ta_bot_modules()
    with (
        patch("ta_bot.main.initialize_telemetry_standard"),
        patch("ta_bot.main.attach_logging_handler"),
        patch("ta_bot.main.setup_signal_handlers"),
        patch("ta_bot.main.MongoDBClient") as mock_mongo_cls,
        patch("ta_bot.main.AppConfigManager") as mock_acm_cls,
        patch("ta_bot.main.SignalPublisher") as mock_pub_cls,
        patch("ta_bot.main.NATSListener") as mock_nats_cls,
        patch("ta_bot.main.start_health_server") as mock_health_fn,
        patch("ta_bot.main.asyncio.gather", new_callable=AsyncMock),
        patch("ta_bot.main.asyncio.sleep", new_callable=AsyncMock),
        patch(
            "ta_bot.services.data_manager_config_client.DataManagerConfigClient"
        ) as mock_dm_cls,
    ):
        mock_mongo = mock_mongo_cls.return_value
        mock_mongo.connect = AsyncMock(return_value=True)

        mock_dm = mock_dm_cls.return_value
        mock_dm.connect = AsyncMock(return_value=True)

        mock_acm = mock_acm_cls.return_value
        mock_acm.start = AsyncMock()
        mock_acm.get_config = AsyncMock(return_value={"version": 1})

        mock_pub = mock_pub_cls.return_value
        mock_pub.nats_client = None

        mock_nats = mock_nats_cls.return_value
        mock_nats.start = AsyncMock(return_value=asyncio.sleep(0))

        mock_health_server = MagicMock()
        mock_health_server.start = AsyncMock(return_value=asyncio.sleep(0))
        mock_health_fn.return_value = mock_health_server

        from ta_bot.main import main

        with patch.dict(os.environ, {"NATS_ENABLED": "True"}):
            with pytest.raises(RuntimeError, match="Signal publishing will not work"):
                await main()
