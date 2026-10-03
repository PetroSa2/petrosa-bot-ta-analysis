"""Daily P&L correlation for symbols and strategies."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from math import sqrt
from typing import Any


def _field(trade: Any, name: str) -> str:
    value = trade.get(name) if isinstance(trade, dict) else getattr(trade, name, None)
    return str(value if value is not None else "unknown")


def _date(trade: Any) -> datetime.date:
    value = _field(trade, "exit_time")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC).date()


def _pnl(trade: Any) -> Decimal:
    return Decimal(_field(trade, "net_pnl"))


def _pearson(left: list[Decimal], right: list[Decimal]) -> float:
    if len(left) < 2 or len(left) != len(right):
        return 0.0
    left_mean = sum(left, Decimal(0)) / len(left)
    right_mean = sum(right, Decimal(0)) / len(right)
    numerator = sum(
        (a - left_mean) * (b - right_mean) for a, b in zip(left, right, strict=True)
    )
    left_var = sum((a - left_mean) ** 2 for a in left)
    right_var = sum((b - right_mean) ** 2 for b in right)
    if not left_var or not right_var:
        return 1.0 if left == right else 0.0
    return float(numerator / Decimal(str(sqrt(float(left_var * right_var)))))


def daily_pnl_correlation(
    trades: Iterable[Any], *, group_by: str = "symbol"
) -> dict[str, Any]:
    """Aggregate net P&L by UTC day and return pairwise correlations."""
    grouped: dict[str, dict[object, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for trade in trades:
        grouped[_field(trade, group_by)][_date(trade)] += _pnl(trade)
    if not grouped:
        return {"group_by": group_by, "n_days": 0, "series": {}, "correlations": {}}
    first = min(day for values in grouped.values() for day in values)
    last = max(day for values in grouped.values() for day in values)
    calendar = []
    day = first
    while day <= last:
        calendar.append(day)
        day += timedelta(days=1)
    names = sorted(grouped)
    series = {name: [str(grouped[name].get(day, Decimal(0))) for day in calendar] for name in names}
    correlations: dict[str, float] = {}
    matrix = {name: {other: (1.0 if name == other else 0.0) for other in names} for name in names}
    for index, left_name in enumerate(names):
        for right_name in names[index + 1 :]:
            left = [Decimal(value) for value in series[left_name]]
            right = [Decimal(value) for value in series[right_name]]
            value = _pearson(left, right)
            correlations[f"{left_name}|{right_name}"] = value
            matrix[left_name][right_name] = value
            matrix[right_name][left_name] = value
    return {
        "group_by": group_by,
        "n_days": len(calendar),
        "series": series,
        "correlations": correlations,
        "matrix": matrix,
    }


correlation_matrix = daily_pnl_correlation
