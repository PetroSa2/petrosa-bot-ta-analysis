"""Deterministic bar-by-bar trade simulation."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pandas as pd

from ta_bot.backtest.config import BacktestConfig

BP = Decimal("10000")


@dataclass
class Trade:
    side: str
    signal_time: str
    entry_time: str
    entry_price: str
    exit_time: str
    exit_price: str
    gross_pnl: str
    fees: str
    slippage: str
    funding: str
    net_pnl: str
    initial_risk: str
    exit_reason: str
    open_at_end: bool = False


@dataclass
class BacktestResult:
    trades: list[Trade]
    parameters: dict[str, str | int]
    gaps: list[str]

    def to_dict(self) -> dict[str, Any]:
        gross = sum((Decimal(t.gross_pnl) for t in self.trades), Decimal(0))
        fees = sum((Decimal(t.fees) for t in self.trades), Decimal(0))
        slippage = sum((Decimal(t.slippage) for t in self.trades), Decimal(0))
        funding = sum((Decimal(t.funding) for t in self.trades), Decimal(0))
        net = sum((Decimal(t.net_pnl) for t in self.trades), Decimal(0))
        winners = sum(Decimal(t.net_pnl) > 0 for t in self.trades)
        risks = sum((Decimal(t.initial_risk) for t in self.trades), Decimal(0))
        expectancy_r = net / risks if risks else Decimal(0)
        best = max((Decimal(t.net_pnl) for t in self.trades), default=Decimal(0))
        remainder = [Decimal(t.net_pnl) for t in self.trades]
        if remainder:
            remainder.remove(best)
        return {
            "trades": [asdict(trade) for trade in self.trades],
            "n_trades": len(self.trades),
            "gross_pnl": str(gross),
            "fees": str(fees),
            "slippage": str(slippage),
            "funding": str(funding),
            "net_pnl": str(net),
            "win_rate": str(
                Decimal(winners) / len(self.trades) if self.trades else Decimal(0)
            ),
            "payoff": str(
                (
                    sum(value for value in remainder if value > 0)
                    / sum(-value for value in remainder if value < 0)
                )
                if any(value < 0 for value in remainder)
                else Decimal(0)
            ),
            "expectancy_net": str(
                net / len(self.trades) if self.trades else Decimal(0)
            ),
            "expectancy_net_r": str(expectancy_r),
            "expectancy_ex_top1": str(
                sum(remainder, Decimal(0)) / len(remainder) if remainder else Decimal(0)
            ),
            "max_drawdown": str(_max_drawdown(self.trades)),
            "fee_share": str(fees / gross if gross else Decimal(0)),
            "cost_share": str(
                (fees + slippage + funding) / gross if gross else Decimal(0)
            ),
            "parameters": self.parameters,
            "gaps": self.gaps,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)


def simulate(
    candles: pd.DataFrame,
    strategy: Callable[[pd.DataFrame], Any],
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """Run a strategy against closed candles only.

    A strategy may return a Signal, a mapping, or None. Mapping keys are
    ``action``, ``stop_loss`` and ``take_profit``.
    """
    config = config or BacktestConfig()
    frame = candles.sort_index()
    if "timestamp" in frame.columns:
        frame = frame.copy()
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        frame = frame.sort_values("timestamp").set_index("timestamp")
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError("candles must be indexed by timestamp")
    trades: list[Trade] = []
    position: dict[str, Any] | None = None
    for index in range(max(0, len(frame) - 1)):
        bar = frame.iloc[index]
        if position is not None:
            if _exit_position(
                position, frame.iloc[index + 1], frame.index[index + 1], config, trades
            ):
                position = None
            elif (
                config.time_stop_bars
                and index + 1 - position["entry_index"] >= config.time_stop_bars
            ):
                _close(
                    position,
                    Decimal(str(frame.iloc[index + 1].close)),
                    frame.index[index + 1],
                    "time_stop",
                    config,
                    trades,
                )
                position = None
        if position is None:
            signal = strategy(frame.iloc[: index + 1].copy())
            action = (
                signal.get("action")
                if isinstance(signal, dict)
                else getattr(signal, "action", None)
            )
            if action not in ("buy", "sell"):
                continue
            entry = frame.iloc[index + 1]
            position = {
                "side": action,
                "signal_time": frame.index[index].isoformat(),
                "entry_index": index + 1,
                "entry_time": frame.index[index + 1].isoformat(),
                "entry": Decimal(str(entry.open)),
                "stop": Decimal(
                    str(
                        signal.get("stop_loss")
                        if isinstance(signal, dict)
                        else signal.stop_loss
                    )
                ),
                "target": Decimal(
                    str(
                        signal.get("take_profit")
                        if isinstance(signal, dict)
                        else signal.take_profit
                    )
                ),
            }
    if position is not None:
        last = frame.iloc[-1]
        _close(
            position,
            Decimal(str(last.close)),
            frame.index[-1],
            "mark_to_market",
            config,
            trades,
            open_at_end=True,
        )
    return BacktestResult(trades, config.as_dict(), [])


def _exit_position(position, bar, timestamp, config, trades) -> bool:
    high, low = Decimal(str(bar.high)), Decimal(str(bar.low))
    if position["side"] == "buy":
        if low <= position["stop"]:
            _close(position, position["stop"], timestamp, "stop_loss", config, trades)
            return True
        if high >= position["target"]:
            _close(
                position, position["target"], timestamp, "take_profit", config, trades
            )
            return True
    else:
        if high >= position["stop"]:
            _close(position, position["stop"], timestamp, "stop_loss", config, trades)
            return True
        if low <= position["target"]:
            _close(
                position, position["target"], timestamp, "take_profit", config, trades
            )
            return True
    return False


def _close(
    position, exit_price, timestamp, reason, config, trades, open_at_end=False
) -> None:
    entry, exit_price = position["entry"], Decimal(exit_price)
    direction = Decimal(1) if position["side"] == "buy" else Decimal(-1)
    gross = (exit_price - entry) * direction * config.notional / entry
    fee_rate = config.fee_bp_per_side / BP
    slippage_rate = config.slippage_bp / BP
    fees = config.notional * fee_rate * 2
    slippage = config.notional * slippage_rate * 2
    marks = _funding_marks(position["entry_time"], timestamp)
    funding = config.notional * config.funding_bp / BP * len(marks)
    initial_risk = abs(entry - position["stop"]) * config.notional / entry
    trades.append(
        Trade(
            position["side"],
            position["signal_time"],
            position["entry_time"],
            str(entry),
            timestamp.isoformat(),
            str(exit_price),
            str(gross),
            str(fees),
            str(slippage),
            str(funding),
            str(gross - fees - slippage - funding),
            str(initial_risk),
            reason,
            open_at_end,
        )
    )


def _funding_marks(entry: str, exit_time: datetime) -> list[datetime]:
    start = datetime.fromisoformat(entry).astimezone(UTC)
    mark = start.replace(hour=0, minute=0, second=0, microsecond=0)
    if mark <= start:
        mark += timedelta(hours=8)
    marks = []
    while mark <= exit_time:
        marks.append(mark)
        mark += timedelta(hours=8)
    return marks


def _max_drawdown(trades: list[Trade]) -> Decimal:
    equity = peak = drawdown = Decimal(0)
    for trade in trades:
        equity += Decimal(trade.net_pnl)
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown
