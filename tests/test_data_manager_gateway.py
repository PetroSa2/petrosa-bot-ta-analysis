from unittest.mock import AsyncMock, patch

import pytest

from ta_bot.services.data_manager_gateway import DataManagerGateway


@pytest.mark.asyncio
async def test_gateway_delegates_candle_fetch():
    with patch("ta_bot.services.data_manager_gateway.DataManagerClient") as client_type:
        client = client_type.return_value
        client.fetch_candles = AsyncMock(return_value=[])
        gateway = DataManagerGateway()

        result = await gateway.fetch_candles("BTCUSDT", "15m", 10)

        assert result == []
        client.fetch_candles.assert_awaited_once_with("BTCUSDT", "15m", 10)
