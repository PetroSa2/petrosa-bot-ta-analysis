"""
Regression tests for MongoDBClient's app_config family of methods when the
client is running in Data Manager mode (petrosa-bot-ta-analysis#290).

Before the fix, `get_app_config`, `upsert_app_config`, `create_app_audit_record`,
and `get_app_audit_trail` guarded only on `self._connected` (which is True in
Data Manager mode) and then unconditionally dereferenced `self.database`
(which is always `None` in that mode, since only the direct-MongoDB path ever
populates it). That produced a continuous, misleading
"'NoneType' object has no attribute 'app_config'" ERROR log on every call.
"""

import logging

import pytest

from ta_bot.db.mongodb_client import MongoDBClient


@pytest.fixture
def data_manager_mode_client():
    """A MongoDBClient in Data Manager mode, connected, with no local
    database handle -- the exact state that reproduced the bug live."""
    client = MongoDBClient(use_data_manager=True)
    # Mirror what MongoDBClient.connect() actually does for this mode: set
    # `_connected = True` without ever touching `self.database`.
    client._connected = True
    assert client.database is None
    assert client.use_data_manager is True
    return client


@pytest.mark.asyncio
class TestAppConfigDataManagerModeNoneGuard:
    async def test_get_app_config_returns_none_without_attribute_error(
        self, data_manager_mode_client, caplog
    ):
        with caplog.at_level(logging.ERROR):
            result = await data_manager_mode_client.get_app_config()

        assert result is None
        assert not any("NoneType" in record.message for record in caplog.records), (
            "get_app_config must not log the NoneType AttributeError anymore"
        )

    async def test_upsert_app_config_returns_none_without_attribute_error(
        self, data_manager_mode_client, caplog
    ):
        with caplog.at_level(logging.ERROR):
            result = await data_manager_mode_client.upsert_app_config(
                config={"enabled_strategies": ["momentum_pulse"]},
                metadata={"changed_by": "test"},
            )

        assert result is None
        assert not any("NoneType" in record.message for record in caplog.records), (
            "upsert_app_config must not log the NoneType AttributeError anymore"
        )

    async def test_create_app_audit_record_returns_none_without_attribute_error(
        self, data_manager_mode_client, caplog
    ):
        with caplog.at_level(logging.ERROR):
            result = await data_manager_mode_client.create_app_audit_record(
                {"action": "update"}
            )

        assert result is None
        assert not any("NoneType" in record.message for record in caplog.records)

    async def test_get_app_audit_trail_returns_empty_list_without_attribute_error(
        self, data_manager_mode_client, caplog
    ):
        with caplog.at_level(logging.ERROR):
            result = await data_manager_mode_client.get_app_audit_trail()

        assert result == []
        assert not any("NoneType" in record.message for record in caplog.records)

    async def test_not_connected_still_returns_none(self):
        """Sanity check: the pre-existing not-connected short-circuit still
        works (this guards the direct-MongoDB path, unaffected by the fix)."""
        client = MongoDBClient(use_data_manager=False)
        assert client._connected is False

        assert await client.get_app_config() is None
        assert await client.upsert_app_config({}, {}) is None
        assert await client.create_app_audit_record({}) is None
        assert await client.get_app_audit_trail() == []
