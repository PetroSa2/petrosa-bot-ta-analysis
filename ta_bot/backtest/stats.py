"""Uncertainty statistics for backtest trade lists."""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any


def _value(trade: Any) -> Decimal:
    value = trade.get("net_pnl") if isinstance(trade, dict) else trade.net_pnl
    return Decimal(str(value))


def _time(trade: Any) -> datetime:
    value = trade.get("exit_time") if isinstance(trade, dict) else trade.exit_time
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)


def _quantile(values: list[Decimal], probability: float) -> Decimal:
    values = sorted(values)
    if not values:
        return Decimal(0)
    position = (len(values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = Decimal(str(position - lower))
    return values[lower] + (values[upper] - values[lower]) * fraction


def block_bootstrap_expectancy_ci(
    trades: Iterable[Any],
    *,
    seed: int = 0,
    n_boot: int = 1000,
    min_trades: int = 1,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Return a seeded confidence interval using UTC-day blocks.

    A bootstrap draw samples complete UTC days with replacement, preserving all
    trades that occurred on each selected day.
    """
    if n_boot < 1:
        raise ValueError("n_boot must be positive")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    items = list(trades)
    by_day: dict[object, list[Decimal]] = defaultdict(list)
    for trade in items:
        by_day[_time(trade).date()].append(_value(trade))
    days = list(by_day.values())
    point = (
        sum((_value(trade) for trade in items), Decimal(0)) / len(items)
        if items
        else Decimal(0)
    )
    samples: list[Decimal] = []
    rng = random.Random(seed)
    for _ in range(n_boot):
        selected = [rng.choice(days) for _ in days] if days else []
        values = [value for day in selected for value in day]
        samples.append(sum(values, Decimal(0)) / len(values) if values else Decimal(0))
    alpha = (1.0 - confidence) / 2.0
    return {
        "expectancy_net": str(point),
        "ci": [str(_quantile(samples, alpha)), str(_quantile(samples, 1.0 - alpha))],
        "confidence": confidence,
        "seed": seed,
        "n_boot": n_boot,
        "n_trades": len(items),
        "n_days": len(days),
        "bootstrap": "UTC day block",
        "sample_ok": len(items) >= min_trades,
        "min_trades": min_trades,
    }


bootstrap_expectancy_ci = block_bootstrap_expectancy_ci


def independent_bootstrap_expectancy_ci(
    trades: Iterable[Any],
    *,
    seed: int = 0,
    n_boot: int = 1000,
    min_trades: int = 1,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Return the comparison interval that samples individual trades."""
    items = list(trades)
    values = [_value(trade) for trade in items]
    if n_boot < 1:
        raise ValueError("n_boot must be positive")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    rng = random.Random(seed)
    samples = [
        sum((rng.choice(values) for _ in values), Decimal(0)) / len(values)
        if values
        else Decimal(0)
        for _ in range(n_boot)
    ]
    alpha = (1.0 - confidence) / 2.0
    return {
        "expectancy_net": str(
            sum(values, Decimal(0)) / len(values) if values else Decimal(0)
        ),
        "ci": [str(_quantile(samples, alpha)), str(_quantile(samples, 1.0 - alpha))],
        "confidence": confidence,
        "seed": seed,
        "n_boot": n_boot,
        "n_trades": len(items),
        "bootstrap": "independent trades",
        "sample_ok": len(items) >= min_trades,
        "min_trades": min_trades,
    }
