"""Determinism + drift-sensitivity tests for the content-addressable strategy
revision (FR53 / P3.4 AC1).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

import pytest

from backtest.strategy_revision import (
    StrategyRevision,
    build_strategy_revision,
    compute_parameter_set_hash,
    compute_strategy_module_hash,
    compute_strategy_revision_id,
)


class _AlphaStrategy:
    """Stand-in strategy class A."""

    name = "alpha"


class _BetaStrategy:
    """Stand-in strategy class B (different source file would normally diverge;
    these two share a file so the test focuses on parameter-side drift)."""

    name = "beta"


@pytest.mark.unit
def test_revision_id_is_deterministic_same_inputs() -> None:
    a = compute_strategy_revision_id(_AlphaStrategy, {"rsi_period": 14})
    b = compute_strategy_revision_id(_AlphaStrategy, {"rsi_period": 14})
    assert a == b


@pytest.mark.unit
def test_revision_id_has_expected_shape() -> None:
    rid = compute_strategy_revision_id(_AlphaStrategy, {})
    assert rid.startswith("srev_")
    parts = rid.split("_")
    assert len(parts) == 3  # ['srev', module12, params12]
    assert len(parts[1]) == 12
    assert len(parts[2]) == 12
    assert all(c in "0123456789abcdef" for c in parts[1])
    assert all(c in "0123456789abcdef" for c in parts[2])


@pytest.mark.unit
def test_parameter_hash_invariant_to_key_order() -> None:
    h1 = compute_parameter_set_hash({"a": 1, "b": 2})
    h2 = compute_parameter_set_hash({"b": 2, "a": 1})
    assert h1 == h2


@pytest.mark.unit
def test_parameter_hash_treats_none_and_empty_equivalently() -> None:
    assert compute_parameter_set_hash(None) == compute_parameter_set_hash({})


@pytest.mark.unit
def test_parameter_hash_changes_with_value() -> None:
    h1 = compute_parameter_set_hash({"rsi_period": 14})
    h2 = compute_parameter_set_hash({"rsi_period": 21})
    assert h1 != h2


@pytest.mark.unit
def test_parameter_hash_changes_with_added_key() -> None:
    h1 = compute_parameter_set_hash({"rsi_period": 14})
    h2 = compute_parameter_set_hash({"rsi_period": 14, "extra": True})
    assert h1 != h2


@pytest.mark.unit
def test_parameter_hash_canonicalizes_datetime() -> None:
    naive = datetime(2026, 1, 1, 12, 0, 0)
    aware_utc = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    # Naive treated as UTC — matches data-manager compute_inputs_hash rule.
    assert compute_parameter_set_hash({"t": naive}) == compute_parameter_set_hash(
        {"t": aware_utc}
    )


@pytest.mark.unit
def test_parameter_hash_canonicalizes_enum_and_path() -> None:
    class Mode(Enum):
        A = "alpha"

    h_enum = compute_parameter_set_hash({"mode": Mode.A})
    h_str = compute_parameter_set_hash({"mode": "alpha"})
    assert h_enum == h_str

    h_path = compute_parameter_set_hash({"out": Path("/tmp/x")})
    h_pstr = compute_parameter_set_hash({"out": "/tmp/x"})
    assert h_path == h_pstr


@pytest.mark.unit
def test_parameter_hash_rejects_uncanonicalizable() -> None:
    class Unserializable:
        pass

    with pytest.raises(TypeError, match="Cannot canonicalize") as exc_info:
        compute_parameter_set_hash({"weird": Unserializable()})
    assert "Unserializable" in str(exc_info.value)


@pytest.mark.unit
def test_module_hash_changes_with_source_drift(tmp_path, monkeypatch) -> None:
    """Two classes loaded from different source files produce different
    module hashes — emulating a real code change between characterizations.
    """
    # Write two near-identical source files differing by one constant.
    src_a = tmp_path / "strat_a.py"
    src_a.write_text(
        "class Strat:\n    name = 'a'\n    threshold = 0.1\n",
        encoding="utf-8",
    )
    src_b = tmp_path / "strat_b.py"
    src_b.write_text(
        "class Strat:\n    name = 'a'\n    threshold = 0.2\n",
        encoding="utf-8",
    )
    import importlib.util
    import sys

    def _load(path: Path, mod_name: str):
        spec = importlib.util.spec_from_file_location(mod_name, path)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        # Register so inspect.getsourcefile / sys.modules lookups succeed.
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
        return mod.Strat

    cls_a = _load(src_a, "strat_a_test")
    cls_b = _load(src_b, "strat_b_test")
    try:
        assert compute_strategy_module_hash(cls_a) != compute_strategy_module_hash(
            cls_b
        )
    finally:
        sys.modules.pop("strat_a_test", None)
        sys.modules.pop("strat_b_test", None)


@pytest.mark.unit
def test_build_strategy_revision_round_trip() -> None:
    rev = build_strategy_revision(
        strategy_id="alpha",
        strategy_cls=_AlphaStrategy,
        parameters={"x": 1},
    )
    assert isinstance(rev, StrategyRevision)
    assert rev.strategy_id == "alpha"
    assert rev.revision_id.startswith("srev_")
    assert len(rev.module_hash) == 64
    assert len(rev.parameter_hash) == 64

    as_dict = rev.to_dict()
    restored = StrategyRevision.from_dict(as_dict)
    assert restored == rev


@pytest.mark.unit
def test_distinct_strategies_yield_distinct_module_hashes() -> None:
    # Use real strategy classes — different source files guarantee divergence.
    from ta_bot.strategies.momentum_pulse import MomentumPulseStrategy
    from ta_bot.strategies.rsi_extreme_reversal import RSIExtremeReversalStrategy

    h1 = compute_strategy_module_hash(MomentumPulseStrategy)
    h2 = compute_strategy_module_hash(RSIExtremeReversalStrategy)
    assert h1 != h2
