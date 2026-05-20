"""CLI surface tests — argument parsing + fixture-backed smoke run."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from backtest.cli import build_parser, main

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "candles_BTCUSDT_15m_recorded.json"


@pytest.mark.unit
def test_parser_requires_strategy_from_to() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args([])
    assert exc_info.value.code != 0


@pytest.mark.unit
def test_parser_parses_iso_dates() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--strategy",
            "momentum_pulse",
            "--from",
            "2026-01-01",
            "--to",
            "2026-12-31",
        ]
    )
    assert args.strategy == "momentum_pulse"
    assert isinstance(args.range_from, datetime)
    assert isinstance(args.range_to, datetime)
    assert args.range_to >= args.range_from


@pytest.mark.unit
def test_parser_rejects_garbage_date() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(
            [
                "--strategy",
                "momentum_pulse",
                "--from",
                "not-a-date",
                "--to",
                "2026-12-31",
            ]
        )
    assert exc_info.value.code != 0


@pytest.mark.e2e
def test_cli_runs_against_fixture_and_writes_output(tmp_path) -> None:
    out_path = tmp_path / "artifact.json"
    exit_code = main(
        [
            "--strategy",
            "momentum_pulse",
            "--from",
            "2026-01-01",
            "--to",
            "2026-12-31",
            "--warmup",
            "60",
            "--fixture",
            str(FIXTURE_PATH),
            "--output",
            str(out_path),
        ]
    )
    assert exit_code == 0
    assert out_path.exists()
    payload = json.loads(out_path.read_text())
    assert payload["strategy_id"] == "momentum_pulse"
    assert payload["source"] == "backtest"
    assert payload["candle_count"] == 260


@pytest.mark.e2e
def test_cli_inverted_range_returns_error() -> None:
    exit_code = main(
        [
            "--strategy",
            "momentum_pulse",
            "--from",
            "2026-12-31",
            "--to",
            "2026-01-01",
            "--fixture",
            str(FIXTURE_PATH),
        ]
    )
    assert exit_code == 2
