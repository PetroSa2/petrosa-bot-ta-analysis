"""CLI for the point-in-time trade simulator."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from decimal import Decimal

from ta_bot.backtest.config import BacktestConfig
from ta_bot.backtest.data import DataManagerCandleLoader, MissingBarsError
from ta_bot.backtest.simulator import simulate
from ta_bot.core.signal_engine import SignalEngine


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ta_bot.backtest")
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--from", dest="start", required=True)
    parser.add_argument("--to", dest="end", required=True)
    parser.add_argument("--fee-bp-per-side", type=Decimal, default=Decimal("4"))
    parser.add_argument("--slippage-bp", type=Decimal, default=Decimal("0"))
    parser.add_argument("--funding-bp", type=Decimal, default=Decimal("0"))
    parser.add_argument("--notional", type=Decimal, default=Decimal("1000"))
    parser.add_argument("--time-stop-bars", type=int, default=0)
    args = parser.parse_args(argv)
    start = datetime.fromisoformat(args.start)
    end = datetime.fromisoformat(args.end)
    start = start.replace(tzinfo=UTC) if start.tzinfo is None else start.astimezone(UTC)
    end = end.replace(tzinfo=UTC) if end.tzinfo is None else end.astimezone(UTC)
    try:
        candles = DataManagerCandleLoader().load(
            args.symbol, args.timeframe, start, end
        )
    except MissingBarsError as error:
        print(json.dumps({"gaps": error.gaps, "error": str(error)}))
        return 2
    engine = SignalEngine()
    if args.strategy not in engine.strategies:
        parser.error(f"unknown strategy: {args.strategy}")

    def strategy(window):
        signals = engine.analyze_candles(
            window, args.symbol, args.timeframe, [args.strategy]
        )
        return signals[0] if signals else None

    result = simulate(
        candles,
        strategy,
        BacktestConfig(
            args.fee_bp_per_side,
            args.slippage_bp,
            args.funding_bp,
            args.notional,
            args.time_stop_bars,
        ),
    )
    print(result.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
