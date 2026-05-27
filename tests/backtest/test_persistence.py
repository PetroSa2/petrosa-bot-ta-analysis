"""Unit tests for backtest.persistence (AC5 — data-manager audit trail)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backtest.artifact import BacktestEvent, CharacterizationArtifact
from backtest.persistence import _COLLECTION, _DATABASE, _DEFAULT_URL, ArtifactPersister


def _simple_artifact() -> CharacterizationArtifact:
    return CharacterizationArtifact(
        schema_version="1.1.0",
        strategy_id="test_strategy",
        symbol="BTCUSDT",
        period="15m",
        range_from="2026-01-01T00:00:00+00:00",
        range_to="2026-01-02T00:00:00+00:00",
        candle_count=100,
        signal_count=1,
        source="backtest",
        events=(
            BacktestEvent(
                decision_id="dec_20260101T000000000_abc123",
                candle_timestamp="2026-01-01T00:00:00+00:00",
                action="buy",
                confidence=0.8,
                current_price=50000.0,
                metadata={},
            ),
        ),
    )


@pytest.mark.unit
def test_persister_uses_default_url_when_no_env(monkeypatch) -> None:
    monkeypatch.delenv("DATA_MANAGER_URL", raising=False)
    p = ArtifactPersister()
    assert p._base_url == _DEFAULT_URL


@pytest.mark.unit
def test_persister_reads_url_from_env(monkeypatch) -> None:
    monkeypatch.setenv("DATA_MANAGER_URL", "http://custom-dm:8080")
    p = ArtifactPersister()
    assert p._base_url == "http://custom-dm:8080"


@pytest.mark.unit
def test_persister_custom_url_kwarg() -> None:
    p = ArtifactPersister(base_url="http://override:9999")
    assert p._base_url == "http://override:9999"


@pytest.mark.unit
def test_build_record_contains_artifact_key() -> None:
    artifact = _simple_artifact()
    p = ArtifactPersister()
    record = p._build_record(artifact)
    assert "_artifact_key" in record
    key = record["_artifact_key"]
    assert "test_strategy" in key
    assert "BTCUSDT" in key
    assert "15m" in key


@pytest.mark.unit
def test_build_record_roundtrips_all_fields() -> None:
    artifact = _simple_artifact()
    p = ArtifactPersister()
    record = p._build_record(artifact)
    assert record["schema_version"] == "1.1.0"
    assert record["strategy_id"] == "test_strategy"
    assert record["signal_count"] == 1
    assert len(record["events"]) == 1


@pytest.mark.unit
def test_persist_returns_false_on_runtime_error() -> None:
    """persist() must not raise when called from within an event loop."""
    p = ArtifactPersister(base_url="http://unreachable")

    # Simulate being inside a running event loop by patching asyncio.run
    with patch("backtest.persistence.asyncio.run", side_effect=RuntimeError("loop")):
        result = p.persist(_simple_artifact())

    assert result is False


def _make_mock_client(*, insert_return: dict) -> MagicMock:
    mock_inner = AsyncMock()
    mock_inner.insert = AsyncMock(return_value=insert_return)
    client = MagicMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client._client = mock_inner
    return client


@pytest.mark.unit
def test_apersist_success() -> None:
    """apersist() returns True when data-manager reports inserted_count > 0."""
    artifact = _simple_artifact()
    mock_client = _make_mock_client(insert_return={"inserted_count": 1})
    p = ArtifactPersister(
        base_url="http://mock-dm", _client_factory=lambda **_: mock_client
    )

    result = asyncio.run(p.apersist(artifact))

    assert result is True
    mock_client._client.insert.assert_called_once()
    call_kwargs = mock_client._client.insert.call_args.kwargs
    assert call_kwargs["database"] == _DATABASE
    assert call_kwargs["collection"] == _COLLECTION


@pytest.mark.unit
def test_apersist_returns_false_when_zero_inserted() -> None:
    artifact = _simple_artifact()
    mock_client = _make_mock_client(insert_return={"inserted_count": 0})
    p = ArtifactPersister(
        base_url="http://mock-dm", _client_factory=lambda **_: mock_client
    )

    result = asyncio.run(p.apersist(artifact))

    assert result is False


@pytest.mark.unit
def test_apersist_returns_false_on_connection_error() -> None:
    artifact = _simple_artifact()
    mock_client = MagicMock()
    mock_client.connect = AsyncMock(side_effect=ConnectionError("refused"))
    mock_client.disconnect = AsyncMock()
    p = ArtifactPersister(
        base_url="http://unreachable", _client_factory=lambda **_: mock_client
    )

    result = asyncio.run(p.apersist(artifact))

    assert result is False


@pytest.mark.unit
def test_persist_uses_asyncio_run(monkeypatch) -> None:
    """persist() calls asyncio.run(apersist(...)) under the hood."""
    artifact = _simple_artifact()
    p = ArtifactPersister(base_url="http://mock-dm")

    with patch("backtest.persistence.asyncio.run", return_value=True) as mock_run:
        result = p.persist(artifact)

    assert result is True
    mock_run.assert_called_once()
