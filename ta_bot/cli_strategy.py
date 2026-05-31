"""Strategy submission CLI for FR54-A (petrosa-bot-ta-analysis#255).

Subcommands:

* ``submit`` — POSTs a strategy definition to
  ``petrosa-data-manager`` at ``POST /api/strategies`` and prints the
  registered ``strategy_id`` on success.
* ``backtest`` — thin shim over the existing ``python -m backtest`` CLI
  (``backtest.cli.main``); forwards ``--strategy/--from/--to/...`` so a
  freshly-submitted candidate can be replayed in one workflow.

The submission payload is **persisted verbatim by the registry**;
``petrosa-data-manager`` never imports, compiles, or executes the code
(see ``petrosa-data-manager/data_manager/models/registered_strategy.py``).
Code-execution sandboxing for the backtest happens entirely on the
caller side via the existing ``backtest.engine.BacktestEngine`` machinery.

Invocation::

    python -m ta_bot.cli_strategy submit \
        --strategy-id momentum-v3 \
        --code-file ./strategies/momentum_v3.py \
        --params '{"window": 14, "threshold": 0.03}' \
        --symbols BTCUSDT,ETHUSDT \
        --submitted-by alice \
        --signed-action-id sa-1

    python -m ta_bot.cli_strategy backtest \
        --strategy momentum-v3 \
        --from 2026-05-01 --to 2026-05-15 --symbol BTCUSDT
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path
from typing import Any

DEFAULT_DATA_MANAGER_URL = os.environ.get(
    "DATA_MANAGER_URL", "http://petrosa-data-manager:8000"
)
STRATEGIES_PATH = "/api/strategies"


def _parse_symbol_scope(raw: str) -> list[str]:
    parts = [s.strip() for s in raw.split(",") if s.strip()]
    if not parts:
        raise argparse.ArgumentTypeError("--symbols must list at least one symbol")
    return parts


def _parse_parameter_set(raw: str) -> dict[str, Any]:
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(
            f"--params must be valid JSON object: {exc.msg}"
        ) from exc
    if not isinstance(obj, dict):
        raise argparse.ArgumentTypeError("--params must be a JSON object")
    return obj


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ta_bot.cli_strategy",
        description=(
            "Self-service strategy submission + backtest CLI (FR54-A). "
            "Submits a strategy definition to petrosa-data-manager and/or "
            "runs the existing backtest engine against historical data."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    submit = sub.add_parser(
        "submit",
        help="POST a strategy definition to petrosa-data-manager",
    )
    submit.add_argument(
        "--strategy-id", required=True, help="Stable identifier (e.g. momentum-v3)"
    )
    submit.add_argument(
        "--code-file",
        required=True,
        type=Path,
        help="Path to a .py file containing the strategy code (persisted verbatim, never executed by the registry)",
    )
    submit.add_argument(
        "--params",
        required=True,
        type=_parse_parameter_set,
        help="Parameter set as JSON object (e.g. '{\"window\": 14}')",
    )
    submit.add_argument(
        "--symbols",
        required=True,
        type=_parse_symbol_scope,
        help="Comma-separated symbol scope (e.g. BTCUSDT,ETHUSDT)",
    )
    submit.add_argument(
        "--submitted-by",
        required=True,
        help="Operator handle (audit-trail field)",
    )
    submit.add_argument(
        "--signed-action-id",
        required=True,
        help="Signed-action audit ID for the submission",
    )
    submit.add_argument(
        "--data-manager-url",
        default=DEFAULT_DATA_MANAGER_URL,
        help=f"Base URL for petrosa-data-manager (default: {DEFAULT_DATA_MANAGER_URL} or $DATA_MANAGER_URL)",
    )
    submit.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds (default 30)",
    )

    # ``backtest`` is intentionally a thin pass-through: it forwards every
    # arg after the subcommand verbatim to ``backtest.cli.main`` without
    # re-parsing. We don't register it on the subparser because argparse's
    # REMAINDER positional eagerly consumes options as the parent parser's
    # unknown args. ``main()`` short-circuits ``argv[0] == 'backtest'``.
    sub.add_parser(
        "backtest",
        help="Delegate to the existing backtest CLI (python -m backtest); "
        "all subsequent args are forwarded verbatim to backtest.cli.main.",
        add_help=False,
    )

    return parser


def _submit_payload(args: argparse.Namespace) -> dict[str, Any]:
    code = args.code_file.read_text(encoding="utf-8")
    return {
        "strategy_id": args.strategy_id,
        "code": code,
        "parameter_set": args.params,
        "symbol_scope": args.symbols,
        "submitted_by": args.submitted_by,
        "signed_action_id": args.signed_action_id,
    }


def _post_strategy(
    url: str,
    payload: dict[str, Any],
    timeout: float,
    opener: urllib.request.OpenerDirector | None = None,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    op = opener or urllib.request.build_opener()
    with op.open(req, timeout=timeout) as resp:
        raw = resp.read()
        status = getattr(resp, "status", None) or resp.getcode()
        text = raw.decode("utf-8") if raw else ""
        if status < 200 or status >= 300:
            raise RuntimeError(f"Strategy submission failed: HTTP {status}: {text}")
        try:
            return json.loads(text) if text else {}
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Strategy submission returned non-JSON response: {text!r}"
            ) from exc


def run_submit(args: argparse.Namespace) -> int:
    if not args.code_file.exists():
        print(f"error: --code-file not found: {args.code_file}", file=sys.stderr)
        return 2
    payload = _submit_payload(args)
    url = args.data_manager_url.rstrip("/") + STRATEGIES_PATH
    try:
        result = _post_strategy(url, payload, args.timeout)
    except urllib.error.HTTPError as e:
        try:
            err_text = e.read().decode("utf-8", errors="replace")
        except Exception:
            err_text = ""
        print(f"error: HTTP {e.code} from {url}: {err_text}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"error: cannot reach {url}: {e.reason}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def run_backtest(forwarded: Sequence[str]) -> int:
    from backtest.cli import main as backtest_main

    return backtest_main(list(forwarded))


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    if raw and raw[0] == "backtest":
        return run_backtest(raw[1:])
    parser = build_parser()
    args = parser.parse_args(raw)
    if args.command == "submit":
        return run_submit(args)
    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover — entry point
    sys.exit(main())
