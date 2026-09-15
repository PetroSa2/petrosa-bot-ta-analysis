"""
Tests for the signal engine module.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
from pydantic import ValidationError

from ta_bot.core.signal_engine import SignalEngine
from ta_bot.models.signal import Signal, SignalStrength


class TestSignalEngine:
    """Test cases for the signal engine."""

    @pytest.fixture
    def signal_engine(self):
        """Create a signal engine instance."""
        return SignalEngine()

    @pytest.fixture
    def sample_candles(self):
        """Create sample candle data."""
        return pd.DataFrame(
            {
                "open": [
                    44.25,
                    44.00,
                    44.10,
                    43.50,
                    44.25,
                    44.80,
                    45.20,
                    45.90,
                    45.90,
                    45.90,
                ],
                "high": [
                    44.50,
                    44.25,
                    44.30,
                    43.75,
                    44.50,
                    45.00,
                    45.50,
                    46.00,
                    46.25,
                    46.50,
                ],
                "low": [
                    44.00,
                    43.75,
                    43.80,
                    43.25,
                    43.75,
                    44.25,
                    44.75,
                    45.25,
                    45.50,
                    45.75,
                ],
                "close": [
                    44.34,
                    44.09,
                    44.15,
                    43.61,
                    44.33,
                    44.83,
                    45.18,
                    45.87,
                    45.87,
                    45.87,
                ],
                "volume": [1000, 1200, 800, 1500, 1100, 900, 1300, 1400, 1600, 1200],
            }
        )

    def test_signal_engine_initialization(self, signal_engine):
        """Test signal engine initialization."""
        assert signal_engine is not None
        assert hasattr(signal_engine, "strategies")
        assert hasattr(signal_engine, "indicators")
        assert len(signal_engine.strategies) > 0

    def test_analyze_candles_with_sufficient_data(self, signal_engine, sample_candles):
        """Test analyzing candles with sufficient data."""
        signals = signal_engine.analyze_candles(sample_candles, "BTCUSDT", "5m")
        # We expect a list of signals (could be empty or populated)
        assert isinstance(signals, list)

    def test_analyze_candles_insufficient_data(self, signal_engine):
        """Test analyzing candles with insufficient data."""
        df = pd.DataFrame(
            {
                "open": [44.25, 44.00],
                "high": [44.50, 44.25],
                "low": [44.00, 43.75],
                "close": [44.34, 44.09],
                "volume": [1000, 1200],
            }
        )
        signals = signal_engine.analyze_candles(df, "BTCUSDT", "5m")
        # With insufficient data, we expect an empty list
        assert isinstance(signals, list)
        assert len(signals) == 0

    def test_indicators_calculation(self, signal_engine, sample_candles):
        """Test that indicators are calculated correctly."""
        indicators = signal_engine._calculate_indicators(sample_candles)

        # Check that we have the expected indicators
        expected_indicators = [
            "rsi",
            "macd",
            "macd_signal",
            "macd_hist",
            "adx",
            "atr",
            "vwap",
            "ema21",
            "ema50",
            "ema200",
            "bb_lower",
            "bb_middle",
            "bb_upper",
            "volume_sma",
            "wick_ratio",
        ]

        for indicator in expected_indicators:
            assert indicator in indicators
            # Each indicator should be a pandas Series or tuple of Series
            if isinstance(indicators[indicator], tuple):
                for series in indicators[indicator]:
                    assert isinstance(series, pd.Series)
            else:
                assert isinstance(indicators[indicator], pd.Series)

    def test_strategy_execution(self, signal_engine, sample_candles):
        """Test execution of a single strategy."""
        # Mock a simple strategy
        mock_strategy = MagicMock()
        mock_signal = Signal(
            strategy_id="test_strategy",
            symbol="BTCUSDT",
            action="buy",
            confidence=0.8,
            current_price=45.5,
            price=45.5,
            strength=SignalStrength.STRONG,
            timeframe="5m",
            stop_loss=45.0,
            take_profit=47.0,
        )
        mock_strategy.analyze.return_value = mock_signal

        # Create minimal indicators dict
        indicators = {
            "rsi": pd.Series([50.0]),
            "ema21": pd.Series([45.0]),
            "ema50": pd.Series([44.0]),
            "ema200": pd.Series([43.0]),
            "atr": pd.Series([1.0]),
        }

        signal = signal_engine._run_strategy(
            mock_strategy,
            "test_strategy",
            sample_candles,
            "BTCUSDT",
            "5m",
            indicators,
            45.5,
        )

        # Verify the signal was processed correctly
        assert signal is not None
        assert isinstance(signal, Signal)
        assert signal.symbol == "BTCUSDT"
        assert signal.timeframe == "5m"
        assert signal.action == "buy"


class TestSignalEngineConfigInjection:
    """Tests for #283: the "config" metadata key must always be injected,
    with a real, non-None resolved configuration, so
    BaseStrategy._get_config() stops always returning None."""

    @pytest.fixture
    def signal_engine(self):
        return SignalEngine()

    def _capture_metadata(self, signal_engine, mock_strategy, indicators, **kwargs):
        signal_engine._run_strategy(
            mock_strategy,
            "rsi_extreme_reversal",
            pd.DataFrame({"close": [1]}),
            "BTCUSDT",
            "5m",
            indicators,
            45.5,
            kwargs.get("strategy_configs"),
        )
        return mock_strategy.analyze.call_args[0][1]

    def test_config_key_always_present_in_metadata(self, signal_engine):
        """AC1: signal_engine.py:329 (now _run_strategy) must inject a
        "config" key on every call -- previously this key never existed."""
        mock_strategy = MagicMock()
        mock_strategy.analyze.return_value = None
        metadata = self._capture_metadata(signal_engine, mock_strategy, {})
        assert "config" in metadata
        assert metadata["config"] is not None

    def test_defaults_py_fallback_when_no_strategy_configs_manager_wired(
        self, signal_engine
    ):
        """AC2: with no live StrategyConfigManager wired (strategy_configs=None,
        the production-today state), resolution falls back to defaults.py --
        never raises, and the resolved value equals the known defaults.py
        constant for rsi_extreme_reversal."""
        mock_strategy = MagicMock()
        mock_strategy.analyze.return_value = None
        metadata = self._capture_metadata(
            signal_engine, mock_strategy, {}, strategy_configs=None
        )
        config = metadata["config"]
        assert config["source"] == "default"
        assert config["is_override"] is False
        assert config["parameters"]["base_confidence"] == 0.65
        assert config["parameters"]["oversold_threshold"] == 25

    def test_missing_strategy_configs_entry_falls_back_to_defaults_not_raise(
        self, signal_engine
    ):
        """AC2: a strategy_configs dict that simply omits this strategy (e.g.
        because its async resolution failed upstream) must not raise and
        must resolve identically to the "no manager wired" case."""
        mock_strategy = MagicMock()
        mock_strategy.analyze.return_value = None
        metadata = self._capture_metadata(
            signal_engine, mock_strategy, {}, strategy_configs={}
        )
        assert metadata["config"]["source"] == "default"
        assert metadata["config"]["parameters"]["base_confidence"] == 0.65

    def test_symbol_or_global_override_takes_priority_over_defaults(
        self, signal_engine
    ):
        """AC2: when an entry IS present in strategy_configs (i.e. resolved
        upstream via StrategyConfigManager.get_config(), which already
        implements symbol -> global -> defaults.py priority), it must win
        over defaults.py entirely."""
        mock_strategy = MagicMock()
        mock_strategy.analyze.return_value = None
        override = {
            "parameters": {"base_confidence": 0.91, "oversold_threshold": 10},
            "version": 3,
            "source": "mongodb",
            "is_override": True,
        }
        metadata = self._capture_metadata(
            signal_engine,
            mock_strategy,
            {},
            strategy_configs={"rsi_extreme_reversal": override},
        )
        assert metadata["config"] == override

    def test_unknown_strategy_id_resolves_to_empty_parameters_not_raise(
        self, signal_engine
    ):
        """A strategy_id absent from both strategy_configs and
        STRATEGY_DEFAULTS must resolve to an empty parameters dict rather
        than raising -- each strategy's own `else` branch then applies."""
        mock_strategy = MagicMock()
        mock_strategy.analyze.return_value = None
        signal_engine._run_strategy(
            mock_strategy,
            "totally_unknown_strategy_id",
            pd.DataFrame({"close": [1]}),
            "BTCUSDT",
            "5m",
            {},
            45.5,
            None,
        )
        metadata = mock_strategy.analyze.call_args[0][1]
        assert metadata["config"]["parameters"] == {}


class TestSignalModel:
    """Test cases for the signal model."""

    def test_signal_creation(self):
        """Test creating a signal."""
        signal = Signal(
            strategy_id="test_strategy",
            symbol="BTCUSDT",
            action="buy",
            confidence=0.8,
            current_price=45.5,
            price=45.5,
            strength=SignalStrength.STRONG,
            timeframe="5m",
            stop_loss=45.0,
            take_profit=47.0,
        )

        assert signal.symbol == "BTCUSDT"
        assert signal.timeframe == "5m"
        assert signal.action == "buy"
        assert signal.confidence == 0.8
        assert signal.strength == SignalStrength.STRONG
        assert signal.stop_loss == 45.0
        assert signal.take_profit == 47.0

    def test_signal_validation(self):
        """Test signal validation."""
        # Valid signal
        valid_signal = Signal(
            strategy_id="test_strategy",
            symbol="BTCUSDT",
            action="buy",
            confidence=0.8,
            current_price=45.5,
            price=45.5,
            strength=SignalStrength.STRONG,
            timeframe="5m",
            stop_loss=45.0,
            take_profit=47.0,
        )
        assert valid_signal.validate_signal() is True

        # Invalid signal - missing stop_loss (but this is now allowed)
        invalid_signal = Signal(
            strategy_id="test_strategy",
            symbol="BTCUSDT",
            action="buy",
            confidence=0.8,
            current_price=45.5,
            price=45.5,
            strength=SignalStrength.STRONG,
            timeframe="5m",
            stop_loss=None,
            take_profit=47.0,
        )
        # Validation should still pass as stop_loss is optional
        assert invalid_signal.validate_signal() is True

        # Invalid signal - negative confidence
        # Pydantic will raise error on instantiation for confidence < 0
        with pytest.raises(ValidationError):
            Signal(
                strategy_id="test_strategy",
                symbol="BTCUSDT",
                action="buy",
                confidence=-0.5,
                current_price=45.5,
                price=45.5,
            )

    def test_signal_to_dict(self):
        """Test converting signal to dictionary."""
        signal = Signal(
            strategy_id="test_strategy",
            symbol="BTCUSDT",
            action="buy",
            confidence=0.8,
            current_price=45.5,
            price=45.5,
            strength=SignalStrength.STRONG,
            timeframe="5m",
            stop_loss=45.0,
            take_profit=47.0,
        )

        signal_dict = signal.to_dict()
        assert isinstance(signal_dict, dict)
        assert signal_dict["symbol"] == "BTCUSDT"
        assert signal_dict["timeframe"] == "5m"
        assert signal_dict["action"] == "buy"
        assert signal_dict["confidence"] == 0.8
        assert signal_dict["strength"] == "strong"
        assert signal_dict["stop_loss"] == 45.0
        assert signal_dict["take_profit"] == 47.0


class TestConfidenceCalculator:
    """Test cases for the confidence calculator."""

    def test_momentum_pulse_confidence(self):
        """Test momentum pulse confidence calculation."""
        df = pd.DataFrame({"close": [45.5]})
        metadata = {"rsi": 55.0, "ema21": 46.0, "ema50": 45.5, "ema200": 45.0}

        # Since we're testing the signal engine's internal methods,
        # we'll test the confidence calculation indirectly through a strategy
        # For now, we'll verify the method exists and can be called
        engine = SignalEngine()
        assert hasattr(engine, "_calculate_signal_strength")

    def test_confidence_bounds(self):
        """Test that confidence is properly bounded between 0 and 1."""
        engine = SignalEngine()

        # Test various confidence values
        test_cases = [-0.5, 0.0, 0.5, 1.0, 1.5]
        for confidence in test_cases:
            # We'll test the private method directly
            if confidence >= 0.8:
                strength = engine._calculate_signal_strength(confidence)
                assert strength.value == "extreme"
            elif confidence >= 0.7:
                strength = engine._calculate_signal_strength(confidence)
                assert strength.value == "strong"
            elif confidence >= 0.6:
                strength = engine._calculate_signal_strength(confidence)
                assert strength.value == "medium"
            else:
                strength = engine._calculate_signal_strength(confidence)
                assert strength.value == "weak"


class TestSignalEngineTracing:
    """Test cases for OpenTelemetry tracing in signal engine."""

    @pytest.fixture
    def mock_tracer(self):
        """Create a mock tracer."""
        with patch("ta_bot.core.signal_engine.tracer") as mock:
            mock_span = MagicMock()
            mock.start_as_current_span.return_value.__enter__.return_value = mock_span
            yield mock, mock_span

    @pytest.fixture
    def sample_candles(self):
        """Create sample candle data."""
        return pd.DataFrame(
            {
                "open": [
                    44.25,
                    44.00,
                    44.10,
                    43.50,
                    44.25,
                    44.80,
                    45.20,
                    45.90,
                    45.90,
                    45.90,
                ],
                "high": [
                    44.50,
                    44.25,
                    44.30,
                    43.75,
                    44.50,
                    45.00,
                    45.50,
                    46.00,
                    46.25,
                    46.50,
                ],
                "low": [
                    44.00,
                    43.75,
                    43.80,
                    43.25,
                    43.75,
                    44.25,
                    44.75,
                    45.25,
                    45.50,
                    45.75,
                ],
                "close": [
                    44.34,
                    44.09,
                    44.15,
                    43.61,
                    44.33,
                    44.83,
                    45.18,
                    45.87,
                    45.87,
                    45.87,
                ],
                "volume": [1000, 1200, 800, 1500, 1100, 900, 1300, 1400, 1600, 1200],
            }
        )

    def test_analyze_candles_creates_span(self, mock_tracer, sample_candles):
        """Test that analyze_candles creates span with attributes."""
        mock_tracer_obj, mock_span = mock_tracer
        engine = SignalEngine()

        with mock_tracer_obj:
            engine.analyze_candles(sample_candles, "BTCUSDT", "5m")

        # Verify span was created
        mock_tracer_obj.start_as_current_span.assert_any_call("analyze_candles")

    def test_run_strategy_creates_span(self, mock_tracer, sample_candles):
        """Test that run_strategy creates span with attributes."""
        mock_tracer_obj, mock_span = mock_tracer
        engine = SignalEngine()

        # Mock a simple strategy
        mock_strategy = MagicMock()
        mock_strategy.analyze.return_value = None

        # Create minimal indicators dict
        indicators = {"rsi": pd.Series([50.0])}

        with mock_tracer_obj:
            engine._run_strategy(
                mock_strategy,
                "test_strategy",
                sample_candles,
                "BTCUSDT",
                "5m",
                indicators,
                45.5,
            )

        # Verify span was created
        mock_tracer_obj.start_as_current_span.assert_called_with("run_strategy")
