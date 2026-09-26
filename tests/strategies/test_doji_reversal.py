"""Regression tests for the doji reversal strategy."""

import logging

import pandas as pd
import pytest

from ta_bot.models.signal import Signal, SignalStrength
from ta_bot.strategies.doji_reversal import DojiReversalStrategy


def make_doji_data(final_close: float) -> pd.DataFrame:
    """Build candles with a clear trend and a valid final doji candle."""
    closes = [100.0] * 19 + [final_close]
    return pd.DataFrame(
        {
            "open": [*closes[:-1], final_close + 0.01],
            "high": [*([101.0] * 19), final_close + 1.0],
            "low": [*([99.0] * 19), final_close - 1.0],
            "close": closes,
            "volume": [1000.0] * 20,
        }
    )


@pytest.mark.parametrize(
    ("final_close", "action"),
    [(102.0, "sell"), (98.0, "buy")],
)
def test_analyze_constructs_signal_for_both_trend_branches(
    final_close, action, caplog
):
    """A valid doji returns a weak signal without logging an error."""
    caplog.set_level(logging.ERROR, logger="ta_bot.strategies.doji_reversal")

    result = DojiReversalStrategy().analyze(
        make_doji_data(final_close),
        {"symbol": "BTCUSDT", "timeframe": "15m"},
    )

    assert result is not None
    assert isinstance(result, Signal)
    assert result.strategy_id == "doji_reversal"
    assert result.strength == SignalStrength.WEAK
    assert result.action == action
    assert result.symbol == "BTCUSDT"
    assert result.timeframe == "15m"
    assert [record for record in caplog.records if record.levelno >= logging.ERROR] == []


def test_signal_strength_enum_contract_has_no_low_member():
    """The shared signal contract remains the four-level enum."""
    assert set(SignalStrength) == {
        SignalStrength.WEAK,
        SignalStrength.MEDIUM,
        SignalStrength.STRONG,
        SignalStrength.EXTREME,
    }
    assert not hasattr(SignalStrength, "LOW")
