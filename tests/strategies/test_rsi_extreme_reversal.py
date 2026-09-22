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


def _oversold_df(n: int = 80, scale: float = 1.0) -> pd.DataFrame:
    """A steadily declining series that drives RSI(2) into the oversold
    zone (< 25) reliably, so `analyze()` reaches the stop_loss/take_profit
    calculation instead of returning None earlier for lack of a signal.

    `scale` uniformly rescales the whole series (closes, wick margins).
    RSI(2) is computed from ratios of successive close deltas, so it is
    scale-invariant -- the same RSI trajectory (and therefore the same
    buy/no-signal outcome) is reproduced at any scale, only the absolute
    price level changes. This lets low-price-level tests (e.g. the risk
    floor below) reuse the exact same proven-oversold shape.
    """
    closes = [(200.0 - i * 1.5) * scale for i in range(n)]
    highs = [c + 0.5 * scale for c in closes]
    lows = [c - 0.5 * scale for c in closes]
    volumes = [1000.0] * n
    return pd.DataFrame(
        {
            "open": closes,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        }
    )


class TestRSIExtremeReversalZeroPriceGuard:
    """Issue #307: `close <= 0` on a corrupted/incomplete candle previously
    reached the stop_loss/take_profit calculation unguarded, producing
    stop_loss=0.0 and take_profit=0.0. SignalEngine's positive-risk-params
    validation then rejected every such signal with "risk parameters must
    be positive", silently dropping all rsi_extreme_reversal signals for
    that candle."""

    def test_zero_close_returns_none(self):
        strategy = RSIExtremeReversalStrategy()
        df = _oversold_df()
        df.loc[df.index[-1], "close"] = 0.0
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(df, metadata)

        assert signal is None

    def test_negative_close_returns_none(self):
        strategy = RSIExtremeReversalStrategy()
        df = _oversold_df()
        df.loc[df.index[-1], "close"] = -5.0
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(df, metadata)

        assert signal is None

    def test_non_finite_close_returns_none(self):
        strategy = RSIExtremeReversalStrategy()
        df = _oversold_df()
        df.loc[df.index[-1], "close"] = float("nan")

        signal = strategy.analyze(df, {"symbol": "BTCUSDT", "timeframe": "15m"})

        assert signal is None

    def test_zero_support_falls_back_to_positive_stop_loss(self):
        strategy = RSIExtremeReversalStrategy()
        df = _oversold_df()
        df.loc[df.index[-5:], "low"] = 0.0

        signal = strategy.analyze(df, {"symbol": "BTCUSDT", "timeframe": "15m"})

        assert signal is not None
        assert signal.stop_loss is not None
        assert signal.take_profit is not None
        assert signal.stop_loss > 0
        assert signal.take_profit > 0

    def test_oversold_signal_never_has_zero_or_negative_risk_params(self):
        """Sanity check: a genuine oversold signal on healthy candles still
        fires, and its stop_loss/take_profit are strictly positive (no
        regression from the close <= 0 guard or the risk_amount floor)."""
        strategy = RSIExtremeReversalStrategy()
        df = _oversold_df()
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(df, metadata)

        assert signal is not None
        assert signal.action == "buy"
        assert signal.stop_loss is not None
        assert signal.take_profit is not None
        assert signal.stop_loss > 0
        assert signal.take_profit > 0
        assert signal.take_profit > signal.current_price > signal.stop_loss

    def test_small_price_signal_selects_the_0_01_risk_floor(self):
        """Exercise the explicit `max(..., 0.01)` risk_amount floor itself,
        not just the close <= 0 guard: at a small-enough price level, both
        `close - stop_loss` and `close * 0.005` fall below 0.01, so 0.01
        must be the value actually selected and propagated into
        take_profit. Raised by Copilot review on PR #309."""
        strategy = RSIExtremeReversalStrategy()
        df = _oversold_df(scale=0.006)
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(df, metadata)

        assert signal is not None
        assert signal.stop_loss is not None
        assert signal.take_profit is not None
        close = signal.current_price
        # Precondition: neither non-floor candidate would reach 0.01 on
        # its own -- otherwise this test would not actually exercise the
        # floor branch.
        assert (close - signal.stop_loss) < 0.01
        assert (close * 0.005) < 0.01
        assert signal.take_profit == pytest.approx(close + 0.01 * 2.0)
