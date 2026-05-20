"""End-to-end backtest test using a recorded fixture.

Covers AC #5 of `petrosa-bot-ta-analysis#233`:
"Tests cover at least one canned strategy end-to-end with a recorded data
fixture." Two runs against the same fixture must produce byte-identical
artifacts (AC #3, reproducibility).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backtest.artifact import CharacterizationArtifact
from backtest.data_source import FixtureHistoricalSource
from backtest.engine import BacktestEngine, BacktestRequest

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "candles_BTCUSDT_15m_recorded.json"


def _request() -> BacktestRequest:
    return BacktestRequest(
        strategy_id="ema_alignment_bullish",
        symbol="BTCUSDT",
        period="15m",
        range_from=datetime(2026, 1, 1, tzinfo=UTC),
        range_to=datetime(2026, 12, 31, tzinfo=UTC),
        warmup=125,
    )


@pytest.mark.e2e
def test_backtest_emits_artifact_from_recorded_fixture() -> None:
    engine = BacktestEngine(data_source=FixtureHistoricalSource(FIXTURE_PATH))
    artifact = engine.run(_request())

    assert isinstance(artifact, CharacterizationArtifact)
    assert artifact.strategy_id == "ema_alignment_bullish"
    assert artifact.symbol == "BTCUSDT"
    assert artifact.period == "15m"
    assert artifact.source == "backtest"
    assert artifact.candle_count == 260
    assert artifact.signal_count == len(artifact.events)
    assert artifact.signal_count > 0, (
        "The recorded uptrend fixture must trigger at least one bullish "
        "EMA-alignment signal; zero means the integration regressed."
    )
    # Every emitted event has to carry a decision_id in the contract shape.
    pattern = re.compile(r"^dec_\d{8}T\d{6}\d{3}_[0-9a-f]{6}$")
    for event in artifact.events:
        assert pattern.match(event.decision_id), event.decision_id
        assert event.action in {"buy", "sell", "hold", "close"}
        assert 0.0 <= event.confidence <= 1.0


@pytest.mark.e2e
def test_backtest_is_reproducible() -> None:
    engine_a = BacktestEngine(data_source=FixtureHistoricalSource(FIXTURE_PATH))
    engine_b = BacktestEngine(data_source=FixtureHistoricalSource(FIXTURE_PATH))
    artifact_a = engine_a.run(_request())
    artifact_b = engine_b.run(_request())
    assert artifact_a.to_json() == artifact_b.to_json()


@pytest.mark.e2e
def test_backtest_rejects_unknown_strategy() -> None:
    engine = BacktestEngine(data_source=FixtureHistoricalSource(FIXTURE_PATH))
    bad = BacktestRequest(
        strategy_id="no_such_strategy",
        symbol="BTCUSDT",
        period="15m",
        range_from=datetime(2026, 1, 1, tzinfo=UTC),
        range_to=datetime(2026, 12, 31, tzinfo=UTC),
        warmup=60,
    )
    with pytest.raises(ValueError, match="Unknown strategy_id") as exc_info:
        engine.run(bad)
    assert "no_such_strategy" in str(exc_info.value)


@pytest.mark.e2e
def test_backtest_handles_short_window() -> None:
    """If the loaded candle count is <= warmup, the artifact is empty."""
    engine = BacktestEngine(data_source=FixtureHistoricalSource(FIXTURE_PATH))
    req = BacktestRequest(
        strategy_id="momentum_pulse",
        symbol="BTCUSDT",
        period="15m",
        range_from=datetime(2026, 1, 1, tzinfo=UTC),
        range_to=datetime(2026, 12, 31, tzinfo=UTC),
        warmup=10_000,
    )
    artifact = engine.run(req)
    assert artifact.signal_count == 0
    assert artifact.events == []
