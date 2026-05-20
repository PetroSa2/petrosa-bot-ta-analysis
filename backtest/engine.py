"""Backtest engine: replay candles, drive one strategy, collect events.

The engine reuses the existing `ta_bot.core.signal_engine.SignalEngine` so
the same indicators, the same strategy-resolution path, and the same `Signal`
shape that runs in production also run in backtest — there is no parallel
implementation drifting from the live system.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd

from backtest.artifact import BacktestEvent, CharacterizationArtifact
from backtest.data_source import HistoricalDataSource
from backtest.identifiers import make_decision_id

ARTIFACT_SCHEMA_VERSION = "1.0.0"
BACKTEST_SOURCE = "backtest"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BacktestRequest:
    strategy_id: str
    symbol: str
    period: str
    range_from: datetime
    range_to: datetime
    warmup: int = 200


class BacktestEngine:
    """Drive a single registered strategy over a candle window.

    The engine is deliberately small: it owns the iteration shape and the
    artifact-construction logic, and delegates indicator math + strategy
    selection back to `SignalEngine.analyze_candles(enabled_strategies=[id])`.
    Determinism: no wall-clock reads, no RNG; `decision_id` is derived from
    the candle anchor via `make_decision_id`.
    """

    def __init__(self, *, data_source: HistoricalDataSource, signal_engine=None):
        self._data_source = data_source
        self._signal_engine = signal_engine  # lazy-instantiated on first run

    def _ensure_signal_engine(self):
        if self._signal_engine is None:
            from ta_bot.core.signal_engine import SignalEngine

            self._signal_engine = SignalEngine()
        return self._signal_engine

    def run(self, request: BacktestRequest) -> CharacterizationArtifact:
        engine = self._ensure_signal_engine()
        if request.strategy_id not in engine.strategies:
            raise ValueError(
                f"Unknown strategy_id {request.strategy_id!r}. "
                f"Available: {sorted(engine.strategies)}"
            )
        if request.warmup < 1:
            raise ValueError("warmup must be >= 1")

        df = self._data_source.load(
            symbol=request.symbol,
            period=request.period,
            range_from=request.range_from,
            range_to=request.range_to,
        )
        events: list[BacktestEvent] = []
        candle_count = int(len(df))

        if candle_count <= request.warmup:
            logger.info(
                "Not enough candles for warmup: have=%d, warmup=%d",
                candle_count,
                request.warmup,
            )
            return CharacterizationArtifact(
                schema_version=ARTIFACT_SCHEMA_VERSION,
                strategy_id=request.strategy_id,
                symbol=request.symbol,
                period=request.period,
                range_from=request.range_from.isoformat(),
                range_to=request.range_to.isoformat(),
                candle_count=candle_count,
                signal_count=0,
                source=BACKTEST_SOURCE,
                events=[],
            )

        sequence = 0
        for end_idx in range(request.warmup, candle_count + 1):
            window = df.iloc[:end_idx]
            signals = engine.analyze_candles(
                window,
                symbol=request.symbol,
                period=request.period,
                enabled_strategies=[request.strategy_id],
            )
            if not signals:
                continue
            candle_ts = _as_datetime(window.index[-1])
            for signal in signals:
                decision_id = make_decision_id(
                    strategy_id=request.strategy_id,
                    symbol=request.symbol,
                    candle_timestamp=candle_ts,
                    sequence=sequence,
                )
                events.append(
                    BacktestEvent(
                        decision_id=decision_id,
                        candle_timestamp=candle_ts.isoformat(),
                        action=signal.action,
                        confidence=float(signal.confidence),
                        current_price=float(signal.current_price),
                        metadata={
                            "strength": signal.strength.value,
                            "strategy_mode": signal.strategy_mode.value,
                        },
                    )
                )
                sequence += 1

        return CharacterizationArtifact(
            schema_version=ARTIFACT_SCHEMA_VERSION,
            strategy_id=request.strategy_id,
            symbol=request.symbol,
            period=request.period,
            range_from=request.range_from.isoformat(),
            range_to=request.range_to.isoformat(),
            candle_count=candle_count,
            signal_count=len(events),
            source=BACKTEST_SOURCE,
            events=events,
        )


def _as_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return pd.Timestamp(value).to_pydatetime()
