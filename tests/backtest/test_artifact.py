"""Artifact serialization tests — covers v1.0.0 and v1.1.0 shapes."""

from __future__ import annotations

import json

import pytest

from backtest.artifact import (
    BacktestEvent,
    CharacterizationArtifact,
    DrawdownEnvelope,
    EdgeEstimate,
    SensitivityAnalysis,
    SensitivityPoint,
)
from backtest.strategy_revision import StrategyRevision


def _v1_artifact() -> CharacterizationArtifact:
    return CharacterizationArtifact(
        schema_version="1.0.0",
        strategy_id="momentum_pulse",
        symbol="BTCUSDT",
        period="15m",
        range_from="2026-01-01T00:00:00+00:00",
        range_to="2026-01-05T00:00:00+00:00",
        candle_count=4,
        signal_count=1,
        source="backtest",
        events=(
            BacktestEvent(
                decision_id="dec_20260101T000000000_abc123",
                candle_timestamp="2026-01-01T00:00:00+00:00",
                action="buy",
                confidence=0.74,
                current_price=50000.0,
                metadata={"strength": "medium"},
            ),
        ),
    )


def _v2_artifact() -> CharacterizationArtifact:
    return CharacterizationArtifact(
        schema_version="1.1.0",
        strategy_id="momentum_pulse",
        symbol="BTCUSDT",
        period="15m",
        range_from="2026-01-01T00:00:00+00:00",
        range_to="2026-01-05T00:00:00+00:00",
        candle_count=4,
        signal_count=2,
        source="backtest",
        events=(
            BacktestEvent(
                decision_id="dec_20260101T000000000_abc123",
                candle_timestamp="2026-01-01T00:00:00+00:00",
                action="buy",
                confidence=0.74,
                current_price=50000.0,
                metadata={},
            ),
            BacktestEvent(
                decision_id="dec_20260101T000000001_abc124",
                candle_timestamp="2026-01-02T00:00:00+00:00",
                action="sell",
                confidence=0.80,
                current_price=51000.0,
                metadata={},
            ),
        ),
        edge_estimate=EdgeEstimate(
            expected_pnl=0.02, win_rate=1.0, sharpe_ratio=0.0, trade_count=1
        ),
        drawdown_envelope=DrawdownEnvelope(p50=0.0, p90=0.0, p99=0.0, p100=0.0),
        sensitivity_analysis=SensitivityAnalysis(
            parameter="confidence_threshold",
            points=(
                SensitivityPoint(
                    confidence_threshold=0.0,
                    win_rate=1.0,
                    expected_pnl=0.02,
                    trade_count=1,
                ),
            ),
        ),
    )


@pytest.mark.unit
def test_v1_to_json_is_stable() -> None:
    artifact = _v1_artifact()
    payload_a = artifact.to_json()
    payload_b = artifact.to_json()
    assert payload_a == payload_b
    parsed = json.loads(payload_a)
    assert parsed["events"][0]["decision_id"] == "dec_20260101T000000000_abc123"
    assert parsed["signal_count"] == 1
    assert parsed["source"] == "backtest"
    assert parsed["edge_estimate"] is None
    assert parsed["drawdown_envelope"] is None
    assert parsed["sensitivity_analysis"] is None


@pytest.mark.unit
def test_v2_to_json_contains_analytic_fields() -> None:
    artifact = _v2_artifact()
    parsed = json.loads(artifact.to_json())
    assert parsed["schema_version"] == "1.1.0"
    assert parsed["edge_estimate"]["trade_count"] == 1
    assert parsed["edge_estimate"]["win_rate"] == 1.0
    assert parsed["drawdown_envelope"]["p50"] == 0.0
    assert parsed["sensitivity_analysis"]["parameter"] == "confidence_threshold"
    assert len(parsed["sensitivity_analysis"]["points"]) == 1


@pytest.mark.unit
def test_from_dict_roundtrip_v1() -> None:
    artifact = _v1_artifact()
    restored = CharacterizationArtifact.from_dict(json.loads(artifact.to_json()))
    assert restored.schema_version == "1.0.0"
    assert restored.strategy_id == artifact.strategy_id
    assert len(restored.events) == 1
    assert restored.edge_estimate is None
    assert restored.drawdown_envelope is None
    assert restored.sensitivity_analysis is None


@pytest.mark.unit
def test_from_dict_roundtrip_v2() -> None:
    artifact = _v2_artifact()
    restored = CharacterizationArtifact.from_dict(json.loads(artifact.to_json()))
    assert restored.schema_version == "1.1.0"
    assert restored.edge_estimate is not None
    assert restored.edge_estimate.trade_count == 1
    assert restored.drawdown_envelope is not None
    assert restored.sensitivity_analysis is not None
    assert restored.sensitivity_analysis.parameter == "confidence_threshold"


@pytest.mark.unit
def test_from_json_roundtrip_v2() -> None:
    artifact = _v2_artifact()
    restored = CharacterizationArtifact.from_json(artifact.to_json())
    assert restored == artifact


@pytest.mark.unit
def test_write_json_creates_parent_dir(tmp_path) -> None:
    out = tmp_path / "nested" / "report.json"
    _v1_artifact().write_json(out)
    assert out.exists()
    on_disk = json.loads(out.read_text())
    assert on_disk["strategy_id"] == "momentum_pulse"


def _v3_artifact_with_revision() -> CharacterizationArtifact:
    return CharacterizationArtifact(
        schema_version="1.2.0",
        strategy_id="momentum_pulse",
        symbol="BTCUSDT",
        period="15m",
        range_from="2026-01-01T00:00:00+00:00",
        range_to="2026-01-05T00:00:00+00:00",
        candle_count=4,
        signal_count=1,
        source="backtest",
        events=(
            BacktestEvent(
                decision_id="dec_20260101T000000000_abc123",
                candle_timestamp="2026-01-01T00:00:00+00:00",
                action="buy",
                confidence=0.74,
                current_price=50000.0,
                metadata={},
            ),
        ),
        edge_estimate=EdgeEstimate(
            expected_pnl=0.02, win_rate=1.0, sharpe_ratio=0.0, trade_count=1
        ),
        drawdown_envelope=DrawdownEnvelope(p50=0.0, p90=0.0, p99=0.0, p100=0.0),
        sensitivity_analysis=SensitivityAnalysis(
            parameter="confidence_threshold",
            points=(
                SensitivityPoint(
                    confidence_threshold=0.0,
                    win_rate=1.0,
                    expected_pnl=0.02,
                    trade_count=1,
                ),
            ),
        ),
        strategy_revision_id="srev_abc123abc123_def456def456",
        strategy_revision=StrategyRevision(
            strategy_id="momentum_pulse",
            revision_id="srev_abc123abc123_def456def456",
            module_hash="abc123abc123" + "0" * 52,
            parameter_hash="def456def456" + "0" * 52,
        ),
    )


@pytest.mark.unit
def test_v3_to_json_contains_revision_fields() -> None:
    artifact = _v3_artifact_with_revision()
    parsed = json.loads(artifact.to_json())
    assert parsed["schema_version"] == "1.2.0"
    assert parsed["strategy_revision_id"] == "srev_abc123abc123_def456def456"
    assert parsed["strategy_revision"]["module_hash"].startswith("abc123abc123")
    assert parsed["strategy_revision"]["parameter_hash"].startswith("def456def456")


@pytest.mark.unit
def test_v3_from_json_roundtrip() -> None:
    artifact = _v3_artifact_with_revision()
    restored = CharacterizationArtifact.from_json(artifact.to_json())
    assert restored == artifact


@pytest.mark.unit
def test_legacy_v1_load_leaves_revision_none() -> None:
    artifact = _v1_artifact()
    restored = CharacterizationArtifact.from_dict(json.loads(artifact.to_json()))
    assert restored.strategy_revision_id is None
    assert restored.strategy_revision is None
