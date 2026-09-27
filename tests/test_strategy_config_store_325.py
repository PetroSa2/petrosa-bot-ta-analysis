from unittest.mock import AsyncMock, MagicMock

import pytest

from ta_bot.services.config_manager import StrategyConfigManager
from ta_bot.services.strategy_config_store import DataManagerStrategyConfigStore


@pytest.fixture
def client():
    value = MagicMock()
    value.connect = AsyncMock()
    value.disconnect = AsyncMock()
    value.get_strategy_config_record = AsyncMock()
    value.set_strategy_config = AsyncMock(return_value=True)
    value.delete_strategy_config = AsyncMock(return_value=True)
    value.get_strategy_audit_trail = AsyncMock(return_value=[])
    value.list_strategy_configs = AsyncMock(return_value=[])
    value.list_strategy_symbols = AsyncMock(return_value=[])
    value.rollback_strategy_config = AsyncMock(return_value=True)
    return value


@pytest.mark.asyncio
async def test_symbol_config_uses_gateway_then_global_fallback(client):
    client.get_strategy_config_record.side_effect = [None, {"parameters": {"x": 1}}]
    store = DataManagerStrategyConfigStore(client)
    manager = StrategyConfigManager(store=store)
    store._connected = True

    result = await manager.get_config("momentum_pulse", "BTCUSDT")

    assert result["parameters"] == {"x": 1}
    assert result["source"] == "mongodb"
    assert client.get_strategy_config_record.await_args_list[0].args == (
        "momentum_pulse",
        "BTCUSDT",
    )


@pytest.mark.asyncio
async def test_writes_delete_and_rollback_use_gateway(client):
    client.get_strategy_config_record.return_value = {
        "parameters": {"x": 1},
        "version": 1,
    }
    store = DataManagerStrategyConfigStore(client)
    store._connected = True
    manager = StrategyConfigManager(store=store)

    success, _, errors = await manager.set_config("strategy", {"x": 2}, "test")
    deleted, delete_errors = await manager.delete_config("strategy", "test")
    rolled_back, _, rollback_errors = await manager.rollback_config("strategy", "test")

    assert success is True
    assert errors == []
    assert deleted is True
    assert delete_errors == []
    assert rolled_back is True
    assert rollback_errors == []
    assert client.set_strategy_config.await_count == 1
    assert client.delete_strategy_config.await_count == 1
    client.rollback_strategy_config.assert_awaited_once()


@pytest.mark.asyncio
async def test_gateway_outage_returns_default(client):
    client.get_strategy_config_record.side_effect = ConnectionError("offline")
    store = DataManagerStrategyConfigStore(client)
    store._connected = True
    manager = StrategyConfigManager(store=store)

    result = await manager.get_config("momentum_pulse", "BTCUSDT")

    assert result["source"] == "default"
