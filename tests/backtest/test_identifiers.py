"""Decision-id contract + determinism tests."""

from __future__ import annotations

import re
from datetime import UTC, datetime

import pytest

from backtest.identifiers import make_decision_id

_CONTRACT_PATTERN = re.compile(r"^dec_\d{8}T\d{6}\d{3}_[0-9a-f]{6}$")


def _ts() -> datetime:
    return datetime(2026, 6, 1, 14, 32, 1, 123_000, tzinfo=UTC)


@pytest.mark.unit
def test_decision_id_matches_contract_shape() -> None:
    decision_id = make_decision_id(
        strategy_id="momentum_pulse",
        symbol="BTCUSDT",
        candle_timestamp=_ts(),
        sequence=0,
    )
    assert _CONTRACT_PATTERN.match(decision_id), decision_id


@pytest.mark.unit
def test_decision_id_is_deterministic() -> None:
    kwargs = {
        "strategy_id": "momentum_pulse",
        "symbol": "BTCUSDT",
        "candle_timestamp": _ts(),
        "sequence": 7,
    }
    assert make_decision_id(**kwargs) == make_decision_id(**kwargs)


@pytest.mark.unit
def test_decision_id_changes_with_inputs() -> None:
    base = make_decision_id(
        strategy_id="momentum_pulse",
        symbol="BTCUSDT",
        candle_timestamp=_ts(),
        sequence=0,
    )
    other_symbol = make_decision_id(
        strategy_id="momentum_pulse",
        symbol="ETHUSDT",
        candle_timestamp=_ts(),
        sequence=0,
    )
    other_seq = make_decision_id(
        strategy_id="momentum_pulse",
        symbol="BTCUSDT",
        candle_timestamp=_ts(),
        sequence=1,
    )
    assert base != other_symbol
    assert base != other_seq


@pytest.mark.unit
def test_decision_id_rejects_negative_sequence() -> None:
    with pytest.raises(ValueError, match="sequence must be") as exc_info:
        make_decision_id(
            strategy_id="momentum_pulse",
            symbol="BTCUSDT",
            candle_timestamp=_ts(),
            sequence=-1,
        )
    assert "sequence" in str(exc_info.value)
