"""
Regression tests for petrosa-bot-ta-analysis#293.

Bug: `StrategyConfigManager`'s `get_global_config`/`upsert_global_config`/
`get_symbol_config`/`upsert_symbol_config` calls unconditionally delegate to
`self.data_manager_client.<method>(...)` on `MongoDBClient` when
`use_data_manager=True`. But `ta_bot.services.data_manager_client.DataManagerClient`
only implements `fetch_candles`, `persist_signal(s)`, and `health_check` — it has
no strategy-config CRUD at all. In deployed (Data Manager) mode this raised a hard
`AttributeError: 'DataManagerClient' object has no attribute 'get_global_config'`
on every `POST /api/v1/strategies/{id}/config` call (confirmed live via
`kubectl logs`).

Fix: `ta_bot/main.py` now gives `StrategyConfigManager` a dedicated MongoDBClient
instance constructed with `use_data_manager=False` (direct MongoDB collection
access) instead of the general Data-Manager-mode client — mirroring the existing
`ConfigRateLimiter` / `rate_limit_mongo_client` precedent for the same collection
family.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ta_bot.db.mongodb_client import MongoDBClient
from ta_bot.services.config_manager import StrategyConfigManager
from ta_bot.services.data_manager_client import DataManagerClient


@pytest.mark.asyncio
class TestDataManagerModeReproducesAttributeError:
    """Prove the bug is real: DataManagerClient genuinely lacks the 4 methods
    that MongoDBClient's config CRUD delegates to in Data Manager mode."""

    @pytest.fixture
    def dm_mode_client_with_real_dm_spec(self):
        """A MongoDBClient in Data Manager mode whose `data_manager_client` is
        spec'd against the *real* DataManagerClient class, so attribute access
        for a method that class doesn't define raises AttributeError exactly
        like production -- not a permissive MagicMock that would mask the bug.
        """
        client = MongoDBClient(use_data_manager=True)
        client._connected = True
        client.data_manager_client = AsyncMock(spec=DataManagerClient)
        return client

    async def test_get_global_config_attribute_error_on_unpatched_client(
        self, dm_mode_client_with_real_dm_spec
    ):
        with pytest.raises(AttributeError):
            await dm_mode_client_with_real_dm_spec.get_global_config("rsi_bot")

    async def test_upsert_global_config_attribute_error_on_unpatched_client(
        self, dm_mode_client_with_real_dm_spec
    ):
        with pytest.raises(AttributeError):
            await dm_mode_client_with_real_dm_spec.upsert_global_config(
                "rsi_bot", {"rsi": 14}, {"created_by": "test"}
            )

    async def test_get_symbol_config_attribute_error_on_unpatched_client(
        self, dm_mode_client_with_real_dm_spec
    ):
        with pytest.raises(AttributeError):
            await dm_mode_client_with_real_dm_spec.get_symbol_config(
                "rsi_bot", "BTCUSDT"
            )

    async def test_upsert_symbol_config_attribute_error_on_unpatched_client(
        self, dm_mode_client_with_real_dm_spec
    ):
        with pytest.raises(AttributeError):
            await dm_mode_client_with_real_dm_spec.upsert_symbol_config(
                "rsi_bot", "BTCUSDT", {"rsi": 14}, {"created_by": "test"}
            )


@pytest.mark.asyncio
class TestDirectMongoModeAvoidsAttributeError:
    """Prove the fix: the same 4 methods succeed against a direct-MongoDB
    (use_data_manager=False) client and never touch `data_manager_client`."""

    @pytest.fixture
    def direct_mode_client(self):
        """A MongoDBClient in direct-MongoDB mode with a fully mocked motor
        database handle -- no real MongoDB connection required."""
        client = MongoDBClient(use_data_manager=False)
        assert client.use_data_manager is False
        client._connected = True
        mock_db = MagicMock()
        mock_db.strategy_configs_global.find_one = AsyncMock(return_value=None)
        mock_db.strategy_configs_global.update_one = AsyncMock(
            return_value=MagicMock(upserted_id="abc123")
        )
        mock_db.strategy_configs_symbol.find_one = AsyncMock(return_value=None)
        mock_db.strategy_configs_symbol.update_one = AsyncMock(
            return_value=MagicMock(upserted_id="def456")
        )
        client.database = mock_db
        return client

    async def test_get_global_config_succeeds_without_data_manager_client(
        self, direct_mode_client
    ):
        assert not hasattr(direct_mode_client, "data_manager_client")
        result = await direct_mode_client.get_global_config("rsi_bot")
        assert result is None  # no doc yet, but no AttributeError

    async def test_upsert_global_config_succeeds_without_data_manager_client(
        self, direct_mode_client
    ):
        config_id = await direct_mode_client.upsert_global_config(
            "rsi_bot", {"rsi": 14}, {"created_by": "test"}
        )
        assert config_id == "abc123"
        direct_mode_client.database.strategy_configs_global.update_one.assert_awaited_once()

    async def test_get_symbol_config_succeeds_without_data_manager_client(
        self, direct_mode_client
    ):
        result = await direct_mode_client.get_symbol_config("rsi_bot", "BTCUSDT")
        assert result is None

    async def test_upsert_symbol_config_succeeds_without_data_manager_client(
        self, direct_mode_client
    ):
        config_id = await direct_mode_client.upsert_symbol_config(
            "rsi_bot", "BTCUSDT", {"rsi": 14}, {"created_by": "test"}
        )
        assert config_id == "def456"


@pytest.mark.asyncio
class TestStrategyConfigManagerEndToEndWithDirectMongo:
    """End-to-end (no real MongoDB) proof that the config-update path AC
    (#293) round-trips through StrategyConfigManager + a direct-mode
    MongoDBClient without any AttributeError."""

    @pytest.fixture
    def manager_with_direct_mongo(self):
        client = MongoDBClient(use_data_manager=False)
        client._connected = True
        mock_db = MagicMock()
        store: dict[str, dict] = {}

        async def fake_find_one(query):
            return store.get(query["strategy_id"])

        async def fake_update_one(query, update, upsert):
            doc = dict(update["$set"])
            store[query["strategy_id"]] = doc
            existed = query["strategy_id"] in store
            result = MagicMock()
            result.upserted_id = None if existed else "new-id"
            return result

        mock_db.strategy_configs_global.find_one = AsyncMock(side_effect=fake_find_one)
        mock_db.strategy_configs_global.update_one = AsyncMock(
            side_effect=fake_update_one
        )
        mock_db.strategy_config_audit.insert_one = AsyncMock(
            return_value=MagicMock(inserted_id="audit-1")
        )
        client.database = mock_db
        return StrategyConfigManager(mongodb_client=client, cache_ttl_seconds=60)

    async def test_set_then_get_config_round_trips(self, manager_with_direct_mongo):
        success, config, errors = await manager_with_direct_mongo.set_config(
            strategy_id="rsi_bot",
            parameters={"rsi_period": 14},
            changed_by="test-user",
        )
        assert success is True
        assert errors == []
        assert config.parameters == {"rsi_period": 14}

        manager_with_direct_mongo._invalidate_cache(
            manager_with_direct_mongo._make_cache_key("rsi_bot", None)
        )
        result = await manager_with_direct_mongo.get_config("rsi_bot")
        assert result["parameters"] == {"rsi_period": 14}
        assert result["source"] == "mongodb"


@pytest.mark.asyncio
async def test_main_wires_strategy_config_manager_with_direct_mongo_client():
    """Wiring regression test: `ta_bot.main.main()` must instantiate a
    *dedicated* `MongoDBClient(use_data_manager=False)` for the strategy
    config manager -- not the general Data-Manager-mode `mongodb_client` that
    reproduces #293's AttributeError. Uses distinct mock instances per
    `use_data_manager` value (via `side_effect`) so the assertion actually
    discriminates between the two clients, unlike a single shared
    `return_value` mock."""
    for m in ["ta_bot.main", "ta_bot.config"]:
        if m in sys.modules:
            del sys.modules[m]

    _petrosa_otel_saved = {
        k: sys.modules[k]
        for k in list(sys.modules)
        if k == "petrosa_otel" or k.startswith("petrosa_otel.")
    }
    for k in _petrosa_otel_saved:
        del sys.modules[k]
    sys.modules["petrosa_otel"] = MagicMock()

    try:
        with patch.dict(os.environ, {"NATS_ENABLED": "False"}):
            with (
                patch("ta_bot.main.initialize_telemetry_standard"),
                patch("ta_bot.main.attach_logging_handler"),
                patch("ta_bot.main.setup_signal_handlers"),
                patch("ta_bot.main.MongoDBClient") as mock_mongo_cls,
                patch("ta_bot.main.AppConfigManager") as mock_acm_cls,
                patch("ta_bot.main.StrategyConfigManager") as mock_scm_cls,
                patch("ta_bot.main.SignalPublisher"),
                patch("ta_bot.main.NATSListener") as mock_nats_cls,
                patch("ta_bot.main.start_health_server") as mock_health_fn,
                patch("ta_bot.main.asyncio.gather", new_callable=AsyncMock),
                patch("ta_bot.main.asyncio.sleep", new_callable=AsyncMock),
                patch(
                    "ta_bot.services.data_manager_config_client.DataManagerConfigClient"
                ) as mock_dm_cls,
            ):
                dm_mode_mongo = MagicMock(name="dm_mode_mongo")
                dm_mode_mongo.connect = AsyncMock(return_value=True)
                direct_mode_mongos: list[MagicMock] = []

                def mongo_side_effect(*args, **kwargs):
                    if kwargs.get("use_data_manager") is False:
                        m = MagicMock(
                            name=f"direct_mode_mongo_{len(direct_mode_mongos)}"
                        )
                        m.connect = AsyncMock(return_value=True)
                        direct_mode_mongos.append(m)
                        return m
                    return dm_mode_mongo

                mock_mongo_cls.side_effect = mongo_side_effect

                mock_dm = mock_dm_cls.return_value
                mock_dm.connect = AsyncMock(return_value=True)

                mock_acm = mock_acm_cls.return_value
                mock_acm.start = AsyncMock()
                mock_acm.get_config = AsyncMock(return_value={"version": 0})
                mock_acm.set_config = AsyncMock(return_value=(True, "ok", []))

                mock_scm = mock_scm_cls.return_value
                mock_scm.start = AsyncMock()

                mock_nats = mock_nats_cls.return_value
                mock_nats.start = AsyncMock(return_value=None)

                mock_health_server = MagicMock()
                mock_health_server.start = AsyncMock(return_value=None)
                mock_health_fn.return_value = mock_health_server

                from ta_bot.api import config_routes
                from ta_bot.main import main

                config_routes.set_config_manager(None)  # type: ignore[arg-type]

                await main()

                # At least two direct-mode clients now: the pre-existing rate
                # limiter one, and the new strategy-config one (#293).
                assert len(direct_mode_mongos) >= 2

                # The StrategyConfigManager must have been built with ONE of
                # the direct-mode clients, never the DM-mode singleton that
                # reproduces the AttributeError.
                call_kwargs = mock_scm_cls.call_args.kwargs
                assert call_kwargs["mongodb_client"] in direct_mode_mongos
                assert call_kwargs["mongodb_client"] is not dm_mode_mongo
                assert call_kwargs["cache_ttl_seconds"] == 60

                # And that client must have actually been connected before
                # being handed to StrategyConfigManager.
                call_kwargs["mongodb_client"].connect.assert_awaited_once()

                mock_scm.start.assert_awaited_once()
                assert config_routes.get_config_manager() is mock_scm
    finally:
        for k in [
            m
            for m in list(sys.modules)
            if m == "petrosa_otel" or m.startswith("petrosa_otel.")
        ]:
            del sys.modules[k]
        sys.modules.update(_petrosa_otel_saved)
