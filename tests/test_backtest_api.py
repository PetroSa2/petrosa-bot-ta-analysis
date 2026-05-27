"""HTTP backtest trigger endpoint tests (#239, FR2).

Drives the real BacktestEngine over the recorded 260-candle fixture through the
FastAPI endpoint and asserts the CharacterizationArtifact is persisted to
petrosa-data-manager (AC5). Persistence is mocked at the data-manager boundary
so the test needs no external services; the data source is swapped for the
recorded fixture so the engine runs end-to-end.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backtest.artifact import CharacterizationArtifact
from backtest.data_source import FixtureHistoricalSource
from ta_bot.health import app

FIXTURE_PATH = (
    Path(__file__).parent
    / "backtest"
    / "fixtures"
    / "candles_BTCUSDT_15m_recorded.json"
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _fixture_source(*_args, **_kwargs) -> FixtureHistoricalSource:
    """Stand in for DataManagerHistoricalSource so the engine replays the fixture."""
    return FixtureHistoricalSource(FIXTURE_PATH)


def test_trigger_backtest_runs_engine_and_persists(client: TestClient) -> None:
    persist_mock = AsyncMock(return_value=True)
    with (
        patch("backtest.data_source.DataManagerHistoricalSource", _fixture_source),
        patch("backtest.persistence.ArtifactPersister.apersist", persist_mock),
    ):
        resp = client.post(
            "/api/v1/backtest",
            json={
                "strategy_id": "ema_alignment_bullish",
                "from": "2026-01-01T00:00:00",
                "to": "2026-12-31T00:00:00",
                "symbol": "BTCUSDT",
                "period": "15m",
                "warmup": 125,
                "persist": True,
            },
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["strategy_id"] == "ema_alignment_bullish"
    assert data["symbol"] == "BTCUSDT"
    assert data["source"] == "backtest"
    assert data["candle_count"] == 260
    assert data["signal_count"] > 0
    assert data["persisted"] is True

    # AC5: the artifact was handed to the data-manager persister.
    persist_mock.assert_awaited_once()
    persisted_artifact = persist_mock.await_args.args[0]
    assert isinstance(persisted_artifact, CharacterizationArtifact)
    assert persisted_artifact.strategy_id == "ema_alignment_bullish"
    assert persisted_artifact.source == "backtest"


def test_trigger_backtest_can_skip_persistence(client: TestClient) -> None:
    persist_mock = AsyncMock(return_value=True)
    with (
        patch("backtest.data_source.DataManagerHistoricalSource", _fixture_source),
        patch("backtest.persistence.ArtifactPersister.apersist", persist_mock),
    ):
        resp = client.post(
            "/api/v1/backtest",
            json={
                "strategy_id": "ema_alignment_bullish",
                "from": "2026-01-01T00:00:00",
                "to": "2026-12-31T00:00:00",
                "warmup": 125,
                "persist": False,
            },
        )

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["persisted"] is False
    persist_mock.assert_not_awaited()


def test_trigger_backtest_unknown_strategy_returns_422(client: TestClient) -> None:
    with patch("backtest.data_source.DataManagerHistoricalSource", _fixture_source):
        resp = client.post(
            "/api/v1/backtest",
            json={
                "strategy_id": "no_such_strategy",
                "from": "2026-01-01T00:00:00",
                "to": "2026-12-31T00:00:00",
                "warmup": 60,
            },
        )
    assert resp.status_code == 422
    assert "no_such_strategy" in resp.text


def test_trigger_backtest_rejects_parameter_overrides(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/backtest",
        json={
            "strategy_id": "ema_alignment_bullish",
            "from": "2026-01-01T00:00:00",
            "to": "2026-12-31T00:00:00",
            "parameter_overrides": {"rsi_oversold": 25},
        },
    )
    assert resp.status_code == 422
    assert "parameter_overrides" in resp.text


def test_trigger_backtest_to_before_from_returns_422(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/backtest",
        json={
            "strategy_id": "ema_alignment_bullish",
            "from": "2026-12-31T00:00:00",
            "to": "2026-01-01T00:00:00",
        },
    )
    assert resp.status_code == 422
