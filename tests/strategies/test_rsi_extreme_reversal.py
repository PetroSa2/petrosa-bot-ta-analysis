"""
Tests for the RSI Extreme Reversal strategy's config-parameter branch (#283).

`rsi_extreme_reversal.py` was, before #283, the *only* strategy file that
already read `self._get_config(metadata)` and branched on `params.get(...)`
-- but since `SignalEngine` never injected a "config" key into metadata,
`config` was always `None` and the `if config:` branch (lines 45-56) was
dead code; every call fell through to the hardcoded `else` (lines 58-68).
These tests prove the params branch is now reachable and actually changes
strategy behavior, not just that it doesn't crash.
"""

import pandas as pd
import pytest

from ta_bot.strategies.rsi_extreme_reversal import RSIExtremeReversalStrategy


def _make_df(n: int = 80) -> pd.DataFrame:
    """An alternating up/down series (small +0.2 gains, larger -1.0 losses)
    with enough rows to clear min_data_points (78). This shape produces a
    stable, computable RSI(2) of ~28.6 -- above the hardcoded/default
    oversold_threshold of 25 (so no signal), but below a looser override
    (so a signal fires). Empirically derived, not a magic number."""
    price = 100.0
    closes = [price]
    for i in range(n - 1):
        price += 0.2 if i % 2 == 0 else -1.0
        closes.append(price)
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    volumes = [1000] * n
    return pd.DataFrame(
        {
            "open": closes,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        }
    )


class TestRSIExtremeReversalConfigBranch:
    """AC4: assert the `if config:` branch (params.get) at lines 45-56 is
    reachable at runtime and is not the sole-unreachable path anymore."""

    def test_else_branch_is_not_the_only_reachable_path(self):
        """Directly proves AC4's literal wording: build a metadata dict WITH
        a "config" key (what SignalEngine now always injects per #283) and
        assert the strategy consults `params`, not the hardcoded literals.
        `_make_df()` produces RSI(2) ~= 28.6: above the hardcoded/default
        `oversold_threshold` of 25 (no signal), but a looser override
        (`oversold_threshold=30`) makes the same candle series signal.
        """
        strategy = RSIExtremeReversalStrategy()
        df = _make_df()

        # Baseline: no "config" key at all -> hardcoded else branch (25).
        # RSI(2) ~28.6 is NOT < 25, so this must be None.
        baseline_metadata = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
        }
        baseline_signal = strategy.analyze(df, baseline_metadata)

        # Same data, but metadata now carries the #283-style injected config
        # with a looser oversold_threshold the hardcoded branch could never
        # apply (it only ever uses 25, verbatim, in the else branch).
        override_metadata = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "config": {
                "parameters": {"oversold_threshold": 30},
                "version": 2,
                "source": "mongodb",
                "is_override": True,
            },
        }
        override_signal = strategy.analyze(df, override_metadata)

        # If the `if config:` branch (lines 45-56) were still unreachable
        # dead code, both calls would take the identical hardcoded path and
        # produce the identical (None) result. They diverge here, proving
        # params.get("oversold_threshold", ...) was actually consulted.
        assert baseline_signal is None
        assert override_signal is not None

    def test_config_none_still_uses_hardcoded_defaults(self):
        """Backward compatibility: metadata.get("config") returning None
        (e.g. a caller that never went through SignalEngine) must still hit
        the else branch with the exact pre-#283 literals."""
        strategy = RSIExtremeReversalStrategy()
        df = _make_df()
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", "config": None}
        signal = strategy.analyze(df, metadata)
        # Whatever the outcome, it must not raise, and must be consistent
        # with the same call without a "config" key at all.
        no_key_metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}
        signal_no_key = strategy.analyze(df, no_key_metadata)
        assert (signal is None) == (signal_no_key is None)
