"""Characterization artifact emitted by the backtest engine.

Schema evolution:
  1.0.0 — per-event signals only (decision_id, action, confidence, price)
  1.1.0 — adds edge_estimate, drawdown_envelope, sensitivity_analysis
           (all three are Optional for backward compat when loading 1.0.0 JSON)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
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
class EdgeEstimate:
    """Summary of per-trade edge derived from backtest events (AC1)."""

    expected_pnl: float  # mean return per completed round-trip trade
    win_rate: float  # fraction of profitable trades (0.0–1.0)
    sharpe_ratio: float  # mean_return / std_return; 0.0 when std is zero
    trade_count: int  # number of completed round-trip trades used


@dataclass(frozen=True)
class DrawdownEnvelope:
    """Characterized drawdown percentiles from the simulated equity curve (AC2).

    Values represent the magnitude of drawdown as a positive fraction
    (e.g. 0.05 = 5% drawdown).  Consumed by FR30 / P4.2 / FR62.
    """

    p50: float
    p90: float
    p99: float
    p100: float  # worst-case drawdown observed


@dataclass(frozen=True)
class SensitivityPoint:
    """Edge metrics at one confidence threshold level."""

    confidence_threshold: float
    win_rate: float
    expected_pnl: float
    trade_count: int


@dataclass(frozen=True)
class SensitivityAnalysis:
    """Strategy edge under confidence-threshold perturbation (AC3)."""

    parameter: str  # always "confidence_threshold" for now
    points: tuple[SensitivityPoint, ...]


@dataclass(frozen=True)
class CharacterizationArtifact:
    """Top-level backtest output.

    v1.0.0 artifacts lack the three analytic fields; load them via
    ``from_dict`` which fills those fields with ``None`` automatically.
    v1.1.0 artifacts always carry all three analytic fields.
    """

    schema_version: str
    strategy_id: str
    symbol: str
    period: str
    range_from: str
    range_to: str
    candle_count: int
    signal_count: int
    source: str
    events: tuple[BacktestEvent, ...]
    # v1.1.0 analytic fields — None only when loading a legacy v1.0.0 artifact
    edge_estimate: EdgeEstimate | None = None
    drawdown_envelope: DrawdownEnvelope | None = None
    sensitivity_analysis: SensitivityAnalysis | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # asdict serialises tuples as lists, which is fine for JSON
        return d

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def write_json(self, path: Path | str, *, indent: int = 2) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.to_json(indent=indent), encoding="utf-8")
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CharacterizationArtifact:
        """Deserialise from a dict; handles both v1.0.0 and v1.1.0 shapes."""
        events = tuple(
            BacktestEvent(**e) if isinstance(e, dict) else e
            for e in data.get("events", [])
        )

        edge_raw = data.get("edge_estimate")
        edge = EdgeEstimate(**edge_raw) if edge_raw else None

        dd_raw = data.get("drawdown_envelope")
        dd = DrawdownEnvelope(**dd_raw) if dd_raw else None

        sa_raw = data.get("sensitivity_analysis")
        if sa_raw:
            pts = tuple(SensitivityPoint(**p) for p in sa_raw.get("points", []))
            sa = SensitivityAnalysis(parameter=sa_raw["parameter"], points=pts)
        else:
            sa = None

        return cls(
            schema_version=data["schema_version"],
            strategy_id=data["strategy_id"],
            symbol=data["symbol"],
            period=data["period"],
            range_from=data["range_from"],
            range_to=data["range_to"],
            candle_count=data["candle_count"],
            signal_count=data["signal_count"],
            source=data["source"],
            events=events,
            edge_estimate=edge,
            drawdown_envelope=dd,
            sensitivity_analysis=sa,
        )

    @classmethod
    def from_json(cls, text: str) -> CharacterizationArtifact:
        return cls.from_dict(json.loads(text))
