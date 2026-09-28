import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ta_bot.services.data_manager_config_client import DataManagerConfigClient


@pytest.mark.asyncio
async def test_config_manager_requires_data_manager_client():
    from ta_bot.services.app_config_manager import AppConfigManager

    with pytest.raises(TypeError):
        AppConfigManager()

    manager = AppConfigManager(DataManagerConfigClient())
    assert manager.data_manager_client is not None


@pytest.mark.asyncio
async def test_app_config_manager_reads_and_writes_through_data_manager():
    from ta_bot.services.app_config_manager import AppConfigManager

    client = MagicMock()
    client.get_app_config = AsyncMock(
        return_value={
            "version": 1,
            "enabled_strategies": ["rsi_extreme_reversal"],
            "symbols": ["BTCUSDT"],
            "candle_periods": ["15m"],
            "min_confidence": 0.7,
            "max_confidence": 0.95,
            "max_positions": 10,
            "position_sizes": [100],
        }
    )
    client.set_app_config = AsyncMock(return_value=True)
    manager = AppConfigManager(client)

    loaded = await manager.get_config()
    success, saved, errors = await manager.set_config(
        loaded | {"source": "default"}, "test"
    )

    assert loaded["source"] == "data_manager"
    assert success is True
    assert saved is not None
    assert errors == []
    client.get_app_config.assert_awaited_once_with()
    client.set_app_config.assert_awaited_once()


@pytest.mark.asyncio
async def test_startup_rate_limiter_uses_data_manager_gateway():
    import ta_bot.main as main

    limiter = object()
    with patch.object(
        main, "DataManagerConfigRateLimiter", return_value=limiter
    ) as factory:
        with patch.object(main, "set_rate_limiter") as set_limiter:
            rate_limiter = main.DataManagerConfigRateLimiter(
                base_url="http://data-manager",
                service_name="ta-bot",
                per_agent_limit=10,
                cooldown_seconds=300,
            )
            set_limiter(rate_limiter)

    factory.assert_called_once_with(
        base_url="http://data-manager",
        service_name="ta-bot",
        per_agent_limit=10,
        cooldown_seconds=300,
    )
    set_limiter.assert_called_once_with(limiter)


@pytest.mark.asyncio
async def test_startup_disables_direct_database_telemetry_instrumentation():
    import ta_bot.main as main

    with (
        patch.object(main, "initialize_telemetry_standard") as initialize,
        patch.object(
            main, "attach_logging_handler", side_effect=RuntimeError("stop startup")
        ),
        patch.dict(os.environ, {"OTEL_NO_AUTO_INIT": ""}),
    ):
        with pytest.raises(RuntimeError, match="stop startup"):
            await main.main()

    initialize.assert_called_once_with(
        service_name="petrosa-bot-ta-analysis",
        service_type="fastapi",
        enable_fastapi=True,
        enable_mongodb=False,
        enable_mysql=False,
    )
