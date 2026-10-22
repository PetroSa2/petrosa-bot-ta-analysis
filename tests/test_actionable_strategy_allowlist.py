from ta_bot.config import ACTIONABLE_STRATEGIES, missing_actionable_strategies


def test_actionable_strategy_allowlist_is_complete():
    assert missing_actionable_strategies(list(ACTIONABLE_STRATEGIES)) == set()


def test_missing_actionable_strategy_is_reported():
    enabled = list(ACTIONABLE_STRATEGIES - {"rsi_extreme_reversal"})

    assert missing_actionable_strategies(enabled) == {"rsi_extreme_reversal"}
