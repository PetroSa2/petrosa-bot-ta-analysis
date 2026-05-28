"""FR52 / P1.5-AC1 (#251) — Signal.recommended_leverage producer field.

Parallel to petrosa-realtime-strategies#177. Adds the optional
`recommended_leverage: int | None` field to the bot-ta-analysis Signal
contract so strategies whose characterization yields a max-leverage envelope
can carry the opinion to CIO. `None` (not 0) means "no recommendation".
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ta_bot.models.signal import Signal


def _base_signal_kwargs() -> dict:
    """The minimum required fields to construct a Signal."""
    return {
        "strategy_id": "test_strategy_15m",
        "symbol": "BTCUSDT",
        "action": "buy",
        "confidence": 0.75,
        "current_price": 50000.0,
        "price": 50000.0,
    }


def test_signal_defaults_recommended_leverage_to_none():
    """Producers that don't set the field keep working (AC1.c — backwards-
    compatible default)."""
    signal = Signal(**_base_signal_kwargs())
    assert signal.recommended_leverage is None


def test_signal_accepts_recommended_leverage():
    signal = Signal(**_base_signal_kwargs(), recommended_leverage=5)
    assert signal.recommended_leverage == 5


def test_signal_round_trips_recommended_leverage_through_dump_load():
    """AC1.d — model_dump → Signal(**dumped) preserves the field."""
    original = Signal(**_base_signal_kwargs(), recommended_leverage=3)
    rebuilt = Signal(**original.model_dump())
    assert rebuilt.recommended_leverage == 3


def test_signal_rejects_recommended_leverage_below_one():
    """`ge=1` — 0 is not a valid 'no recommendation' sentinel; callers must
    use None for that semantics."""
    with pytest.raises(ValidationError) as exc_info:
        Signal(**_base_signal_kwargs(), recommended_leverage=0)
    assert "recommended_leverage" in str(exc_info.value)


def test_signal_to_dict_carries_recommended_leverage():
    """`to_dict()` round-trips the field for downstream JSON consumers."""
    signal = Signal(**_base_signal_kwargs(), recommended_leverage=2)
    data = signal.to_dict()
    assert data["recommended_leverage"] == 2


def test_signal_to_dict_defaults_recommended_leverage_to_none():
    """A signal with no leverage opinion serializes the field as None."""
    signal = Signal(**_base_signal_kwargs())
    data = signal.to_dict()
    assert data["recommended_leverage"] is None
