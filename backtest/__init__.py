"""Backtest engine for petrosa-bot-ta-analysis (P3.1 MVP).

Replays historical candles for a registered TA strategy and emits a
characterization artifact consumable by the P3.2 evaluator.
"""

from backtest.artifact import (
    BacktestEvent,
    CharacterizationArtifact,
    DrawdownEnvelope,
    EdgeEstimate,
    SensitivityAnalysis,
    SensitivityPoint,
)
from backtest.data_source import (
    DataManagerHistoricalSource,
    FixtureHistoricalSource,
    HistoricalDataSource,
)
from backtest.engine import BacktestEngine
from backtest.identifiers import make_decision_id
from backtest.strategy_revision import (
    StrategyRevision,
    build_strategy_revision,
    compute_parameter_set_hash,
    compute_strategy_module_hash,
    compute_strategy_revision_id,
)

__all__ = [
    "BacktestEngine",
    "BacktestEvent",
    "CharacterizationArtifact",
    "DataManagerHistoricalSource",
    "DrawdownEnvelope",
    "EdgeEstimate",
    "FixtureHistoricalSource",
    "HistoricalDataSource",
    "SensitivityAnalysis",
    "SensitivityPoint",
    "StrategyRevision",
    "build_strategy_revision",
    "compute_parameter_set_hash",
    "compute_strategy_module_hash",
    "compute_strategy_revision_id",
    "make_decision_id",
]
