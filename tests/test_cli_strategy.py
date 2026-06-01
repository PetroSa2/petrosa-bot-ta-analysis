"""Tests for ``ta_bot/cli_strategy.py`` (FR54-A, #255)."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest

from ta_bot import cli_strategy


def _write_sample_strategy(tmp_path: Path) -> Path:
    p = tmp_path / "momentum_v3.py"
    p.write_text("def signal(*a, **kw):\n    return None\n", encoding="utf-8")
    return p


class _FakeResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    def read(self) -> bytes:
        return self._body

    def getcode(self) -> int:
        return self.status

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: Any) -> None:
        return None


class _FakeOpener:
    def __init__(self, response: _FakeResponse) -> None:
        self.response = response
        self.requests: list[dict[str, Any]] = []

    def open(self, req: Any, timeout: float = 0) -> _FakeResponse:
        self.requests.append(
            {
                "url": req.full_url,
                "method": req.get_method(),
                "headers": dict(req.header_items()),
                "body": req.data,
                "timeout": timeout,
            }
        )
        return self.response


# ─── _submit_payload ──────────────────────────────────────────────────────────


def test_submit_payload_reads_code_file_and_assembles_request(tmp_path: Path) -> None:
    code_path = _write_sample_strategy(tmp_path)
    args = cli_strategy.build_parser().parse_args(
        [
            "submit",
            "--strategy-id",
            "momentum-v3",
            "--code-file",
            str(code_path),
            "--params",
            '{"window": 14, "threshold": 0.03}',
            "--symbols",
            "BTCUSDT,ETHUSDT",
            "--submitted-by",
            "alice",
            "--signed-action-id",
            "sa-1",
        ]
    )
    payload = cli_strategy._submit_payload(args)
    assert payload == {
        "strategy_id": "momentum-v3",
        "code": "def signal(*a, **kw):\n    return None\n",
        "parameter_set": {"window": 14, "threshold": 0.03},
        "symbol_scope": ["BTCUSDT", "ETHUSDT"],
        "submitted_by": "alice",
        "signed_action_id": "sa-1",
    }


# ─── _post_strategy ──────────────────────────────────────────────────────────


def test_post_strategy_sends_json_and_returns_parsed_body() -> None:
    response_body = json.dumps(
        {
            "strategy_id": "momentum-v3",
            "status": "candidate",
            "registered_at": "2026-05-30T22:00:00Z",
        }
    ).encode("utf-8")
    fake = _FakeOpener(_FakeResponse(201, response_body))
    result = cli_strategy._post_strategy(
        "http://dm.local/api/strategies",
        {"strategy_id": "momentum-v3"},
        timeout=5.0,
        opener=fake,
    )
    assert result["strategy_id"] == "momentum-v3"
    assert result["status"] == "candidate"
    assert len(fake.requests) == 1
    sent = fake.requests[0]
    assert sent["url"] == "http://dm.local/api/strategies"
    assert sent["method"] == "POST"
    header_pairs = {(k.lower(), v) for k, v in sent["headers"].items()}
    assert ("content-type", "application/json") in header_pairs
    assert json.loads(sent["body"].decode("utf-8")) == {"strategy_id": "momentum-v3"}


def test_post_strategy_raises_on_non_2xx() -> None:
    fake = _FakeOpener(_FakeResponse(500, b'{"detail":"boom"}'))
    with pytest.raises(RuntimeError, match="HTTP 500") as exc_info:
        cli_strategy._post_strategy(
            "http://dm.local/api/strategies",
            {"strategy_id": "x"},
            timeout=5.0,
            opener=fake,
        )
    assert "HTTP 500" in str(exc_info.value)


# ─── parameter / symbol validators ───────────────────────────────────────────


def test_parse_symbol_scope_accepts_csv_and_strips() -> None:
    assert cli_strategy._parse_symbol_scope("BTCUSDT, ETHUSDT") == [
        "BTCUSDT",
        "ETHUSDT",
    ]


def test_parse_symbol_scope_rejects_empty() -> None:
    import argparse as _ap

    with pytest.raises(_ap.ArgumentTypeError) as exc_info:
        cli_strategy._parse_symbol_scope("   ,  ")
    assert "at least one symbol" in str(exc_info.value)


def test_parse_parameter_set_rejects_non_object() -> None:
    import argparse as _ap

    with pytest.raises(_ap.ArgumentTypeError) as exc_info:
        cli_strategy._parse_parameter_set("[1,2,3]")
    assert "JSON object" in str(exc_info.value)


def test_parse_parameter_set_rejects_invalid_json() -> None:
    import argparse as _ap

    with pytest.raises(_ap.ArgumentTypeError) as exc_info:
        cli_strategy._parse_parameter_set("{not json")
    assert "valid JSON object" in str(exc_info.value)


def test_run_submit_returns_1_on_url_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import urllib.error as _err

    code_path = _write_sample_strategy(tmp_path)

    class _ErroringOpener:
        def open(self, req: Any, timeout: float = 0) -> Any:
            raise _err.URLError("connection refused")

    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: _ErroringOpener(),
    )
    rc = cli_strategy.main(
        [
            "submit",
            "--strategy-id",
            "x",
            "--code-file",
            str(code_path),
            "--params",
            "{}",
            "--symbols",
            "BTCUSDT",
            "--submitted-by",
            "alice",
            "--signed-action-id",
            "sa-1",
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "cannot reach" in err


# ─── status subcommand (FR54-C, #257) ────────────────────────────────────────


def test_run_status_happy_path_prints_response_and_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    response_body = json.dumps(
        {
            "strategy_id": "momentum-v3",
            "status": "candidate",
            "registered_at": "2026-05-30T22:00:00Z",
            "version": 1,
        }
    ).encode("utf-8")
    fake = _FakeOpener(_FakeResponse(200, response_body))
    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: fake,
    )
    rc = cli_strategy.main(
        [
            "status",
            "--strategy-id",
            "momentum-v3",
            "--data-manager-url",
            "http://dm.local/",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    printed = json.loads(out)
    assert printed["strategy_id"] == "momentum-v3"
    assert printed["status"] == "candidate"
    assert len(fake.requests) == 1
    assert fake.requests[0]["url"] == "http://dm.local/api/strategies/momentum-v3"
    assert fake.requests[0]["method"] == "GET"


def test_run_status_returns_3_on_404_distinct_from_other_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import urllib.error as _err

    class _NotFoundOpener:
        def open(self, req: Any, timeout: float = 0) -> Any:
            raise _err.HTTPError(
                req.full_url,
                404,
                "Not Found",
                {},
                io.BytesIO(b'{"detail":"unknown strategy"}'),
            )

    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: _NotFoundOpener(),
    )
    rc = cli_strategy.main(
        ["status", "--strategy-id", "ghost", "--data-manager-url", "http://dm.local"]
    )
    assert rc == 3
    err = capsys.readouterr().err
    assert "'ghost' not found" in err


def test_run_status_returns_1_on_5xx(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import urllib.error as _err

    class _ErrOpener:
        def open(self, req: Any, timeout: float = 0) -> Any:
            raise _err.HTTPError(req.full_url, 503, "boom", {}, io.BytesIO(b"down"))

    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: _ErrOpener(),
    )
    rc = cli_strategy.main(
        ["status", "--strategy-id", "x", "--data-manager-url", "http://dm.local"]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "HTTP 503" in err


def test_get_strategy_sends_get_and_returns_body() -> None:
    body = json.dumps({"strategy_id": "abc", "status": "accepted"}).encode("utf-8")
    fake = _FakeOpener(_FakeResponse(200, body))
    result = cli_strategy._get_strategy(
        "http://dm.local/api/strategies/abc", timeout=5.0, opener=fake
    )
    assert result["strategy_id"] == "abc"
    assert fake.requests[0]["method"] == "GET"


def test_get_strategy_raises_on_non_2xx() -> None:
    fake = _FakeOpener(_FakeResponse(500, b'{"detail":"boom"}'))
    with pytest.raises(RuntimeError, match="HTTP 500") as exc_info:
        cli_strategy._get_strategy(
            "http://dm.local/api/strategies/x", timeout=5.0, opener=fake
        )
    assert "HTTP 500" in str(exc_info.value)


def test_get_strategy_raises_on_non_json_body() -> None:
    fake = _FakeOpener(_FakeResponse(200, b"not-json"))
    with pytest.raises(RuntimeError, match="non-JSON") as exc_info:
        cli_strategy._get_strategy(
            "http://dm.local/api/strategies/x", timeout=5.0, opener=fake
        )
    assert "non-JSON" in str(exc_info.value)


def test_run_status_returns_1_on_url_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import urllib.error as _err

    class _ErrOpener:
        def open(self, req: Any, timeout: float = 0) -> Any:
            raise _err.URLError("connection refused")

    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: _ErrOpener(),
    )
    rc = cli_strategy.main(
        ["status", "--strategy-id", "x", "--data-manager-url", "http://dm.local"]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "cannot reach" in err


def test_run_status_returns_1_on_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """_get_strategy raises RuntimeError if the response body isn't JSON;
    run_status converts that to exit 1 with the error message."""
    fake = _FakeOpener(_FakeResponse(200, b"not-json-not-anything"))
    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: fake,
    )
    rc = cli_strategy.main(
        ["status", "--strategy-id", "x", "--data-manager-url", "http://dm.local"]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "non-JSON" in err


def test_run_submit_returns_1_on_http_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import urllib.error as _err

    code_path = _write_sample_strategy(tmp_path)

    class _HttpErroringOpener:
        def open(self, req: Any, timeout: float = 0) -> Any:
            raise _err.HTTPError(
                req.full_url,
                503,
                "Service Unavailable",
                {},
                io.BytesIO(b'{"detail":"mongo down"}'),
            )

    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: _HttpErroringOpener(),
    )
    rc = cli_strategy.main(
        [
            "submit",
            "--strategy-id",
            "x",
            "--code-file",
            str(code_path),
            "--params",
            "{}",
            "--symbols",
            "BTCUSDT",
            "--submitted-by",
            "alice",
            "--signed-action-id",
            "sa-1",
        ]
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "HTTP 503" in err
    assert "mongo down" in err


# ─── parser wiring ───────────────────────────────────────────────────────────


def test_parser_requires_subcommand() -> None:
    parser = cli_strategy.build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args([])
    assert exc_info.value.code == 2


def test_backtest_subcommand_forwards_remaining(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[Any] = []

    def _fake_backtest_main(argv: Any) -> int:
        captured.append(argv)
        return 0

    import sys

    fake_backtest_module = type(sys)("backtest")
    fake_cli_module = type(sys)("backtest.cli")
    fake_cli_module.main = _fake_backtest_main  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "backtest", fake_backtest_module)
    monkeypatch.setitem(sys.modules, "backtest.cli", fake_cli_module)

    rc = cli_strategy.main(
        [
            "backtest",
            "--strategy",
            "momentum-v3",
            "--from",
            "2026-05-01",
            "--to",
            "2026-05-02",
        ]
    )
    assert rc == 0
    assert captured == [
        ["--strategy", "momentum-v3", "--from", "2026-05-01", "--to", "2026-05-02"]
    ]


# ─── end-to-end submit (mock HTTP) ───────────────────────────────────────────


def test_run_submit_happy_path_prints_response_and_returns_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code_path = _write_sample_strategy(tmp_path)
    response_body = json.dumps(
        {
            "strategy_id": "momentum-v3",
            "status": "candidate",
            "registered_at": "2026-05-30T22:00:00Z",
        }
    ).encode("utf-8")
    fake = _FakeOpener(_FakeResponse(201, response_body))
    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: fake,
    )
    rc = cli_strategy.main(
        [
            "submit",
            "--strategy-id",
            "momentum-v3",
            "--code-file",
            str(code_path),
            "--params",
            '{"window": 14}',
            "--symbols",
            "BTCUSDT",
            "--submitted-by",
            "alice",
            "--signed-action-id",
            "sa-1",
            "--data-manager-url",
            "http://dm.local/",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    printed = json.loads(out)
    assert printed["strategy_id"] == "momentum-v3"
    assert printed["status"] == "candidate"
    assert len(fake.requests) == 1
    sent_url = fake.requests[0]["url"]
    assert sent_url == "http://dm.local/api/strategies"


def test_run_submit_returns_2_when_code_file_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = cli_strategy.main(
        [
            "submit",
            "--strategy-id",
            "x",
            "--code-file",
            str(tmp_path / "does-not-exist.py"),
            "--params",
            "{}",
            "--symbols",
            "BTCUSDT",
            "--submitted-by",
            "alice",
            "--signed-action-id",
            "sa-1",
        ]
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "not found" in err


# ─── FR54-B (#256) persist-characterization + register-with-cio ─────────────


def _sample_artifact() -> dict[str, Any]:
    """A v1.3.0-shaped CharacterizationArtifact dict for mapping tests."""
    return {
        "schema_version": "1.3.0",
        "strategy_id": "momentum-v3",
        "symbol": "BTCUSDT",
        "period": "1h",
        "range_from": "2026-05-01T00:00:00+00:00",
        "range_to": "2026-05-15T00:00:00+00:00",
        "candle_count": 336,
        "signal_count": 12,
        "source": "binance",
        "events": [],
        "edge_estimate": {
            "expected_pnl": 0.0123,
            "win_rate": 0.58,
            "sharpe_ratio": 1.42,
            "trade_count": 12,
        },
        "drawdown_envelope": {
            "p50": 0.01,
            "p90": 0.04,
            "p99": 0.09,
            "p100": 0.12,
        },
        "sensitivity_analysis": {
            "parameter": "confidence_threshold",
            "points": [
                {
                    "confidence_threshold": 0.5,
                    "win_rate": 0.55,
                    "expected_pnl": 0.011,
                    "trade_count": 14,
                },
                {
                    "confidence_threshold": 0.7,
                    "win_rate": 0.62,
                    "expected_pnl": 0.014,
                    "trade_count": 9,
                },
            ],
        },
        "strategy_revision_id": "srev_abc123def456_789012ghi345",
        "strategy_revision": {
            "revision_id": "srev_abc123def456_789012ghi345",
            "module_hash": "a" * 64,
            "parameter_hash": "b" * 64,
        },
        "max_leverage_envelope": 3.5,
    }


def _write_artifact(tmp_path: Path, payload: dict[str, Any] | None = None) -> Path:
    p = tmp_path / "artifact.json"
    p.write_text(json.dumps(payload or _sample_artifact()), encoding="utf-8")
    return p


def test_artifact_to_characterization_payload_maps_all_fields() -> None:
    payload = cli_strategy._artifact_to_characterization_payload(
        artifact=_sample_artifact(),
        strategy_version="v1",
        seed=7,
        params={"window": 14},
    )
    assert payload["strategy_id"] == "momentum-v3"
    assert payload["strategy_version"] == "v1"
    assert payload["data_window_from"] == "2026-05-01T00:00:00+00:00"
    assert payload["data_window_to"] == "2026-05-15T00:00:00+00:00"
    assert payload["seed"] == 7
    # metrics: required keys + carry-overs
    assert payload["metrics"]["sharpe"] == pytest.approx(1.42)
    assert payload["metrics"]["win_rate"] == pytest.approx(0.58)
    assert payload["metrics"]["mean_return"] == pytest.approx(0.0123)
    assert payload["metrics"]["trade_count"] == pytest.approx(12)
    assert payload["metrics"]["max_leverage_envelope"] == pytest.approx(3.5)
    # drawdown envelope flattened to ordered list
    assert payload["drawdown_envelope"] == [0.01, 0.04, 0.09, 0.12]
    # sensitivities re-keyed by parameter name
    assert "confidence_threshold" in payload["param_sensitivities"]
    assert len(payload["param_sensitivities"]["confidence_threshold"]) == 2
    # revision binding survives
    assert payload["strategy_revision_id"] == "srev_abc123def456_789012ghi345"
    assert payload["strategy_revision"]["module_hash"] == "a" * 64
    # inputs_hash is a 64-hex SHA-256 string
    assert isinstance(payload["inputs_hash"], str)
    assert len(payload["inputs_hash"]) == 64
    int(payload["inputs_hash"], 16)


def test_artifact_to_characterization_payload_deterministic_inputs_hash() -> None:
    """Same inputs → byte-identical inputs_hash regardless of dict ordering."""
    a = cli_strategy._artifact_to_characterization_payload(
        artifact=_sample_artifact(),
        strategy_version="v1",
        seed=7,
        params={"window": 14, "threshold": 0.03},
    )
    b = cli_strategy._artifact_to_characterization_payload(
        artifact=_sample_artifact(),
        strategy_version="v1",
        seed=7,
        params={"threshold": 0.03, "window": 14},
    )
    assert a["inputs_hash"] == b["inputs_hash"]


def test_artifact_to_characterization_payload_changes_hash_on_seed() -> None:
    a = cli_strategy._artifact_to_characterization_payload(
        artifact=_sample_artifact(),
        strategy_version="v1",
        seed=7,
        params={},
    )
    b = cli_strategy._artifact_to_characterization_payload(
        artifact=_sample_artifact(),
        strategy_version="v1",
        seed=8,
        params={},
    )
    assert a["inputs_hash"] != b["inputs_hash"]


def test_artifact_to_characterization_payload_rejects_missing_edge() -> None:
    bad = _sample_artifact()
    bad.pop("edge_estimate")
    with pytest.raises(ValueError, match="edge_estimate") as exc_info:
        cli_strategy._artifact_to_characterization_payload(
            artifact=bad, strategy_version="v1", seed=0, params={}
        )
    assert "edge_estimate" in str(exc_info.value)


def test_artifact_to_characterization_payload_rejects_missing_drawdown() -> None:
    bad = _sample_artifact()
    bad.pop("drawdown_envelope")
    with pytest.raises(ValueError, match="drawdown_envelope") as exc_info:
        cli_strategy._artifact_to_characterization_payload(
            artifact=bad, strategy_version="v1", seed=0, params={}
        )
    assert "drawdown_envelope" in str(exc_info.value)


def test_artifact_to_characterization_payload_rejects_missing_strategy_id() -> None:
    bad = _sample_artifact()
    bad.pop("strategy_id")
    with pytest.raises(ValueError, match="strategy_id") as exc_info:
        cli_strategy._artifact_to_characterization_payload(
            artifact=bad, strategy_version="v1", seed=0, params={}
        )
    assert "strategy_id" in str(exc_info.value)


def test_artifact_to_characterization_payload_handles_missing_revision() -> None:
    """v1.0–v1.1 artifacts have no strategy_revision_id; the mapper still works."""
    legacy = _sample_artifact()
    legacy.pop("strategy_revision_id")
    legacy.pop("strategy_revision")
    legacy.pop("max_leverage_envelope")
    payload = cli_strategy._artifact_to_characterization_payload(
        artifact=legacy, strategy_version="v1", seed=0, params={}
    )
    assert "strategy_revision_id" not in payload
    assert "strategy_revision" not in payload
    assert "max_leverage_envelope" not in payload["metrics"]


def test_run_persist_characterization_happy_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    art_path = _write_artifact(tmp_path)
    response_body = json.dumps(
        {
            "strategy_id": "momentum-v3",
            "strategy_version": "v1",
            "created_at": "2026-06-01T12:00:00Z",
        }
    ).encode("utf-8")
    fake = _FakeOpener(_FakeResponse(201, response_body))
    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: fake,
    )
    rc = cli_strategy.main(
        [
            "persist-characterization",
            "--artifact-file",
            str(art_path),
            "--strategy-version",
            "v1",
            "--seed",
            "7",
            "--data-manager-url",
            "http://dm.local/",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    printed = json.loads(out)
    assert printed["strategy_id"] == "momentum-v3"
    # Asserts request shape: POST to /api/characterizations with the mapped body
    assert len(fake.requests) == 1
    sent = fake.requests[0]
    assert sent["url"] == "http://dm.local/api/characterizations"
    assert sent["method"] == "POST"
    sent_body = json.loads(sent["body"].decode("utf-8"))
    assert sent_body["strategy_id"] == "momentum-v3"
    assert sent_body["strategy_version"] == "v1"
    assert sent_body["metrics"]["sharpe"] == pytest.approx(1.42)
    assert sent_body["drawdown_envelope"] == [0.01, 0.04, 0.09, 0.12]
    assert sent_body["strategy_revision_id"] == "srev_abc123def456_789012ghi345"


def test_run_persist_characterization_idempotency_re_post_yields_same_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR54-B AC3: two identical invocations produce byte-identical POSTs.
    The data-manager upsert is keyed by (strategy_id, strategy_version), so
    a byte-identical re-POST yields no schema/state change downstream."""
    art_path = _write_artifact(tmp_path)
    responses: list[_FakeResponse] = [
        _FakeResponse(201, b'{"strategy_id":"momentum-v3"}'),
        _FakeResponse(201, b'{"strategy_id":"momentum-v3"}'),
    ]
    opens: list[dict[str, Any]] = []

    class _SeqOpener:
        def __init__(self) -> None:
            self._iter = iter(responses)

        def open(self, req: Any, timeout: float = 0) -> _FakeResponse:
            opens.append(
                {
                    "url": req.full_url,
                    "method": req.get_method(),
                    "body": req.data,
                }
            )
            return next(self._iter)

    seq = _SeqOpener()
    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: seq,
    )
    argv = [
        "persist-characterization",
        "--artifact-file",
        str(art_path),
        "--strategy-version",
        "v1",
        "--seed",
        "7",
        "--data-manager-url",
        "http://dm.local/",
    ]
    assert cli_strategy.main(argv) == 0
    assert cli_strategy.main(argv) == 0
    assert opens[0]["body"] == opens[1]["body"]


def test_run_persist_characterization_returns_2_when_artifact_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = cli_strategy.main(
        [
            "persist-characterization",
            "--artifact-file",
            str(tmp_path / "missing.json"),
            "--strategy-version",
            "v1",
        ]
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "not found" in err


def test_run_persist_characterization_returns_2_when_artifact_invalid_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    rc = cli_strategy.main(
        [
            "persist-characterization",
            "--artifact-file",
            str(bad),
            "--strategy-version",
            "v1",
        ]
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "not valid JSON" in err


def test_run_persist_characterization_returns_2_on_missing_required_metric(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """If the artifact's edge_estimate lacks fields the receiver requires
    (sharpe/win_rate/mean_return → mapped from sharpe_ratio/win_rate/expected_pnl),
    surface the failure locally with exit 2 before issuing the HTTP call."""
    art = _sample_artifact()
    # Drop a key the mapper needs to satisfy required metrics
    art["edge_estimate"].pop("expected_pnl")
    path = tmp_path / "art.json"
    path.write_text(json.dumps(art), encoding="utf-8")
    rc = cli_strategy.main(
        [
            "persist-characterization",
            "--artifact-file",
            str(path),
            "--strategy-version",
            "v1",
        ]
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "error" in err.lower()


def test_run_persist_characterization_handles_http_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import urllib.error as _err

    art_path = _write_artifact(tmp_path)

    class _ErrOpener:
        def open(self, req: Any, timeout: float = 0) -> Any:
            raise _err.HTTPError(
                req.full_url, 422, "Unprocessable", {}, io.BytesIO(b"bad")
            )

    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: _ErrOpener(),
    )
    rc = cli_strategy.main(
        [
            "persist-characterization",
            "--artifact-file",
            str(art_path),
            "--strategy-version",
            "v1",
        ]
    )
    assert rc == 1
    assert "HTTP 422" in capsys.readouterr().err


def test_run_persist_characterization_handles_url_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import urllib.error as _err

    art_path = _write_artifact(tmp_path)

    class _ErrOpener:
        def open(self, req: Any, timeout: float = 0) -> Any:
            raise _err.URLError("connection refused")

    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: _ErrOpener(),
    )
    rc = cli_strategy.main(
        [
            "persist-characterization",
            "--artifact-file",
            str(art_path),
            "--strategy-version",
            "v1",
        ]
    )
    assert rc == 1
    assert "cannot reach" in capsys.readouterr().err


def test_run_persist_characterization_loads_params_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--params-file feeds the canonical inputs_hash; same params via different
    files must yield identical inputs_hash bytes."""
    art_path = _write_artifact(tmp_path)
    p1 = tmp_path / "p1.json"
    p1.write_text('{"a": 1, "b": 2}', encoding="utf-8")
    p2 = tmp_path / "p2.json"
    p2.write_text('{"b": 2, "a": 1}', encoding="utf-8")

    captured: list[bytes] = []

    class _CapturingOpener:
        def open(self, req: Any, timeout: float = 0) -> _FakeResponse:
            captured.append(req.data)
            return _FakeResponse(201, b"{}")

    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: _CapturingOpener(),
    )
    for params_file in (p1, p2):
        cli_strategy.main(
            [
                "persist-characterization",
                "--artifact-file",
                str(art_path),
                "--strategy-version",
                "v1",
                "--params-file",
                str(params_file),
            ]
        )
    body_a = json.loads(captured[0].decode("utf-8"))
    body_b = json.loads(captured[1].decode("utf-8"))
    assert body_a["inputs_hash"] == body_b["inputs_hash"]


def test_run_persist_characterization_returns_2_when_params_file_missing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    art_path = _write_artifact(tmp_path)
    rc = cli_strategy.main(
        [
            "persist-characterization",
            "--artifact-file",
            str(art_path),
            "--strategy-version",
            "v1",
            "--params-file",
            str(tmp_path / "missing-params.json"),
        ]
    )
    assert rc == 2
    assert "not found" in capsys.readouterr().err


def test_run_register_with_cio_happy_path(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    response_body = json.dumps(
        {
            "strategy_id": "momentum-v3",
            "position_size_usd": 5000.0,
            "leverage": 3.0,
            "strategy_revision_id": "srev_abc",
            "submitted_by": "alice",
            "status": "admitted",
        }
    ).encode("utf-8")
    fake = _FakeOpener(_FakeResponse(201, response_body))
    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: fake,
    )
    rc = cli_strategy.main(
        [
            "register-with-cio",
            "--strategy-id",
            "momentum-v3",
            "--position-size-usd",
            "5000",
            "--leverage",
            "3",
            "--strategy-revision-id",
            "srev_abc",
            "--submitted-by",
            "alice",
            "--cio-url",
            "http://cio.local/",
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    printed = json.loads(out)
    assert printed["status"] == "admitted"
    assert len(fake.requests) == 1
    sent = fake.requests[0]
    assert sent["url"] == "http://cio.local/api/admission/register"
    assert sent["method"] == "POST"
    body = json.loads(sent["body"].decode("utf-8"))
    assert body == {
        "strategy_id": "momentum-v3",
        "position_size_usd": 5000.0,
        "leverage": 3.0,
        "strategy_revision_id": "srev_abc",
        "submitted_by": "alice",
    }


def test_run_register_with_cio_idempotency_byte_identical_resends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR54-B AC3: re-register with the same args → byte-identical request body.
    PortfolioTracker.record_admit replaces the per-strategy entry in a dict,
    so two byte-identical POSTs leave portfolio state unchanged after the
    second."""
    opens: list[bytes] = []

    class _CapOpener:
        def open(self, req: Any, timeout: float = 0) -> _FakeResponse:
            opens.append(req.data)
            return _FakeResponse(201, b'{"status":"admitted"}')

    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: _CapOpener(),
    )
    argv = [
        "register-with-cio",
        "--strategy-id",
        "x",
        "--position-size-usd",
        "100",
        "--leverage",
        "2",
    ]
    assert cli_strategy.main(argv) == 0
    assert cli_strategy.main(argv) == 0
    assert opens[0] == opens[1]


def test_run_register_with_cio_omits_optional_fields() -> None:
    """When --strategy-revision-id/--submitted-by are absent the keys are
    NOT sent (rather than null) so the CIO Pydantic model uses its
    field defaults."""
    fake = _FakeOpener(_FakeResponse(201, b'{"status":"admitted"}'))
    args = cli_strategy.build_parser().parse_args(
        [
            "register-with-cio",
            "--strategy-id",
            "x",
            "--position-size-usd",
            "100",
            "--leverage",
            "2",
        ]
    )
    # Call run_register_with_cio directly with a monkey-patched build_opener
    import urllib.request as _ur

    orig = _ur.build_opener
    _ur.build_opener = lambda *a, **kw: fake  # type: ignore[assignment]
    try:
        rc = cli_strategy.run_register_with_cio(args)
    finally:
        _ur.build_opener = orig
    assert rc == 0
    sent_body = json.loads(fake.requests[0]["body"].decode("utf-8"))
    assert "strategy_revision_id" not in sent_body
    assert "submitted_by" not in sent_body


def test_run_register_with_cio_validates_position_size_negative(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = cli_strategy.main(
        [
            "register-with-cio",
            "--strategy-id",
            "x",
            "--position-size-usd",
            "-1",
            "--leverage",
            "2",
        ]
    )
    assert rc == 2
    assert ">= 0" in capsys.readouterr().err


def test_run_register_with_cio_validates_leverage_below_one(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = cli_strategy.main(
        [
            "register-with-cio",
            "--strategy-id",
            "x",
            "--position-size-usd",
            "100",
            "--leverage",
            "0.5",
        ]
    )
    assert rc == 2
    assert ">= 1" in capsys.readouterr().err


def test_run_register_with_cio_handles_http_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import urllib.error as _err

    class _ErrOpener:
        def open(self, req: Any, timeout: float = 0) -> Any:
            raise _err.HTTPError(
                req.full_url, 503, "tracker missing", {}, io.BytesIO(b"down")
            )

    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: _ErrOpener(),
    )
    rc = cli_strategy.main(
        [
            "register-with-cio",
            "--strategy-id",
            "x",
            "--position-size-usd",
            "100",
            "--leverage",
            "2",
        ]
    )
    assert rc == 1
    assert "HTTP 503" in capsys.readouterr().err


def test_run_register_with_cio_handles_url_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import urllib.error as _err

    class _ErrOpener:
        def open(self, req: Any, timeout: float = 0) -> Any:
            raise _err.URLError("connection refused")

    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: _ErrOpener(),
    )
    rc = cli_strategy.main(
        [
            "register-with-cio",
            "--strategy-id",
            "x",
            "--position-size-usd",
            "100",
            "--leverage",
            "2",
        ]
    )
    assert rc == 1
    assert "cannot reach" in capsys.readouterr().err


def test_run_register_with_cio_handles_non_json_response(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake = _FakeOpener(_FakeResponse(201, b"not-json"))
    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: fake,
    )
    rc = cli_strategy.main(
        [
            "register-with-cio",
            "--strategy-id",
            "x",
            "--position-size-usd",
            "100",
            "--leverage",
            "2",
        ]
    )
    assert rc == 1
    assert "non-JSON" in capsys.readouterr().err


# ─── AC4 — end-to-end FR54-A → FR54-B chain ─────────────────────────────────


def test_fr54_b_end_to_end_persist_then_register(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC4 — end-to-end test:
    1. Persist a CharacterizationArtifact via persist-characterization.
    2. Register the same strategy with CIO via register-with-cio.
    3. Both records exist and the strategy_revision_id is bound across them.
    4. Re-running both is a no-op (byte-identical request bodies).
    """
    art_path = _write_artifact(tmp_path)
    # Two routing buckets keyed by host: data-manager and cio. The fake opener
    # routes each request to the correct response bucket and records both for
    # cross-record consistency assertions.
    dm_responses: list[_FakeResponse] = [
        _FakeResponse(201, b'{"strategy_id":"momentum-v3","strategy_version":"v1"}'),
        _FakeResponse(201, b'{"strategy_id":"momentum-v3","strategy_version":"v1"}'),
    ]
    cio_responses: list[_FakeResponse] = [
        _FakeResponse(201, b'{"strategy_id":"momentum-v3","status":"admitted"}'),
        _FakeResponse(201, b'{"strategy_id":"momentum-v3","status":"admitted"}'),
    ]
    dm_recorded: list[bytes] = []
    cio_recorded: list[bytes] = []

    class _RoutingOpener:
        def open(self, req: Any, timeout: float = 0) -> _FakeResponse:
            url = req.full_url
            if "/api/characterizations" in url:
                dm_recorded.append(req.data)
                return dm_responses.pop(0)
            if "/api/admission/register" in url:
                cio_recorded.append(req.data)
                return cio_responses.pop(0)
            raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr(
        cli_strategy.urllib.request,
        "build_opener",
        lambda *a, **kw: _RoutingOpener(),
    )

    # Step 1: persist
    rc1 = cli_strategy.main(
        [
            "persist-characterization",
            "--artifact-file",
            str(art_path),
            "--strategy-version",
            "v1",
            "--seed",
            "7",
            "--data-manager-url",
            "http://dm.local/",
        ]
    )
    assert rc1 == 0

    # Step 2: register with CIO using the artifact's revision id
    artifact = json.loads(art_path.read_text(encoding="utf-8"))
    rc2 = cli_strategy.main(
        [
            "register-with-cio",
            "--strategy-id",
            artifact["strategy_id"],
            "--position-size-usd",
            "5000",
            "--leverage",
            "3",
            "--strategy-revision-id",
            artifact["strategy_revision_id"],
            "--submitted-by",
            "alice",
            "--cio-url",
            "http://cio.local/",
        ]
    )
    assert rc2 == 0

    # Both records were emitted
    assert len(dm_recorded) == 1
    assert len(cio_recorded) == 1

    # Bound to the same strategy revision id across services
    dm_body = json.loads(dm_recorded[0].decode("utf-8"))
    cio_body = json.loads(cio_recorded[0].decode("utf-8"))
    assert (
        dm_body["strategy_revision_id"]
        == cio_body["strategy_revision_id"]
        == "srev_abc123def456_789012ghi345"
    )
    assert dm_body["strategy_id"] == cio_body["strategy_id"] == "momentum-v3"

    # Step 3 — AC3 idempotency: re-run both, expect byte-identical request bodies
    rc3 = cli_strategy.main(
        [
            "persist-characterization",
            "--artifact-file",
            str(art_path),
            "--strategy-version",
            "v1",
            "--seed",
            "7",
            "--data-manager-url",
            "http://dm.local/",
        ]
    )
    rc4 = cli_strategy.main(
        [
            "register-with-cio",
            "--strategy-id",
            artifact["strategy_id"],
            "--position-size-usd",
            "5000",
            "--leverage",
            "3",
            "--strategy-revision-id",
            artifact["strategy_revision_id"],
            "--submitted-by",
            "alice",
            "--cio-url",
            "http://cio.local/",
        ]
    )
    assert rc3 == 0
    assert rc4 == 0
    assert dm_recorded[0] == dm_recorded[1]
    assert cio_recorded[0] == cio_recorded[1]
