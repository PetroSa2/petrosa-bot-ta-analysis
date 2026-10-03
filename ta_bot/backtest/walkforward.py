"""Rolling train/test windows for backtest trade lists."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from typing import Any


def _time(trade: Any) -> datetime:
    value = trade.get("exit_time") if isinstance(trade, dict) else trade.exit_time
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)


def walk_forward(
    trades: Iterable[Any],
    *,
    train_days: int,
    test_days: int,
    step_days: int,
    summarize: Callable[[list[Any]], Any] | None = None,
) -> list[dict[str, Any]]:
    """Return disjoint test-window reports without fitting or simulating train data."""
    if min(train_days, test_days, step_days) <= 0 or step_days < test_days:
        raise ValueError("train_days, test_days, and step_days must be positive")
    items = sorted(trades, key=_time)
    if not items:
        return []
    first = _time(items[0]).replace(hour=0, minute=0, second=0, microsecond=0)
    last = _time(items[-1])
    cursor = first + timedelta(days=train_days)
    reports: list[dict[str, Any]] = []
    while cursor < last:
        test_end = cursor + timedelta(days=test_days)
        train_start = cursor - timedelta(days=train_days)
        train = [trade for trade in items if train_start <= _time(trade) < cursor]
        test = [trade for trade in items if cursor <= _time(trade) < test_end]
        if test:
            reports.append(
                {
                    "train_start": train_start.isoformat(),
                    "train_end": cursor.isoformat(),
                    "test_start": cursor.isoformat(),
                    "test_end": test_end.isoformat(),
                    "n_train": len(train),
                    "n_test": len(test),
                    "in_sample": summarize(train) if summarize else train,
                    "out_of_sample": summarize(test) if summarize else test,
                    "test_trades": test,
                }
            )
        cursor += timedelta(days=step_days)
    return reports
