"""Artifact serialization tests."""

from __future__ import annotations

import json

import pytest

from backtest.artifact import BacktestEvent, CharacterizationArtifact


def _artifact() -> CharacterizationArtifact:
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
        events=[
            BacktestEvent(
                decision_id="dec_20260101T000000000_abc123",
                candle_timestamp="2026-01-01T00:00:00+00:00",
                action="buy",
                confidence=0.74,
                current_price=50000.0,
                metadata={"strength": "medium"},
            )
        ],
    )


@pytest.mark.unit
def test_to_json_is_stable() -> None:
    payload_a = _artifact().to_json()
    payload_b = _artifact().to_json()
    assert payload_a == payload_b
    parsed = json.loads(payload_a)
    assert parsed["events"][0]["decision_id"] == "dec_20260101T000000000_abc123"
    assert parsed["signal_count"] == 1
    assert parsed["source"] == "backtest"


@pytest.mark.unit
def test_write_json_creates_parent_dir(tmp_path) -> None:
    out = tmp_path / "nested" / "report.json"
    _artifact().write_json(out)
    assert out.exists()
    on_disk = json.loads(out.read_text())
    assert on_disk["strategy_id"] == "momentum_pulse"
