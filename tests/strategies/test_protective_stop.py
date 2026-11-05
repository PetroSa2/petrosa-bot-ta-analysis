"""Stops are always on the protective side of the entry (petrosa-bot-ta-analysis#375)."""

import math

import pytest

from ta_bot.strategies.base_strategy import ATR_STOP_MULTIPLE, BaseStrategy

stop = BaseStrategy._protective_stop


def test_a_protective_level_stop_is_kept_unchanged():
    assert stop("buy", 98.5, 100.0, {"atr": 1.0}) == (98.5, "level")
    assert stop("sell", 101.5, 100.0, {"atr": 1.0}) == (101.5, "level")


def test_a_buy_stop_above_the_entry_moves_below_it_by_atr():
    assert stop("buy", 100.5, 100.0, {"atr": 1.0}) == (
        100.0 - ATR_STOP_MULTIPLE * 1.0,
        "volatility",
    )


def test_a_sell_stop_below_the_entry_moves_above_it_by_atr():
    assert stop("sell", 99.5, 100.0, {"atr": 1.0}) == (
        100.0 + ATR_STOP_MULTIPLE * 1.0,
        "volatility",
    )


def test_a_stop_equal_to_the_entry_is_not_protective():
    assert stop("buy", 100.0, 100.0, {"atr": 0.5})[1] == "volatility"
    assert stop("sell", 100.0, 100.0, {"atr": 0.5})[1] == "volatility"


def test_half_band_width_is_the_fallback_without_atr():
    current = {"atr": float("nan"), "bb_upper": 104.0, "bb_lower": 96.0}

    assert stop("buy", 101.0, 100.0, current) == (96.0, "volatility")
    assert stop("sell", 99.0, 100.0, {"bb_upper": 104.0, "bb_lower": 96.0}) == (
        104.0,
        "volatility",
    )


@pytest.mark.parametrize(
    "current",
    [{}, {"atr": 0.0}, {"atr": -1.0}, {"bb_upper": 96.0, "bb_lower": 96.0}],
)
def test_no_signal_when_no_volatility_is_measured(current):
    assert stop("buy", 101.0, 100.0, current) == (None, "none")


@pytest.mark.parametrize("level", [None, float("nan"), float("inf"), 0.0, -3.0])
def test_an_unusable_level_falls_back_to_volatility(level):
    value, source = stop("buy", level, 100.0, {"atr": 1.0})

    assert (value, source) == (98.0, "volatility")


def test_a_volatility_stop_that_would_be_negative_is_refused():
    assert stop("buy", 5.0, 1.0, {"atr": 10.0}) == (None, "none")


@pytest.mark.parametrize("entry", [0.0, -1.0, float("nan")])
def test_an_invalid_entry_gets_no_stop(entry):
    assert stop("buy", 1.0, entry, {"atr": 1.0}) == (None, "none")


def test_every_returned_stop_is_protective():
    for i in range(1, 400):
        entry = 1.0 + i * 0.37
        for action in ("buy", "sell"):
            for level in (entry * 0.9, entry, entry * 1.1, None):
                value, _ = stop(action, level, entry, {"atr": entry * 0.01 * (i % 7)})
                if value is None:
                    continue
                assert math.isfinite(value) and value > 0
                assert value < entry if action == "buy" else value > entry
