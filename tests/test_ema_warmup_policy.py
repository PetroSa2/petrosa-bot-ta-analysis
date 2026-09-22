"""Regression fixtures for the repository-wide EMA warm-up policy."""

import pandas as pd
import pytest

from ta_bot.core.indicators import Indicators, calculate_ema


def _close_prices(count: int) -> pd.Series:
    """Return deterministic trend data with a repeatable small variation."""
    return pd.Series(
        [100.0 + 0.15 * i + ((i % 11) - 5) * 0.03 for i in range(count)],
        name="close",
    )


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (
            250,
            {
                8: 136.82716537804535,
                21: 135.8470223087807,
                80: 131.43510854312063,
            },
        ),
        (
            400,
            {
                8: 159.2888846502939,
                21: 158.33702436218914,
                80: 153.92214314554215,
            },
        ),
    ],
)
def test_ema_regression_fixtures_cover_250_and_400_candles(count, expected):
    """EMA8, EMA21, and EMA80 values remain deterministic at both windows."""
    close = _close_prices(count)
    frame = pd.DataFrame({"close": close})

    for period, expected_value in expected.items():
        result = calculate_ema(close, period)
        indicator_result = Indicators.ema(frame, period)

        assert result.iloc[-1] == pytest.approx(expected_value)
        assert indicator_result.iloc[-1] == pytest.approx(expected_value)


def test_ema_policy_is_explicitly_adjust_false():
    """The shared helper matches pandas' recursive, non-adjusted calculation."""
    close = _close_prices(250)

    expected = close.ewm(span=21, min_periods=20, adjust=False).mean()

    assert calculate_ema(close, 21).equals(expected)
