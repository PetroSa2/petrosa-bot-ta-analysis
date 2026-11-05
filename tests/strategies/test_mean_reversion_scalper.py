"""
Tests for the Mean Reversion Scalper strategy.
"""

import pandas as pd
import pytest

from ta_bot.strategies.mean_reversion_scalper import MeanReversionScalperStrategy


@pytest.fixture
def sample_data():
    """Create sample OHLCV data for testing."""
    return pd.DataFrame(
        {
            "open": [100, 101, 102, 103, 104],
            "high": [105, 106, 107, 108, 109],
            "low": [95, 96, 97, 98, 99],
            "close": [102, 103, 104, 105, 106],
            "volume": [1000, 1100, 1200, 1300, 1400],
        }
    )


@pytest.fixture
def sample_indicators():
    """Create sample indicators data for testing."""
    return {
        "bb_lower": pd.Series([90, 91, 92, 93, 94]),
        "bb_upper": pd.Series([110, 111, 112, 113, 114]),
        "bb_middle": pd.Series([100, 101, 102, 103, 104]),
        "rsi": pd.Series([30, 35, 40, 45, 50]),
        "close": pd.Series([102, 103, 104, 105, 106]),
    }


class TestMeanReversionScalperStrategy:
    """Test cases for MeanReversionScalperStrategy."""

    def test_strategy_initialization(self):
        """Test that strategy initializes correctly."""
        strategy = MeanReversionScalperStrategy()
        assert strategy is not None

    def test_analyze_with_valid_data(self, sample_data, sample_indicators):
        """Test strategy analysis with valid data."""
        strategy = MeanReversionScalperStrategy()
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **sample_indicators}

        signal = strategy.analyze(sample_data, metadata)

        # Signal may or may not be generated based on conditions
        if signal:
            assert signal.symbol == "BTCUSDT"
            assert signal.timeframe == "15m"
            assert signal.strategy_id == "mean_reversion_scalper"
            assert signal.action in ["buy", "sell"]
            assert signal.confidence >= 0.5
            assert signal.stop_loss is not None
            assert signal.take_profit is not None

    def test_analyze_insufficient_data(self):
        """Test strategy with insufficient data."""
        strategy = MeanReversionScalperStrategy()
        df = pd.DataFrame({"close": [100]})  # Only one data point
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m"}

        signal = strategy.analyze(df, metadata)
        assert signal is None

    def test_analyze_missing_indicators(self, sample_data):
        """Test strategy with missing indicators."""
        strategy = MeanReversionScalperStrategy()
        # Missing some required indicators
        incomplete_indicators = {
            "bb_lower": pd.Series([90, 91, 92, 93, 94]),
            "bb_upper": pd.Series([110, 111, 112, 113, 114]),
            # Missing bb_middle, rsi and close
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **incomplete_indicators}

        signal = strategy.analyze(sample_data, metadata)
        assert signal is None

    def test_analyze_no_mean_reversion_pattern(self, sample_data):
        """Test strategy when no mean reversion pattern is detected."""
        strategy = MeanReversionScalperStrategy()
        # Price near middle band (no extreme)
        df = pd.DataFrame(
            {
                "open": [100, 101, 102, 103, 104],
                "high": [105, 106, 107, 108, 109],
                "low": [95, 96, 97, 98, 99],
                "close": [102, 103, 104, 105, 106],  # Near middle
                "volume": [1000, 1100, 1200, 1300, 1400],
            }
        )

        indicators = {
            "bb_lower": pd.Series([90, 91, 92, 93, 94]),
            "bb_upper": pd.Series([110, 111, 112, 113, 114]),
            "bb_middle": pd.Series([100, 101, 102, 103, 104]),
            "rsi": pd.Series([30, 35, 40, 45, 50]),
            "close": pd.Series([102, 103, 104, 105, 106]),
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **indicators}

        signal = strategy.analyze(df, metadata)
        assert signal is None

    def test_analyze_zero_ema21_returns_none(self):
        """Issue #297: ema21 == 0 must not raise ZeroDivisionError in the
        deviation calculation (abs(close - ema21) / ema21) -- the strategy
        should skip signal generation instead."""
        strategy = MeanReversionScalperStrategy()
        n = 25
        df = pd.DataFrame(
            {
                "open": [100] * n,
                "high": [105] * n,
                "low": [95] * n,
                "close": [102] * n,
                "volume": [1000] * n,
            }
        )
        indicators = {
            "ema21": pd.Series([0] * n),
            "rsi": pd.Series([20] * n),
            "close": pd.Series([102] * n),
            "bb_lower": pd.Series([90] * n),
            "bb_upper": pd.Series([110] * n),
        }
        metadata = {"symbol": "BTCUSDT", "timeframe": "15m", **indicators}

        signal = strategy.analyze(df, metadata)

        assert signal is None


def _deep_band_case(action):
    """A close more than 1.5% beyond its band (#375): the old band stop was on the wrong side."""
    n = 30
    if action == "buy":
        closes = [100.0] * (n - 3) + [97.0, 96.0, 95.0]
        bb_lower, bb_upper, rsi = 97.0, 104.0, 20.0  # 97 * 0.985 = 95.545 > 95
    else:
        closes = [100.0] * (n - 3) + [103.0, 104.0, 105.0]
        bb_lower, bb_upper, rsi = 96.0, 103.0, 80.0  # 103 * 1.015 = 104.545 < 105
    df = pd.DataFrame(
        {
            "open": closes,
            "high": [c + 0.5 for c in closes],
            "low": [c - 0.5 for c in closes],
            "close": closes,
            "volume": [1000.0] * n,
        }
    )
    metadata = {
        "symbol": "ADAUSDT",
        "timeframe": "15m",
        "ema21": pd.Series([100.0] * n),
        "rsi": pd.Series([rsi] * n),
        "bb_lower": pd.Series([bb_lower] * n),
        "bb_upper": pd.Series([bb_upper] * n),
        "atr": pd.Series([0.8] * n),
    }
    return df, metadata


def test_deep_oversold_buy_stop_is_below_the_close():
    df, metadata = _deep_band_case("buy")

    signal = MeanReversionScalperStrategy().analyze(df, metadata)

    assert signal is not None and signal.action == "buy"
    assert signal.stop_loss < signal.current_price
    assert signal.stop_loss == pytest.approx(95.0 - 2 * 0.8)
    assert signal.metadata["stop_source"] == "volatility"


def test_deep_overbought_sell_stop_is_above_the_close():
    df, metadata = _deep_band_case("sell")

    signal = MeanReversionScalperStrategy().analyze(df, metadata)

    assert signal is not None and signal.action == "sell"
    assert signal.stop_loss > signal.current_price
    assert signal.stop_loss == pytest.approx(105.0 + 2 * 0.8)
    assert signal.metadata["stop_source"] == "volatility"


def test_a_band_stop_on_the_protective_side_is_unchanged():
    df, metadata = _deep_band_case("buy")
    metadata["bb_lower"] = pd.Series([95.5] * len(df))  # 95.5 * 0.985 = 94.07 < 95

    signal = MeanReversionScalperStrategy().analyze(df, metadata)

    assert signal is not None
    assert signal.stop_loss == pytest.approx(95.5 * 0.985)
    assert signal.metadata["stop_source"] == "level"


def test_no_signal_without_a_protective_stop():
    df, metadata = _deep_band_case("buy")
    del metadata["atr"]
    metadata["bb_upper"] = metadata["bb_lower"]  # no measurable volatility either

    assert MeanReversionScalperStrategy().analyze(df, metadata) is None
