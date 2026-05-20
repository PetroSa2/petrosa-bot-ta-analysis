"""Characterization artifact emitted by the backtest engine.

The schema and persistence model for P3.2 are still open
(see `petrosa-bot-ta-analysis#233` scope notes); the MVP shape recorded here
is the minimal stable surface the downstream evaluator (P2.3) will need:
strategy/symbol/period identity, the date window, and a flat list of every
signal-bearing event with its `decision_id`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BacktestEvent:
    """One signal-bearing decision emitted during a backtest run."""

    decision_id: str
    candle_timestamp: str
    action: str
    confidence: float
    current_price: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CharacterizationArtifact:
    """Top-level backtest output."""

    schema_version: str
    strategy_id: str
    symbol: str
    period: str
    range_from: str
    range_to: str
    candle_count: int
    signal_count: int
    source: str
    events: list[BacktestEvent]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def write_json(self, path: Path | str, *, indent: int = 2) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.to_json(indent=indent), encoding="utf-8")
        return out


def _isoformat(value: datetime | str) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return value
