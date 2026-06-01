"""Strategy submission CLI for FR54 (petrosa-bot-ta-analysis #255 / #257 / #256).

Subcommands:

* ``submit`` — POSTs a strategy definition to
  ``petrosa-data-manager`` at ``POST /api/strategies`` and prints the
  registered ``strategy_id`` on success.
* ``backtest`` — thin shim over the existing ``python -m backtest`` CLI
  (``backtest.cli.main``); forwards ``--strategy/--from/--to/...`` so a
  freshly-submitted candidate can be replayed in one workflow.
* ``status`` — GET ``/api/strategies/{id}`` and print the persisted
  document. Exit code 3 disambiguates "strategy not registered" (404)
  from "transport failure" (1).
* ``persist-characterization`` (FR54-B AC1, #256) — maps a
  ``CharacterizationArtifact`` JSON produced by the ``backtest``
  subcommand into the ``Characterization`` shape that
  ``petrosa-data-manager`` persists, then POSTs to
  ``POST /api/characterizations``. The data-manager upsert is keyed by
  ``(strategy_id, strategy_version)`` so re-POSTing the same artifact is
  a natural no-op (AC3).
* ``register-with-cio`` (FR54-B AC2, #256) — POSTs to
  ``POST /api/admission/register`` on ``petrosa-cio``. The receiving
  ``PortfolioTracker.record_admit`` replaces the per-strategy position
  in a dict, so re-registering the same ``strategy_id`` is also a
  natural no-op (AC3).

The submission payload is **persisted verbatim by the registry**;
``petrosa-data-manager`` never imports, compiles, or executes the code
(see ``petrosa-data-manager/data_manager/models/registered_strategy.py``).
Code-execution sandboxing for the backtest happens entirely on the
caller side via the existing ``backtest.engine.BacktestEngine`` machinery.
"""

from __future__ import annotations

import argparse
import hashlib
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
DEFAULT_CIO_URL = os.environ.get("CIO_URL", "http://petrosa-cio:8000")
STRATEGIES_PATH = "/api/strategies"
CHARACTERIZATIONS_PATH = "/api/characterizations"
CIO_ADMISSION_REGISTER_PATH = "/api/admission/register"

# FR54-B AC1: required edge-metric keys on the data-manager
# ``Characterization`` shape (mirrors
# ``data_manager/models/characterization.REQUIRED_METRIC_KEYS``). The CLI
# refuses to POST an artifact whose ``edge_estimate`` cannot satisfy these
# keys so the operator sees the mismatch locally rather than as a 422 from
# the receiving service.
REQUIRED_METRIC_KEYS = ("sharpe", "win_rate", "mean_return")


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
            "Self-service strategy submission + backtest + characterization "
            "+ admission CLI (FR54-A/B/C). Submits, replays, persists, and "
            "registers strategies against the petrosa-data-manager and "
            "petrosa-cio services."
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

    status = sub.add_parser(
        "status",
        help="GET /api/strategies/{strategy_id} and print the registered document (FR54-C, #257)",
    )
    status.add_argument("--strategy-id", required=True, help="Strategy ID to query")
    status.add_argument(
        "--data-manager-url",
        default=DEFAULT_DATA_MANAGER_URL,
        help=f"Base URL for petrosa-data-manager (default: {DEFAULT_DATA_MANAGER_URL} or $DATA_MANAGER_URL)",
    )
    status.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds (default 30)",
    )

    persist = sub.add_parser(
        "persist-characterization",
        help=(
            "Map a CharacterizationArtifact JSON to the data-manager "
            "Characterization shape and POST it (FR54-B AC1, #256)"
        ),
    )
    persist.add_argument(
        "--artifact-file",
        required=True,
        type=Path,
        help=(
            "Path to a CharacterizationArtifact JSON (output of "
            "``python -m backtest`` / ``ta_bot.cli_strategy backtest``)"
        ),
    )
    persist.add_argument(
        "--strategy-version",
        required=True,
        help=(
            "Strategy version tag for the persisted characterization "
            "(forms the upsert key with strategy_id; reuse the same value "
            "to overwrite in-place per AC3)"
        ),
    )
    persist.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Deterministic RNG seed used for the backtest run (default 0)",
    )
    persist.add_argument(
        "--params-file",
        type=Path,
        default=None,
        help=(
            "Optional JSON file with the parameter set used by the backtest; "
            "feeds the canonical inputs_hash so a re-run can verify "
            "byte-reproducibility. Defaults to ``{}`` when omitted "
            "(strategy_revision_id remains the strong reproducibility key)."
        ),
    )
    persist.add_argument(
        "--data-manager-url",
        default=DEFAULT_DATA_MANAGER_URL,
        help=f"Base URL for petrosa-data-manager (default: {DEFAULT_DATA_MANAGER_URL} or $DATA_MANAGER_URL)",
    )
    persist.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds (default 30)",
    )

    register = sub.add_parser(
        "register-with-cio",
        help=(
            "POST a characterized strategy to petrosa-cio for admission "
            "consideration (FR54-B AC2, #256)"
        ),
    )
    register.add_argument(
        "--strategy-id", required=True, help="Strategy identifier to register"
    )
    register.add_argument(
        "--position-size-usd",
        required=True,
        type=float,
        help="Admitted notional position size in USD (>= 0)",
    )
    register.add_argument(
        "--leverage",
        required=True,
        type=float,
        help="Admitted leverage (>= 1)",
    )
    register.add_argument(
        "--strategy-revision-id",
        default=None,
        help=(
            "FR53 / P3.4 revision id for the audit trail "
            "(srev_{module_hash[:12]}_{parameter_hash[:12]})"
        ),
    )
    register.add_argument(
        "--submitted-by",
        default=None,
        help="Operator handle for the audit trail",
    )
    register.add_argument(
        "--cio-url",
        default=DEFAULT_CIO_URL,
        help=f"Base URL for petrosa-cio (default: {DEFAULT_CIO_URL} or $CIO_URL)",
    )
    register.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds (default 30)",
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


def _post_json(
    url: str,
    payload: dict[str, Any],
    timeout: float,
    opener: urllib.request.OpenerDirector | None = None,
) -> dict[str, Any]:
    """POST ``payload`` as JSON and return the decoded response body.

    Shared transport for ``submit``, ``persist-characterization``, and
    ``register-with-cio`` so all three use the same urllib contract; tests
    inject a fake opener to assert request shape.
    """
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
            raise RuntimeError(f"POST {url} failed: HTTP {status}: {text}")
        try:
            return json.loads(text) if text else {}
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"POST {url} returned non-JSON response: {text!r}"
            ) from exc


def _post_strategy(
    url: str,
    payload: dict[str, Any],
    timeout: float,
    opener: urllib.request.OpenerDirector | None = None,
) -> dict[str, Any]:
    return _post_json(url, payload, timeout, opener=opener)


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


def _get_strategy(
    url: str,
    timeout: float,
    opener: urllib.request.OpenerDirector | None = None,
) -> dict[str, Any]:
    """GET the strategy document. Mirrors :func:`_post_strategy` for the read side
    so the lifecycle status query (FR54-C) uses the same urllib transport
    contract as the submit path.
    """
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"Accept": "application/json"},
    )
    op = opener or urllib.request.build_opener()
    with op.open(req, timeout=timeout) as resp:
        raw = resp.read()
        status = getattr(resp, "status", None) or resp.getcode()
        text = raw.decode("utf-8") if raw else ""
        if status < 200 or status >= 300:
            raise RuntimeError(f"Strategy status query failed: HTTP {status}: {text}")
        try:
            return json.loads(text) if text else {}
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Strategy status returned non-JSON response: {text!r}"
            ) from exc


def run_status(args: argparse.Namespace) -> int:
    url = args.data_manager_url.rstrip("/") + STRATEGIES_PATH + "/" + args.strategy_id
    try:
        result = _get_strategy(url, args.timeout)
    except urllib.error.HTTPError as e:
        try:
            err_text = e.read().decode("utf-8", errors="replace")
        except Exception:
            err_text = ""
        # 404 is a normal "not registered" answer in the lifecycle context;
        # surface it explicitly to the operator with a distinct exit code so a
        # CI script can disambiguate "doesn't exist" from "transport failure".
        if e.code == 404:
            print(f"error: strategy {args.strategy_id!r} not found", file=sys.stderr)
            return 3
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


# ---------------------------------------------------------------------------
# FR54-B (petrosa-bot-ta-analysis#256)
# ---------------------------------------------------------------------------


def _compute_inputs_hash(
    *,
    strategy_id: str,
    strategy_version: str,
    data_window_from: str,
    data_window_to: str,
    seed: int,
    params: dict[str, Any],
) -> str:
    """Mirror ``data_manager.models.characterization.compute_inputs_hash``.

    Both sides canonicalise to the same JSON shape so the persisted
    ``inputs_hash`` is the byte-identical value the data-manager helper
    would have computed had we used Python imports across services. The
    CLI deliberately re-implements rather than depending on the
    ``petrosa-data-manager`` package — ``ta-analysis`` is the producer
    side and importing the consumer's model would couple the two
    deployments.
    """
    payload = {
        "strategy_id": strategy_id,
        "strategy_version": strategy_version,
        "data_window_from": data_window_from,
        "data_window_to": data_window_to,
        "seed": int(seed),
        "params": params or {},
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _artifact_to_characterization_payload(
    *,
    artifact: dict[str, Any],
    strategy_version: str,
    seed: int,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Map a producer-side ``CharacterizationArtifact`` dict to the consumer
    ``Characterization`` payload accepted by ``POST /api/characterizations``.

    Field translation (producer → consumer):

    * ``range_from`` / ``range_to`` → ``data_window_from`` / ``data_window_to``.
    * ``edge_estimate`` → ``metrics`` with the three required keys
      (``sharpe``, ``win_rate``, ``mean_return``) plus the extra
      ``trade_count``; ``max_leverage_envelope`` (v1.3.0) is folded in when
      present so the consumer's open ``metrics`` dict carries the FR3 / FR52
      bound without a schema change.
    * ``drawdown_envelope`` is flattened from
      ``{p50, p90, p99, p100}`` to a 4-element list ``[p50, p90, p99, p100]``.
    * ``sensitivity_analysis`` → ``param_sensitivities`` keyed by the
      perturbed parameter name (producer always uses
      ``confidence_threshold`` today).
    * ``strategy_revision_id`` + ``strategy_revision`` pass through.

    Raises :class:`ValueError` if a required producer field is missing —
    surfacing the schema mismatch locally beats waiting for the
    consumer's 422.
    """
    try:
        strategy_id = artifact["strategy_id"]
    except KeyError as exc:
        raise ValueError("artifact JSON missing required key 'strategy_id'") from exc
    try:
        range_from = artifact["range_from"]
        range_to = artifact["range_to"]
    except KeyError as exc:
        raise ValueError(f"artifact JSON missing required key {exc.args[0]!r}") from exc

    edge = artifact.get("edge_estimate") or {}
    if not edge:
        raise ValueError(
            "artifact JSON missing 'edge_estimate' — cannot build required metrics "
            "(sharpe, win_rate, mean_return)"
        )
    # Required producer keys map to the consumer's REQUIRED_METRIC_KEYS — surface
    # a missing one as ValueError so the CLI exits 2 cleanly rather than letting
    # a KeyError bubble up as an opaque traceback.
    edge_to_metric = {
        "sharpe_ratio": "sharpe",
        "win_rate": "win_rate",
        "expected_pnl": "mean_return",
    }
    missing_edge = [k for k in edge_to_metric if k not in edge]
    if missing_edge:
        raise ValueError(
            "artifact JSON 'edge_estimate' missing required key(s): "
            + ", ".join(missing_edge)
        )
    metrics: dict[str, float] = {
        "sharpe": float(edge["sharpe_ratio"]),
        "win_rate": float(edge["win_rate"]),
        "mean_return": float(edge["expected_pnl"]),
        "trade_count": float(edge.get("trade_count", 0)),
    }
    mle = artifact.get("max_leverage_envelope")
    if mle is not None:
        metrics["max_leverage_envelope"] = float(mle)

    dd = artifact.get("drawdown_envelope") or {}
    if not dd:
        raise ValueError("artifact JSON missing 'drawdown_envelope'")
    drawdown_envelope = [
        float(dd["p50"]),
        float(dd["p90"]),
        float(dd["p99"]),
        float(dd["p100"]),
    ]

    sa = artifact.get("sensitivity_analysis") or {}
    if sa:
        param_sensitivities: dict[str, Any] = {
            sa.get("parameter", "confidence_threshold"): [
                dict(pt) for pt in sa.get("points", [])
            ]
        }
    else:
        param_sensitivities = {}

    inputs_hash = _compute_inputs_hash(
        strategy_id=strategy_id,
        strategy_version=strategy_version,
        data_window_from=range_from,
        data_window_to=range_to,
        seed=seed,
        params=params,
    )

    payload: dict[str, Any] = {
        "strategy_id": strategy_id,
        "strategy_version": strategy_version,
        "data_window_from": range_from,
        "data_window_to": range_to,
        "seed": int(seed),
        "metrics": metrics,
        "drawdown_envelope": drawdown_envelope,
        "param_sensitivities": param_sensitivities,
        "inputs_hash": inputs_hash,
    }
    revision_id = artifact.get("strategy_revision_id")
    if revision_id is not None:
        payload["strategy_revision_id"] = revision_id
    revision = artifact.get("strategy_revision")
    if revision is not None:
        payload["strategy_revision"] = {
            "revision_id": revision["revision_id"],
            "module_hash": revision["module_hash"],
            "parameter_hash": revision["parameter_hash"],
        }
    return payload


def _load_artifact(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"--artifact-file {path} is not valid JSON: {exc.msg}"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError(f"--artifact-file {path} must contain a JSON object")
    return data


def _load_params(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--params-file {path} is not valid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"--params-file {path} must contain a JSON object")
    return data


def run_persist_characterization(args: argparse.Namespace) -> int:
    if not args.artifact_file.exists():
        print(
            f"error: --artifact-file not found: {args.artifact_file}",
            file=sys.stderr,
        )
        return 2
    if args.params_file is not None and not args.params_file.exists():
        print(
            f"error: --params-file not found: {args.params_file}",
            file=sys.stderr,
        )
        return 2
    try:
        artifact = _load_artifact(args.artifact_file)
        params = _load_params(args.params_file)
        payload = _artifact_to_characterization_payload(
            artifact=artifact,
            strategy_version=args.strategy_version,
            seed=args.seed,
            params=params,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    missing = [k for k in REQUIRED_METRIC_KEYS if k not in payload["metrics"]]
    if missing:
        print(
            "error: artifact does not satisfy required metric keys "
            f"({', '.join(missing)})",
            file=sys.stderr,
        )
        return 2

    url = args.data_manager_url.rstrip("/") + CHARACTERIZATIONS_PATH
    try:
        result = _post_json(url, payload, args.timeout)
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


def run_register_with_cio(args: argparse.Namespace) -> int:
    if args.position_size_usd < 0:
        print("error: --position-size-usd must be >= 0", file=sys.stderr)
        return 2
    if args.leverage < 1:
        print("error: --leverage must be >= 1", file=sys.stderr)
        return 2

    payload: dict[str, Any] = {
        "strategy_id": args.strategy_id,
        "position_size_usd": float(args.position_size_usd),
        "leverage": float(args.leverage),
    }
    if args.strategy_revision_id is not None:
        payload["strategy_revision_id"] = args.strategy_revision_id
    if args.submitted_by is not None:
        payload["submitted_by"] = args.submitted_by

    url = args.cio_url.rstrip("/") + CIO_ADMISSION_REGISTER_PATH
    try:
        result = _post_json(url, payload, args.timeout)
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


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    if raw and raw[0] == "backtest":
        return run_backtest(raw[1:])
    parser = build_parser()
    args = parser.parse_args(raw)
    if args.command == "submit":
        return run_submit(args)
    if args.command == "status":
        return run_status(args)
    if args.command == "persist-characterization":
        return run_persist_characterization(args)
    if args.command == "register-with-cio":
        return run_register_with_cio(args)
    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover — entry point
    sys.exit(main())
