"""End-to-end FR54 zero-shim verification test (AC2, petrosa-bot-ta-analysis#257).

Chains FR54-A (submit) → FR54-B (persist-characterization + register-with-cio)
→ FR54-C (status) with no live HTTP calls.

Zero-shim assertions:
  1. No new .py files added to ta_bot/ since origin/main.
  2. No k8s/ directory exists in this repo (manifests live in petrosa_k8s).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from ta_bot import cli_strategy

# ---------------------------------------------------------------------------
# Fake HTTP transport
# ---------------------------------------------------------------------------


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


class _RoutingOpener:
    """Routes each request to a canned (status, body) by longest matching path pattern."""

    def __init__(self, routes: dict[str, tuple[int, bytes]]) -> None:
        self._routes = routes

    def open(self, req: Any, timeout: float | None = None) -> _FakeResponse:  # noqa: ARG002
        url: str = req.full_url
        for pattern, (status, body) in sorted(
            self._routes.items(), key=lambda kv: -len(kv[0])
        ):
            if pattern in url:
                return _FakeResponse(status, body)
        raise RuntimeError(f"No fake route registered for URL: {url!r}")


# ---------------------------------------------------------------------------
# Fixtures / shared data
# ---------------------------------------------------------------------------

_SAMPLE_CODE = "def signal(*a, **kw):\n    return None\n"

_SAMPLE_ARTIFACT: dict[str, Any] = {
    "strategy_id": "fr54c_e2e_strategy",
    "range_from": "2026-01-01",
    "range_to": "2026-03-31",
    "edge_estimate": {
        "sharpe_ratio": 1.5,
        "win_rate": 0.62,
        "expected_pnl": 0.021,
        "trade_count": 47,
    },
    "drawdown_envelope": {"p50": 0.01, "p90": 0.03, "p99": 0.05, "p100": 0.08},
    "sensitivity_analysis": {
        "parameter": "confidence_threshold",
        "points": [{"x": 0.5, "sharpe": 1.2}, {"x": 0.7, "sharpe": 1.5}],
    },
    "strategy_revision_id": "srev_aabbcc112233_ddeeff445566",
    "strategy_revision": {
        "revision_id": "srev_aabbcc112233_ddeeff445566",
        "module_hash": "aabbcc112233",
        "parameter_hash": "ddeeff445566",
    },
}

_DM = "http://data-manager.e2e"
_CIO = "http://cio.e2e"
_STRATEGY_ID = "fr54c_e2e_strategy"


@pytest.fixture()
def strategy_files(tmp_path: Path) -> dict[str, Path]:
    code = tmp_path / "strategy.py"
    code.write_text(_SAMPLE_CODE, encoding="utf-8")
    artifact = tmp_path / "artifact.json"
    artifact.write_text(json.dumps(_SAMPLE_ARTIFACT), encoding="utf-8")
    return {"code": code, "artifact": artifact}


def _multi_service_opener(lifecycle_state: str = "registered") -> _RoutingOpener:
    return _RoutingOpener(
        {
            "/api/strategies": (
                201,
                json.dumps(
                    {
                        "strategy_id": _STRATEGY_ID,
                        "status": lifecycle_state,
                        "registered_at": "2026-06-14T00:00:00Z",
                    }
                ).encode(),
            ),
            "/api/characterizations": (
                201,
                json.dumps(
                    {
                        "strategy_id": _STRATEGY_ID,
                        "strategy_version": "v1.0",
                        "persisted": True,
                    }
                ).encode(),
            ),
            "/api/admission/register": (
                201,
                json.dumps(
                    {"strategy_id": _STRATEGY_ID, "status": "admitted"}
                ).encode(),
            ),
        }
    )


# ---------------------------------------------------------------------------
# AC2 — full chain integration tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestFR54EndToEnd:
    """FR54-C AC2: full FR54-A → FR54-B → FR54-C chain with zero live HTTP."""

    def test_submit_succeeds_and_returns_registered_status(
        self, strategy_files: dict[str, Path], capsys: pytest.CaptureFixture[str]
    ) -> None:
        import argparse

        args = argparse.Namespace(
            strategy_id=_STRATEGY_ID,
            code_file=strategy_files["code"],
            params={"window": 14},
            symbols=["BTCUSDT"],
            submitted_by="e2e_operator",
            signed_action_id="signed_e2e_abc",
            data_manager_url=_DM,
            timeout=5.0,
        )
        with patch(
            "urllib.request.build_opener",
            return_value=_multi_service_opener("registered"),
        ):
            rc = cli_strategy.run_submit(args)
        assert rc == 0
        result = json.loads(capsys.readouterr().out)
        assert result["strategy_id"] == _STRATEGY_ID
        assert result["status"] == "registered"

    def test_persist_characterization_succeeds(
        self, strategy_files: dict[str, Path]
    ) -> None:
        import argparse

        args = argparse.Namespace(
            artifact_file=strategy_files["artifact"],
            strategy_version="v1.0",
            seed=0,
            params_file=None,
            data_manager_url=_DM,
            timeout=5.0,
        )
        with patch("urllib.request.build_opener", return_value=_multi_service_opener()):
            rc = cli_strategy.run_persist_characterization(args)
        assert rc == 0

    def test_register_with_cio_succeeds(self) -> None:
        import argparse

        args = argparse.Namespace(
            strategy_id=_STRATEGY_ID,
            position_size_usd=500.0,
            leverage=2.0,
            strategy_revision_id="srev_aabbcc112233_ddeeff445566",
            submitted_by="e2e_operator",
            cio_url=_CIO,
            timeout=5.0,
        )
        with patch(
            "urllib.request.build_opener",
            return_value=_multi_service_opener("admitted"),
        ):
            rc = cli_strategy.run_register_with_cio(args)
        assert rc == 0

    @pytest.mark.parametrize(
        "lifecycle_state",
        ["registered", "backtested", "admitted", "live_trial", "graduated"],
    )
    def test_status_query_returns_each_lifecycle_state(
        self, lifecycle_state: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import argparse

        args = argparse.Namespace(
            strategy_id=_STRATEGY_ID,
            data_manager_url=_DM,
            timeout=5.0,
        )
        opener = _RoutingOpener(
            {
                f"/api/strategies/{_STRATEGY_ID}": (
                    200,
                    json.dumps(
                        {"strategy_id": _STRATEGY_ID, "status": lifecycle_state}
                    ).encode(),
                )
            }
        )
        with patch("urllib.request.build_opener", return_value=opener):
            rc = cli_strategy.run_status(args)
        assert rc == 0
        result = json.loads(capsys.readouterr().out)
        assert result["status"] == lifecycle_state

    def test_status_not_found_returns_exit_3(self) -> None:
        import argparse
        import urllib.error

        args = argparse.Namespace(
            strategy_id="nonexistent_strategy",
            data_manager_url=_DM,
            timeout=5.0,
        )

        class _Always404:
            def open(self, req: Any, timeout: float | None = None) -> None:  # noqa: ARG002
                raise urllib.error.HTTPError(
                    url=req.full_url, code=404, msg="Not Found", hdrs={}, fp=None
                )

        with patch("urllib.request.build_opener", return_value=_Always404()):
            rc = cli_strategy.run_status(args)
        assert rc == 3

    def test_full_sequential_chain(
        self, strategy_files: dict[str, Path], capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Runs submit → persist → register → status in sequence; every step must succeed."""
        import argparse

        opener = _multi_service_opener("admitted")

        # FR54-A: submit
        with patch("urllib.request.build_opener", return_value=opener):
            rc = cli_strategy.run_submit(
                argparse.Namespace(
                    strategy_id=_STRATEGY_ID,
                    code_file=strategy_files["code"],
                    params={"window": 14},
                    symbols=["BTCUSDT"],
                    submitted_by="e2e_operator",
                    signed_action_id="signed_e2e",
                    data_manager_url=_DM,
                    timeout=5.0,
                )
            )
        assert rc == 0, "FR54-A submit failed"
        capsys.readouterr()

        # FR54-B: persist-characterization
        with patch("urllib.request.build_opener", return_value=opener):
            rc = cli_strategy.run_persist_characterization(
                argparse.Namespace(
                    artifact_file=strategy_files["artifact"],
                    strategy_version="v1.0",
                    seed=0,
                    params_file=None,
                    data_manager_url=_DM,
                    timeout=5.0,
                )
            )
        assert rc == 0, "FR54-B persist-characterization failed"
        capsys.readouterr()

        # FR54-B: register-with-cio
        with patch("urllib.request.build_opener", return_value=opener):
            rc = cli_strategy.run_register_with_cio(
                argparse.Namespace(
                    strategy_id=_STRATEGY_ID,
                    position_size_usd=500.0,
                    leverage=2.0,
                    strategy_revision_id=None,
                    submitted_by=None,
                    cio_url=_CIO,
                    timeout=5.0,
                )
            )
        assert rc == 0, "FR54-B register-with-cio failed"
        capsys.readouterr()

        # FR54-C: status query (lifecycle state = admitted)
        status_opener = _RoutingOpener(
            {
                f"/api/strategies/{_STRATEGY_ID}": (
                    200,
                    json.dumps(
                        {"strategy_id": _STRATEGY_ID, "status": "admitted"}
                    ).encode(),
                )
            }
        )
        with patch("urllib.request.build_opener", return_value=status_opener):
            rc = cli_strategy.run_status(
                argparse.Namespace(
                    strategy_id=_STRATEGY_ID,
                    data_manager_url=_DM,
                    timeout=5.0,
                )
            )
        assert rc == 0, "FR54-C status query failed"
        result = json.loads(capsys.readouterr().out)
        assert result["strategy_id"] == _STRATEGY_ID
        assert result["status"] == "admitted"


# ---------------------------------------------------------------------------
# AC2 — zero-shim structural assertions
# ---------------------------------------------------------------------------


class TestFR54ZeroShimProperties:
    """Verify FR54 required no k8s manifests and no new source .py files."""

    def test_no_k8s_directory_in_bot_ta_analysis(self) -> None:
        """k8s manifests must live in petrosa_k8s, never in this service repo."""
        repo_root = Path(__file__).parent.parent
        assert not (repo_root / "k8s").exists(), (
            "k8s/ directory found in petrosa-bot-ta-analysis — "
            "manifests belong in petrosa_k8s"
        )

    def test_no_new_source_py_files_added_by_fr54c(self) -> None:
        """FR54-C must add zero new .py files to ta_bot/ (the source package).

        Compares HEAD against origin/main via ``git diff --diff-filter=A``.
        Skips gracefully when origin/main is unreachable (detached CI HEAD or
        shallow clone without remote).
        """
        repo_root = Path(__file__).parent.parent
        result = subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                "--diff-filter=A",
                "origin/main",
                "--",
                "ta_bot/",
            ],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip(f"git diff unavailable: {result.stderr.strip()}")
        new_source_files = [
            f for f in result.stdout.strip().splitlines() if f.endswith(".py")
        ]
        assert new_source_files == [], (
            f"FR54-C added unexpected new .py files to ta_bot/: {new_source_files}"
        )
