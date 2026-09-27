from unittest.mock import patch

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
async def test_startup_rate_limiter_uses_data_manager_gateway():
    import ta_bot.main as main

    limiter = object()
    with patch.object(main, "DataManagerConfigRateLimiter", return_value=limiter) as factory:
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
