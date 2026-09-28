from unittest.mock import AsyncMock, patch

import pytest

from ta_bot.services.data_manager_gateway import DataManagerGateway
from ta_bot.services.mysql_client import MySQLClient


@pytest.mark.asyncio
async def test_gateway_delegates_candle_fetch():
    with patch("ta_bot.services.data_manager_gateway.DataManagerClient") as client_type:
        client = client_type.return_value
        client.fetch_candles = AsyncMock(return_value=[])
        gateway = DataManagerGateway()

        result = await gateway.fetch_candles("BTCUSDT", "15m", 10)

        assert result == []
        client.fetch_candles.assert_awaited_once_with("BTCUSDT", "15m", 10)


@pytest.mark.asyncio
async def test_gateway_delegates_lifecycle_and_signal_persistence():
    with patch("ta_bot.services.data_manager_gateway.DataManagerClient") as client_type:
        client = client_type.return_value
        client.connect = AsyncMock()
        client.disconnect = AsyncMock()
        client.persist_signal = AsyncMock(return_value=True)
        client.persist_signals_batch = AsyncMock(return_value=True)
        gateway = DataManagerGateway()

        await gateway.connect()
        await gateway.disconnect()
        assert await gateway.persist_signal({"id": "signal-1"}) is True
        assert await gateway.persist_signals_batch([{"id": "signal-1"}]) is True

        client.connect.assert_awaited_once_with()
        client.disconnect.assert_awaited_once_with()
        client.persist_signal.assert_awaited_once_with({"id": "signal-1"})
        client.persist_signals_batch.assert_awaited_once_with([{"id": "signal-1"}])


def test_mysql_client_is_deprecated_data_manager_alias():
    assert MySQLClient is DataManagerGateway
