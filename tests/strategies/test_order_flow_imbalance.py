"""
Tests for the Order Flow Imbalance strategy.

Covers #296: support_level/resistance_level computed via a plain
df["low"/"high"].iloc[-20:-10].min()/max() can silently return 0.0 when the
window contains zero prices, or misbehave on an empty/short-window slice,
producing an invalid stop_loss=0.0 that later fails risk-parameter
validation downstream.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from ta_bot.strategies.order_flow_imbalance import OrderFlowImbalanceStrategy


@pytest.fixture
def sample_data():
    """Create sample OHLCV data for testing (25 rows, well-formed)."""
    n = 25
    return pd.DataFrame(
        {
            "open": [100.0] * n,
            "high": [105.0] * n,
            "low": [95.0] * n,
            "close": [102.0] * n,
            "volume": [1000.0] * n,
        }
    )


@pytest.fixture
def sample_indicators():
    """Create sample indicator series for testing."""
    n = 25
    return {
        "close": pd.Series([102.0] * n),
        "volume": pd.Series([1000.0] * n),
        "rsi": pd.Series([50.0] * n),
        "volume_sma": pd.Series([800.0] * n),
    }


class TestOrderFlowImbalanceStrategy:
    """Test cases for OrderFlowImbalanceStrategy."""

    def test_strategy_initialization(self):
        """Test that strategy initializes correctly."""
        strategy = OrderFlowImbalanceStrategy()
        assert strategy is not None

    def test_analyze_insufficient_data(self):
        """Test strategy with insufficient data returns None early."""
        strategy = OrderFlowImbalanceStrategy()
        df = pd.DataFrame({"close": [100]})
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(df, metadata)
        assert signal is None

    def test_analyze_missing_indicators(self, sample_data):
        """Test strategy with missing required indicators returns None."""
        strategy = OrderFlowImbalanceStrategy()
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(sample_data, metadata)
        assert signal is None

    def test_analyze_no_accumulation_or_distribution(
        self, sample_data, sample_indicators
    ):
        """Flat, uniform data has no accumulation/distribution pattern -> None."""
        strategy = OrderFlowImbalanceStrategy()
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **sample_indicators}

        signal = strategy.analyze(sample_data, metadata)
        assert signal is None


class TestDegenerateCandleGuards:
    """Issue #302: three additional unguarded divisions distinct from #296's
    _safe_level fix -- _detect_accumulation/_detect_distribution's
    price_range = (high - low) / low, and _check_price_consolidation's
    price_range = (max - min) / mean. All must skip cleanly on a zero
    denominator instead of raising/warning."""

    def test_detect_accumulation_zero_low_does_not_raise(self):
        strategy = OrderFlowImbalanceStrategy()
        n = 15
        df = pd.DataFrame(
            {
                "open": [100.0] * n,
                "high": [105.0] * n,
                "low": [0.0] * n,
                "close": [102.0] * n,
                "volume": [1000.0] * n,
            }
        )

        result = strategy._detect_accumulation(df)
        assert result is False

    def test_detect_distribution_zero_low_does_not_raise(self):
        strategy = OrderFlowImbalanceStrategy()
        n = 15
        df = pd.DataFrame(
            {
                "open": [100.0] * n,
                "high": [105.0] * n,
                "low": [0.0] * n,
                "close": [102.0] * n,
                "volume": [1000.0] * n,
            }
        )

        result = strategy._detect_distribution(df)
        assert result is False

    def test_check_price_consolidation_zero_mean_returns_false(self):
        strategy = OrderFlowImbalanceStrategy()
        n = 15
        df = pd.DataFrame(
            {
                "open": [0.0] * n,
                "high": [0.0] * n,
                "low": [0.0] * n,
                "close": [0.0] * n,
                "volume": [1000.0] * n,
            }
        )

        result = strategy._check_price_consolidation(df)
        assert result is False


class TestSafeLevelHelper:
    """Direct unit tests for the _safe_level guard introduced for #296."""

    def test_safe_level_min_filters_zero_prices(self):
        prices = pd.Series([0.0, 0.0, 5.0, 6.0, 0.0])
        result = OrderFlowImbalanceStrategy._safe_level(prices, "min")
        assert result == 5.0

    def test_safe_level_max_filters_zero_prices(self):
        prices = pd.Series([0.0, 12.0, 0.0, 9.0])
        result = OrderFlowImbalanceStrategy._safe_level(prices, "max")
        assert result == 12.0

    def test_safe_level_all_zero_returns_none(self):
        prices = pd.Series([0.0] * 10)
        assert OrderFlowImbalanceStrategy._safe_level(prices, "min") is None
        assert OrderFlowImbalanceStrategy._safe_level(prices, "max") is None

    def test_safe_level_empty_slice_returns_none(self):
        prices = pd.Series([], dtype=float)
        assert OrderFlowImbalanceStrategy._safe_level(prices, "min") is None

    def test_safe_level_negative_and_nan_filtered_out(self):
        prices = pd.Series([-5.0, float("nan"), 0.0, 3.5])
        assert OrderFlowImbalanceStrategy._safe_level(prices, "min") == 3.5

    def test_safe_level_none_input_returns_none(self):
        assert OrderFlowImbalanceStrategy._safe_level(None, "min") is None


class TestOrderFlowImbalanceZeroStopLossGuard:
    """
    Reproduces the #296 bug scenario end-to-end through analyze(): forces the
    accumulation/distribution branch via mocking the pattern detectors (their
    own heuristics are exercised separately) and verifies analyze() never
    returns a signal with stop_loss <= 0, skipping signal generation instead.
    """

    def _build_metadata(self, n: int, low_window_zero: bool = False):
        df = pd.DataFrame(
            {
                "open": [100.0] * n,
                "high": [105.0] * n,
                "low": ([0.0] * n if low_window_zero else [95.0] * n),
                "close": [102.0] * n,
                "volume": [1000.0] * n,
            }
        )
        indicators = {
            "close": pd.Series([102.0] * n),
            "volume": pd.Series([1000.0] * n),
            "rsi": pd.Series([50.0] * n),
            "volume_sma": pd.Series([800.0] * n),
        }
        metadata = {"symbol": "TESTUSDT", "timeframe": "15m", **indicators}
        return df, metadata

    @patch.object(
        OrderFlowImbalanceStrategy, "_detect_distribution", return_value=False
    )
    @patch.object(OrderFlowImbalanceStrategy, "_detect_accumulation", return_value=True)
    def test_buy_signal_skipped_when_support_window_all_zero(
        self, mock_accum, mock_dist
    ):
        """
        Bug repro: support window all-zero used to yield stop_loss=0.0.
        Fixed behavior: analyze() returns None instead of an invalid signal.
        """
        strategy = OrderFlowImbalanceStrategy()
        df, metadata = self._build_metadata(25, low_window_zero=True)

        signal = strategy.analyze(df, metadata)
        assert signal is None

    @patch.object(OrderFlowImbalanceStrategy, "_detect_distribution", return_value=True)
    @patch.object(
        OrderFlowImbalanceStrategy, "_detect_accumulation", return_value=False
    )
    def test_sell_signal_skipped_when_resistance_window_all_zero(
        self, mock_accum, mock_dist
    ):
        """Same guard applied to the distribution/sell branch (resistance_level)."""
        strategy = OrderFlowImbalanceStrategy()
        n = 25
        df = pd.DataFrame(
            {
                "open": [100.0] * n,
                "high": [0.0] * n,  # zero resistance window
                "low": [95.0] * n,
                "close": [102.0] * n,
                "volume": [1000.0] * n,
            }
        )
        indicators = {
            "close": pd.Series([102.0] * n),
            "volume": pd.Series([1000.0] * n),
            "rsi": pd.Series([50.0] * n),
            "volume_sma": pd.Series([800.0] * n),
        }
        metadata = {"symbol": "TESTUSDT", "timeframe": "15m", **indicators}

        signal = strategy.analyze(df, metadata)
        assert signal is None

    @patch.object(
        OrderFlowImbalanceStrategy, "_detect_distribution", return_value=False
    )
    @patch.object(OrderFlowImbalanceStrategy, "_detect_accumulation", return_value=True)
    def test_buy_signal_skipped_when_support_window_empty(self, mock_accum, mock_dist):
        """Short dataframe (< 20 rows) makes iloc[-20:-10] an empty slice."""
        strategy = OrderFlowImbalanceStrategy()
        # len(df) must be >= 20 to pass the top-level guard, but the -20:-10
        # window still ends up empty when fewer than 10 rows precede index -10
        # is not achievable with len>=20; instead directly validate via a
        # monkeypatched slice by shrinking effective history through NaNs.
        df, metadata = self._build_metadata(20, low_window_zero=False)
        df.loc[df.index[-20:-10], "low"] = float("nan")

        signal = strategy.analyze(df, metadata)
        assert signal is None

    @patch.object(
        OrderFlowImbalanceStrategy, "_detect_distribution", return_value=False
    )
    @patch.object(OrderFlowImbalanceStrategy, "_detect_accumulation", return_value=True)
    def test_buy_signal_generated_with_valid_positive_support(
        self, mock_accum, mock_dist
    ):
        """Sanity check: a valid, positive support window still produces a
        signal with a strictly positive stop_loss (no regression)."""
        strategy = OrderFlowImbalanceStrategy()
        df, metadata = self._build_metadata(25, low_window_zero=False)

        signal = strategy.analyze(df, metadata)

        assert signal is not None
        assert signal.stop_loss is not None
        assert signal.stop_loss > 0
        assert signal.take_profit is not None
