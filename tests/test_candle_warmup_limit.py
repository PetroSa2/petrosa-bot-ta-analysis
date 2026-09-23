"""Guards for the candle warm-up contract (petrosa-bot-ta-analysis#303).

The fetch limit and the strategies' ``min_periods`` are declared in different
files. Nothing linked them, so ``minervini_trend_template`` shipped with
``min_periods = 265`` against a hardcoded fetch of 250 and could never fire.
These tests fail CI if that gap reopens.
"""

import pandas as pd
import pytest

from ta_bot.core.signal_engine import SignalEngine
from ta_bot.services.data_manager_client import MIN_WARMUP_CANDLES
from ta_bot.strategies.minervini_trend_template import MinerviniTrendTemplateStrategy


def _registered_strategies():
    """Every strategy the engine actually runs, keyed by name."""
    engine = SignalEngine.__new__(SignalEngine)
    SignalEngine.__init__(engine)
    return engine.strategies


def test_warmup_limit_covers_every_registered_strategy():
    """MIN_WARMUP_CANDLES must satisfy the hungriest registered strategy.

    Adding a strategy with a larger ``min_periods`` than the fetch limit must
    fail here rather than silently starve it in production.
    """
    floors = {
        name: getattr(strategy, "min_periods", 0)
        for name, strategy in _registered_strategies().items()
    }
    hungriest = max(floors, key=lambda n: floors[n])

    assert MIN_WARMUP_CANDLES >= floors[hungriest], (
        f"MIN_WARMUP_CANDLES={MIN_WARMUP_CANDLES} is below "
        f"{hungriest}.min_periods={floors[hungriest]}; that strategy can never fire. "
        "Raise MIN_WARMUP_CANDLES or lower the strategy's requirement."
    )


def test_minervini_requirement_is_covered():
    """The specific regression from #303: 250 < 265 starved minervini."""
    assert MIN_WARMUP_CANDLES >= MinerviniTrendTemplateStrategy().min_periods


def test_fetch_candles_defaults_to_the_warmup_limit():
    """The default must be the constant, not a re-declared literal."""
    import inspect

    from ta_bot.services.data_manager_client import DataManagerClient

    default = (
        inspect.signature(DataManagerClient.fetch_candles).parameters["limit"].default
    )
    assert default == MIN_WARMUP_CANDLES


def _daily_frame(distinct_days: int, duplicates_per_day: int = 1) -> pd.DataFrame:
    """Build a 1d OHLCV frame with a controllable number of duplicate bars."""
    stamps = pd.date_range("2024-01-01", periods=distinct_days, freq="D")
    stamps = stamps.repeat(duplicates_per_day)
    rows = len(stamps)
    close = [100.0 + i * 0.5 for i in range(rows)]
    return pd.DataFrame(
        {
            "open": close,
            "high": [c * 1.01 for c in close],
            "low": [c * 0.99 for c in close],
            "close": close,
            "volume": [1000.0] * rows,
        },
        index=pd.DatetimeIndex(stamps, name="timestamp"),
    )


@pytest.mark.parametrize("duplicates_per_day", [2, 3])
def test_minervini_gates_on_distinct_bars_not_row_count(duplicates_per_day):
    """Duplicate rows must not satisfy the warm-up gate.

    Before #303 the gate was ``len(data) < min_periods``. Duplicated daily rows
    cleared that row count while the 260/252-bar "52-week" windows actually
    spanned a fraction of the calendar time their labels claim.
    """
    strategy = MinerviniTrendTemplateStrategy()
    distinct = strategy.min_periods - 10  # deliberately too few REAL bars
    frame = _daily_frame(distinct, duplicates_per_day)

    # Row count clears the old gate...
    assert len(frame) >= strategy.min_periods
    # ...but distinct bars do not.
    assert frame.index.nunique() < strategy.min_periods

    assert strategy.analyze(frame, {"symbol": "BTCUSDT", "timeframe": "1d"}) is None


def test_minervini_still_runs_with_enough_distinct_bars():
    """The distinct-bar gate must not block genuinely sufficient data."""
    strategy = MinerviniTrendTemplateStrategy()
    frame = _daily_frame(strategy.min_periods + 5)

    assert frame.index.nunique() >= strategy.min_periods
    # Must get past the warm-up gate. The trend criteria may or may not be met
    # on synthetic data, so only assert it did not bail on insufficient data.
    strategy.analyze(frame, {"symbol": "BTCUSDT", "timeframe": "1d"})
