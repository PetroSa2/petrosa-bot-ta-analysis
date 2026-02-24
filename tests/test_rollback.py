"""
Tests for configuration rollback in TA Bot.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from ta_bot.services.app_config_manager import AppConfigManager
from ta_bot.services.config_manager import StrategyConfigManager


@pytest.fixture
def mock_mongodb_client():
    client = MagicMock()
    client.is_connected = True
    client.use_data_manager = True
    client.data_manager_client = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_strategy_config_rollback(mock_mongodb_client):
    # Setup
    mock_mongodb_client.data_manager_client.rollback_strategy_config.return_value = True

    manager = StrategyConfigManager(mongodb_client=mock_mongodb_client)
    # Mock get_config to avoid actual DB call
    manager.get_config = AsyncMock(
        return_value={"parameters": {"rsi": 14}, "version": 2}
    )

    # Execute
    success, config, errors = await manager.rollback_config("rsi_bot", "admin")

    # Verify
    assert success is True
    assert config.strategy_id == "rsi_bot"
    mock_mongodb_client.data_manager_client.rollback_strategy_config.assert_called_once()


@pytest.mark.asyncio
async def test_app_config_rollback(mock_mongodb_client):
    # Setup
    mock_data_manager = AsyncMock()
    mock_data_manager.rollback_app_config.return_value = True

    manager = AppConfigManager(data_manager_client=mock_data_manager)
    # Mock get_config
    manager.get_config = AsyncMock(return_value={"symbols": ["BTCUSDT"], "version": 5})

    # Execute
    success, config, errors = await manager.rollback_config("admin")

    # Verify
    assert success is True
    assert config.version == 5
    mock_data_manager.rollback_app_config.assert_called_once()
