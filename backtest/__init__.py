"""Backtest engine for petrosa-bot-ta-analysis (P3.1 MVP).

Replays historical candles for a registered TA strategy and emits a
characterization artifact consumable by the P3.2 evaluator.
"""

from backtest.artifact import BacktestEvent, CharacterizationArtifact
from backtest.data_source import (
    DataManagerHistoricalSource,
    FixtureHistoricalSource,
    HistoricalDataSource,
)
from backtest.engine import BacktestEngine
from backtest.identifiers import make_decision_id

__all__ = [
    "BacktestEngine",
    "BacktestEvent",
    "CharacterizationArtifact",
    "DataManagerHistoricalSource",
    "FixtureHistoricalSource",
    "HistoricalDataSource",
    "make_decision_id",
]
