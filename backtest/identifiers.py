"""Deterministic `decision_id` generation for backtest events.

The cross-service identifier contract
(`petrosa_k8s/docs/cross-service-identifier-contract.md`) prescribes
`dec_{compact_ts}_{6hex}` for production decisions. CIO assigns these from
wall-clock + RNG. Backtests need byte-identical reruns (FR4), so the random
suffix is replaced with a SHA-256-derived 6-hex digest of the candle anchor.
The on-the-wire shape is unchanged, so downstream consumers (audit evaluator,
Grafana queries) cannot tell a backtest decision from a live one by shape
alone — only by inspecting the `source` field on the event payload.
"""

from __future__ import annotations

import hashlib
from datetime import datetime


def _compact_timestamp(ts: datetime) -> str:
    """Format like the contract examples: `20260601T143201123`."""
    return ts.strftime("%Y%m%dT%H%M%S") + f"{ts.microsecond // 1000:03d}"


def make_decision_id(
    *,
    strategy_id: str,
    symbol: str,
    candle_timestamp: datetime,
    sequence: int,
) -> str:
    """Return a contract-conformant, deterministic `decision_id`.

    Two calls with the same `(strategy_id, symbol, candle_timestamp, sequence)`
    produce byte-identical output — this is the reproducibility guarantee.
    """
    if sequence < 0:
        raise ValueError("sequence must be >= 0")
    anchor = f"{strategy_id}|{symbol}|{candle_timestamp.isoformat()}|{sequence}"
    digest = hashlib.sha256(anchor.encode("utf-8")).hexdigest()[:6]
    return f"dec_{_compact_timestamp(candle_timestamp)}_{digest}"
