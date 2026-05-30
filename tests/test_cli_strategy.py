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
