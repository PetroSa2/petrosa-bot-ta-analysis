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
            "enabled_strategies": ["bollinger_squeeze_alert"],
        }
    )

    with caplog.at_level(logging.ERROR, logger="ta_bot.services.app_config_manager"):
        config = asyncio.run(AppConfigManager(client).get_config())

    assert config["enabled_strategies"] == ["bollinger_squeeze_alert"]
    assert "missing actionable strategies" in caplog.text
