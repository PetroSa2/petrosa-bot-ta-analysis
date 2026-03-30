"""
Tests for configuration rollback in TA Bot.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ta_bot.models.app_config import AppConfig, AppConfigAudit
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
    """Test strategy config rollback (Proxy to Data Manager)."""
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
    """Test app config rollback using the new implementation."""
    # 1. Setup
    manager = AppConfigManager(mongodb_client=mock_mongodb_client)

    sample_history = [
        AppConfigAudit(
            id="audit_2",
            action="UPDATE",
            old_config={"version": 1, "symbols": ["BTCUSDT"]},
            new_config={"version": 2, "symbols": ["BTCUSDT", "ETHUSDT"]},
            changed_by="user1",
            changed_at=datetime.now(timezone.utc),
        )
    ]

    # 2. Mock necessary methods
    with (
        patch.object(manager, "get_audit_trail", return_value=sample_history),
        patch.object(manager, "set_config", new_callable=AsyncMock) as mock_set_config,
    ):
        mock_set_config.return_value = (True, MagicMock(spec=AppConfig), [])

        # 3. Execute
        success, config, errors = await manager.rollback_config("admin")

        # 4. Verify
        assert success is True
        mock_set_config.assert_called_once()
        # Verify fix #1: correct parameter name
        kwargs = mock_set_config.call_args[1]
        assert "config" in kwargs
        assert kwargs["config"]["version"] == 1
