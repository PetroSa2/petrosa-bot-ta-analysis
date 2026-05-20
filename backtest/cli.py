"""`python -m backtest` command-line entry point.

Stdlib `argparse` keeps the dependency footprint zero. The CLI is the
production binding for the engine; tests drive `BacktestEngine` directly with
a `FixtureHistoricalSource` and never spin up argparse.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from backtest.data_source import (
    DataManagerHistoricalSource,
    FixtureHistoricalSource,
    HistoricalDataSource,
)
from backtest.engine import BacktestEngine, BacktestRequest


def _parse_date(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"{value!r} is not an ISO-8601 date (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
        ) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="backtest",
        description=(
            "Replay a registered TA strategy against historical candles "
            "from petrosa-data-manager and emit a characterization artifact."
        ),
    )
    parser.add_argument("--strategy", required=True, help="Registered strategy_id")
    parser.add_argument(
        "--from",
        dest="range_from",
        required=True,
        type=_parse_date,
        help="ISO-8601 start of the date window",
    )
    parser.add_argument(
        "--to",
        dest="range_to",
        required=True,
        type=_parse_date,
        help="ISO-8601 end of the date window",
    )
    parser.add_argument(
        "--symbol", default="BTCUSDT", help="Trading symbol (default BTCUSDT)"
    )
    parser.add_argument("--period", default="15m", help="Candle period (default 15m)")
    parser.add_argument(
        "--warmup",
        type=int,
        default=200,
        help="Minimum candles before strategies are evaluated (default 200)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the artifact JSON to this path (otherwise stdout)",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        help=(
            "Optional fixture JSON path. When supplied, the engine reads "
            "candles from disk instead of petrosa-data-manager."
        ),
    )
    parser.add_argument(
        "--max-candles",
        type=int,
        default=1000,
        help="Cap on data-manager fetches (live mode only, default 1000)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser


def _resolve_data_source(args: argparse.Namespace) -> HistoricalDataSource:
    if args.fixture is not None:
        return FixtureHistoricalSource(args.fixture)
    return DataManagerHistoricalSource(max_candles=args.max_candles)


def run(args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )
    if args.range_to < args.range_from:
        print("error: --to must be on or after --from", file=sys.stderr)
        return 2

    data_source = _resolve_data_source(args)
    engine = BacktestEngine(data_source=data_source)
    request = BacktestRequest(
        strategy_id=args.strategy,
        symbol=args.symbol,
        period=args.period,
        range_from=args.range_from,
        range_to=args.range_to,
        warmup=args.warmup,
    )
    artifact = engine.run(request)

    payload = artifact.to_json()
    if args.output is not None:
        artifact.write_json(args.output)
        print(f"wrote {artifact.signal_count} events to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(payload + "\n")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except Exception as exc:  # noqa: BLE001
        print(f"backtest failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover - thin wrapper
    raise SystemExit(main())
