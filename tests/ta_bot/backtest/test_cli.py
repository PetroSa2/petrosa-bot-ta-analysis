from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pandas as pd
import pytest

from ta_bot.backtest import __main__
from ta_bot.backtest.data import MissingBarsError


def frame():
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return pd.DataFrame(
        [
            {
                "timestamp": start + timedelta(minutes=5 * index),
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100,
                "volume": 1,
            }
            for index in range(2)
        ]
    ).set_index("timestamp")


def arguments():
    return [
        "--strategy",
        "demo",
        "--symbol",
        "BTCUSDT",
        "--timeframe",
        "5m",
        "--from",
        "2026-01-01T00:00:00",
        "--to",
        "2026-01-01T00:05:00",
    ]


def test_cli_prints_simulation_result(monkeypatch, capsys):
    class Loader:
        def load(self, *_args):
            return frame()

    class Engine:
        strategies = {"demo": object()}

        def analyze_candles(self, *_args):
            return [SimpleNamespace(action="buy", stop_loss=95, take_profit=105)]

    monkeypatch.setattr(__main__, "DataManagerCandleLoader", Loader)
    monkeypatch.setattr(__main__, "SignalEngine", Engine)
    assert __main__.main(arguments() + ["--time-stop-bars", "1"]) == 0
    assert '"parameters"' in capsys.readouterr().out


def test_cli_returns_gap_error(monkeypatch, capsys):
    class Loader:
        def load(self, *_args):
            raise MissingBarsError(["2026-01-01T00:05:00+00:00"])

    monkeypatch.setattr(__main__, "DataManagerCandleLoader", Loader)
    assert __main__.main(arguments()) == 2
    assert '"gaps"' in capsys.readouterr().out


def test_cli_rejects_unknown_strategy(monkeypatch):
    class Loader:
        def load(self, *_args):
            return frame()

    class Engine:
        strategies = {}

    monkeypatch.setattr(__main__, "DataManagerCandleLoader", Loader)
    monkeypatch.setattr(__main__, "SignalEngine", Engine)
    with pytest.raises(SystemExit):
        __main__.main(arguments())
