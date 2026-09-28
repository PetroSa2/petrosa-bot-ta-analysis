"""
Regression tests for #335: data-manager config responses are wrapped in a
``{"success": true, "data": {...}}`` envelope. ta-bot must read the inner record,
otherwise ``version`` looks like 0 and the stored application config is ignored
("No application configuration found in database, using defaults").
"""

import logging
from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientSession

from ta_bot.services.app_config_manager import AppConfigManager
from ta_bot.services.data_manager_config_client import DataManagerConfigClient

# Shape copied from the live GET /api/v1/config/application response.
APP_ENVELOPE = {
    "success": True,
    "data": {
        "enabled_strategies": ["momentum_pulse", "bollinger_squeeze_alert"],
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "candle_periods": ["5m", "15m"],
        "min_confidence": 0.7,
        "max_confidence": 0.95,
        "max_positions": 10,
        "position_sizes": [100, 200, 500, 1000],
        "llm_spend_ceiling_usd_per_day": 5.0,
        "version": 86,
        "source": "mongodb",
        "created_at": "2026-03-11T17:54:20.179000",
        "updated_at": "2026-09-28T18:57:42.432000",
    },
}

STRATEGY_ENVELOPE = {
    "success": True,
    "data": {
        "parameters": {"enabled": False},
        "version": 27,
        "source": "mongodb",
        "is_override": False,
    },
}


def _client_returning(payload, status=200):
    client = DataManagerConfigClient()
    client._session = AsyncMock(spec=ClientSession)
    response = AsyncMock()
    response.status = status
    response.json.return_value = payload
    context = AsyncMock()
    context.__aenter__.return_value = response
    client._session.get.return_value = context
    return client


class TestUnwrapEnvelope:
    def test_unwraps_data(self):
        assert (
            DataManagerConfigClient._unwrap_envelope(APP_ENVELOPE)
            == (APP_ENVELOPE["data"])
        )

    def test_bare_record_unchanged(self):
        bare = {"version": 1, "symbols": ["BTCUSDT"]}
        assert DataManagerConfigClient._unwrap_envelope(bare) is bare

    def test_null_data_preserved(self):
        assert DataManagerConfigClient._unwrap_envelope({"data": None}) is None

    def test_non_dict_unchanged(self):
        assert DataManagerConfigClient._unwrap_envelope([1, 2]) == [1, 2]


class TestClientEnvelope:
    @pytest.mark.asyncio
    async def test_get_app_config_unwraps_envelope(self):
        client = _client_returning(APP_ENVELOPE)
        result = await client.get_app_config()
        assert result["version"] == 86
        assert result["symbols"] == ["BTCUSDT", "ETHUSDT"]
        assert "success" not in result

    @pytest.mark.asyncio
    async def test_get_strategy_config_unwraps_envelope(self):
        client = _client_returning(STRATEGY_ENVELOPE)
        result = await client.get_strategy_config("bollinger_squeeze_alert")
        assert result["parameters"] == {"enabled": False}
        assert result["version"] == 27

    @pytest.mark.asyncio
    async def test_get_strategy_config_record_unwraps_envelope(self):
        client = _client_returning(STRATEGY_ENVELOPE)
        result = await client.get_strategy_config_record("bollinger_squeeze_alert")
        assert result == STRATEGY_ENVELOPE["data"]


class TestAppConfigManagerWithEnvelope:
    @pytest.mark.asyncio
    async def test_stored_config_is_used_not_defaults(self, caplog):
        manager = AppConfigManager(data_manager_client=_client_returning(APP_ENVELOPE))
        with caplog.at_level(
            logging.WARNING, logger="ta_bot.services.app_config_manager"
        ):
            result = await manager.get_config()

        assert result["source"] == "data_manager"
        assert result["version"] == 86
        assert result["enabled_strategies"] == [
            "momentum_pulse",
            "bollinger_squeeze_alert",
        ]
        assert result["symbols"] == ["BTCUSDT", "ETHUSDT"]
        assert result["candle_periods"] == ["5m", "15m"]
        assert "using defaults" not in caplog.text

    @pytest.mark.asyncio
    async def test_stored_config_is_cached(self):
        client = _client_returning(APP_ENVELOPE)
        manager = AppConfigManager(data_manager_client=client)
        await manager.get_config()
        second = await manager.get_config()
        assert second["cache_hit"] is True
        assert client._session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_unseeded_config_still_falls_back_to_defaults(self, caplog):
        # data-manager returns version 0 defaults when no document exists.
        envelope = {"success": True, "data": {**APP_ENVELOPE["data"], "version": 0}}
        manager = AppConfigManager(data_manager_client=_client_returning(envelope))
        with caplog.at_level(
            logging.WARNING, logger="ta_bot.services.app_config_manager"
        ):
            result = await manager.get_config()
        assert result["source"] == "default"
        assert "using defaults" in caplog.text
