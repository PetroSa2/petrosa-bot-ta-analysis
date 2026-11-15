import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

from ta_bot.config import ACTIONABLE_STRATEGIES, missing_actionable_strategies
from ta_bot.services.app_config_manager import AppConfigManager


def test_actionable_strategy_allowlist_is_complete():
    assert missing_actionable_strategies(list(ACTIONABLE_STRATEGIES)) == set()


def test_missing_actionable_strategy_is_reported():
    enabled = list(ACTIONABLE_STRATEGIES - {"rsi_extreme_reversal"})

    assert missing_actionable_strategies(enabled) == {"rsi_extreme_reversal"}


def test_runtime_config_logs_missing_actionable_strategy(caplog):
    client = MagicMock()
    client.get_app_config = AsyncMock(
        return_value={
            "version": 225,
            "enabled_strategies": list(
                ACTIONABLE_STRATEGIES - {"rsi_extreme_reversal"}
            ),
        }
    )
    client.get_cio_pause_entry = AsyncMock(return_value=None)

    with caplog.at_level(logging.ERROR, logger="ta_bot.services.app_config_manager"):
        config = asyncio.run(AppConfigManager(client).get_config())

    assert config["enabled_strategies"] == list(
        ACTIONABLE_STRATEGIES - {"rsi_extreme_reversal"}
    )
    assert "missing unexplained actionable strategy" in caplog.text


def test_runtime_config_logs_cio_pause_reason_once(caplog):
    client = MagicMock()
    client.get_app_config = AsyncMock(
        return_value={
            "version": 225,
            "enabled_strategies": list(
                ACTIONABLE_STRATEGIES - {"rsi_extreme_reversal"}
            ),
        }
    )
    client.get_cio_pause_entry = AsyncMock(
        return_value={"status": "paused", "pause_reason": "negative health"}
    )
    manager = AppConfigManager(client)

    with caplog.at_level(logging.WARNING, logger="ta_bot.services.app_config_manager"):
        asyncio.run(manager.get_config())
        manager._cache = None
        asyncio.run(manager.get_config())

    assert caplog.text.count("CIO-paused strategy") == 1
    assert "negative health" in caplog.text
    assert "ERROR" not in caplog.text


def test_runtime_config_logs_again_when_pause_classification_changes(caplog):
    client = MagicMock()
    client.get_app_config = AsyncMock(
        return_value={
            "version": 225,
            "enabled_strategies": list(
                ACTIONABLE_STRATEGIES - {"rsi_extreme_reversal"}
            ),
        }
    )
    client.get_cio_pause_entry = AsyncMock(
        side_effect=[{"status": "paused", "pause_reason": "negative health"}, None]
    )
    manager = AppConfigManager(client)

    with caplog.at_level(logging.WARNING, logger="ta_bot.services.app_config_manager"):
        asyncio.run(manager.get_config())
        manager._cache = None
        asyncio.run(manager.get_config())

    assert caplog.text.count("CIO-paused strategy") == 1
    assert caplog.text.count("missing unexplained actionable strategy") == 1


def test_runtime_config_treats_pause_lookup_failure_as_unexplained(caplog):
    client = MagicMock()
    client.get_app_config = AsyncMock(
        return_value={
            "version": 225,
            "enabled_strategies": list(
                ACTIONABLE_STRATEGIES - {"rsi_extreme_reversal"}
            ),
        }
    )
    client.get_cio_pause_entry = AsyncMock(side_effect=RuntimeError("timeout"))

    with caplog.at_level(logging.ERROR, logger="ta_bot.services.app_config_manager"):
        config = asyncio.run(AppConfigManager(client).get_config())

    assert config["version"] == 225
    assert "missing unexplained actionable strategy" in caplog.text
