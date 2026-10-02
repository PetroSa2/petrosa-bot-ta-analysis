from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pandas as pd
import pytest

from ta_bot.backtest.config import BacktestConfig
from ta_bot.backtest.data import (
    DataManagerCandleLoader,
    MissingBarsError,
    expected_timestamps,
    normalize_candles,
)
from ta_bot.backtest.simulator import simulate


def candles(values):
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return pd.DataFrame(
        [
            {
                "timestamp": start + timedelta(minutes=5 * i),
                "open": value,
                "high": value + 2,
                "low": value - 1,
                "close": value + 1,
                "volume": 1,
            }
            for i, value in enumerate(values)
        ]
    )


def long_strategy(_window):
    return {"action": "buy", "stop_loss": 99, "take_profit": 105}


def test_decimal_trade_and_fee_accounting():
    result = simulate(
        candles([100, 100, 104, 110]),
        long_strategy,
        BacktestConfig(fee_bp_per_side=Decimal("4"), notional=Decimal("1000")),
    )
    assert result.trades[0].exit_reason == "take_profit"
    assert Decimal(result.trades[0].gross_pnl) == Decimal("50")
    assert Decimal(result.trades[0].fees) == Decimal("0.8")


def test_stop_wins_when_both_levels_are_touched():
    frame = candles([100, 100, 100])
    frame.loc[frame.index[2], "high"] = 106
    frame.loc[frame.index[2], "low"] = 98
    result = simulate(
        frame, long_strategy, BacktestConfig(fee_bp_per_side=Decimal("0"))
    )
    assert result.trades[0].exit_reason == "stop_loss"
    assert Decimal(result.trades[0].gross_pnl) < 0


def test_top_trade_is_removed_from_expectancy():
    result = simulate(
        candles([100, 100, 104, 110, 100]),
        long_strategy,
        BacktestConfig(fee_bp_per_side=Decimal("0")),
    )
    payload = result.to_dict()
    assert payload["expectancy_ex_top1"] != payload["expectancy_net"]


def test_missing_bars_are_rejected():
    start = datetime(2026, 1, 1, tzinfo=UTC)
    records = [
        {"timestamp": start, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1},
        {
            "timestamp": start + timedelta(minutes=10),
            "open": 1,
            "high": 1,
            "low": 1,
            "close": 1,
            "volume": 1,
        },
    ]
    try:
        normalize_candles(records, start, start + timedelta(minutes=10), "5m")
    except MissingBarsError as error:
        assert len(error.gaps) == 1
    else:
        raise AssertionError("missing bar was accepted")


def test_funding_is_charged_for_each_crossed_mark_and_open_trade_is_marked():
    frame = candles([100] * 10)
    frame.index = [
        datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=i) for i in range(10)
    ]
    frame = frame.drop(columns="timestamp")

    def funding_strategy(_window):
        return {"action": "buy", "stop_loss": 95, "take_profit": 105}

    result = simulate(
        frame,
        funding_strategy,
        BacktestConfig(fee_bp_per_side=Decimal("0"), funding_bp=Decimal("1")),
    )
    assert result.trades[0].open_at_end is True
    assert Decimal(result.trades[0].funding) == Decimal("0.1")


def test_strategy_only_sees_the_closed_prefix():
    seen_lengths = []

    def strategy(window):
        seen_lengths.append(len(window))
        return None

    simulate(candles([100, 101, 102]), strategy)
    assert seen_lengths == [1, 2]


def test_backtest_package_has_no_database_driver_imports():
    from pathlib import Path

    source = "".join(path.read_text() for path in Path("ta_bot/backtest").rglob("*.py"))
    assert "mysql" not in source.lower()


def test_sell_strategy_and_time_stop():
    frame = candles([100, 100, 100, 100]).set_index("timestamp")

    def strategy(_window):
        return {"action": "sell", "stop_loss": 105, "take_profit": 95}

    result = simulate(frame, strategy, BacktestConfig(time_stop_bars=1))
    assert result.trades[0].exit_reason == "time_stop"
    assert Decimal(result.trades[0].net_pnl) < 0


def test_result_serialization_covers_empty_and_cost_metrics():
    payload = simulate(candles([100, 100]), lambda _window: None).to_dict()
    assert payload["n_trades"] == 0
    assert payload["fee_share"] == "0"


def test_data_normalization_index_and_validation():
    start = datetime(2026, 1, 1, tzinfo=UTC)
    frame = candles([100, 101]).set_index("timestamp")
    normalized = normalize_candles(frame, start, start + timedelta(minutes=5), "5m")
    assert list(normalized.columns) == ["open", "high", "low", "close", "volume"]
    assert len(expected_timestamps(start, start, "5m")) == 1
    with pytest.raises(ValueError, match="unsupported timeframe"):
        expected_timestamps(start, start, "1d")
    with pytest.raises(ValueError, match="candle data missing columns"):
        normalize_candles(
            frame.drop(columns="volume"), start, start + timedelta(minutes=5), "5m"
        )


def test_data_loader_uses_async_client_factory():
    class Client:
        def __init__(self):
            self.connected = False

        async def connect(self):
            self.connected = True

        async def fetch_candles(self, **_kwargs):
            return candles([100, 101])

        async def disconnect(self):
            self.connected = False

    start = datetime(2026, 1, 1, tzinfo=UTC)
    result = DataManagerCandleLoader(Client).load(
        "BTCUSDT", "5m", start, start + timedelta(minutes=5)
    )
    assert len(result) == 2


def test_config_rejects_invalid_values():
    with pytest.raises(ValueError) as notional_error:
        BacktestConfig(notional=0)
    assert "notional" in str(notional_error.value)
    with pytest.raises(ValueError) as stop_error:
        BacktestConfig(time_stop_bars=-1)
    assert "time_stop_bars" in str(stop_error.value)
