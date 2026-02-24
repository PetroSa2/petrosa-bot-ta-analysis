"""
Tests for the confidence calculation module.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ta_bot.core.confidence import ConfidenceCalculator


class TestConfidenceCalculator:
    """Test cases for the confidence calculator."""

    def test_momentum_pulse_confidence_basic(self):
        """Test basic momentum pulse confidence calculation."""
        df = pd.DataFrame({"close": [50000]})
        metadata = {"rsi": 55.0, "ema21": 50025.0, "ema50": 49980.0, "ema200": 49500.0}

        confidence = ConfidenceCalculator.momentum_pulse_confidence(df, metadata)
        assert confidence == pytest.approx(0.8)  # Base 0.6 + RSI bonus 0.1 + EMA bonus 0.1

    def test_momentum_pulse_confidence_low_rsi_only(self):
        """Test momentum pulse confidence with low RSI only."""
        df = pd.DataFrame({"close": [50000]})
        metadata = {"rsi": 55.0, "ema21": 49000.0, "ema50": 49500.0, "ema200": 50000.0}

        confidence = ConfidenceCalculator.momentum_pulse_confidence(df, metadata)
        assert confidence == 0.7  # Base 0.6 + RSI bonus 0.1

    def test_band_fade_reversal_confidence_basic(self):
        """Test basic band fade reversal confidence calculation."""
        df = pd.DataFrame({"close": [50000]})
        metadata = {"rsi": 85.0, "wick_ratio": 2.0, "atr": 1.0}

        confidence = ConfidenceCalculator.band_fade_reversal_confidence(df, metadata)
        assert confidence == 0.75  # Base 0.55 + RSI bonus 0.1 + wick bonus 0.1

    def test_golden_trend_sync_confidence_basic(self):
        """Test basic golden trend sync confidence calculation."""
        df = pd.DataFrame({"close": [50000]})
        metadata = {"close": 50000.0, "vwap": 49500.0, "volume_rank": 1}

        confidence = ConfidenceCalculator.golden_trend_sync_confidence(df, metadata)
        assert confidence == 0.85  # Base 0.65 + price>vwap bonus 0.1 + volume bonus 0.1

    def test_range_break_pop_confidence_basic(self):
        """Test basic range break pop confidence calculation."""
        df = pd.DataFrame({"close": [50000]})
        metadata = {"volume_ratio": 2.5, "macd_trend": 0.5}

        confidence = ConfidenceCalculator.range_break_pop_confidence(df, metadata)
        assert confidence == pytest.approx(0.8)  # Base 0.6 + volume bonus 0.1 + MACD bonus 0.1

    def test_divergence_trap_confidence_basic(self):
        """Test basic divergence trap confidence calculation."""
        df = pd.DataFrame({"close": [50000]})
        metadata = {"trend_percent": 15.0, "lower_wick": 0.7}

        confidence = ConfidenceCalculator.divergence_trap_confidence(df, metadata)
        assert confidence == 0.8  # Base 0.6 + trend bonus 0.15 + wick bonus 0.05

    def test_calculate_confidence_with_known_strategy(self):
        """Test confidence calculation for a known strategy."""
        df = pd.DataFrame({"close": [50000]})
        metadata = {"rsi": 55.0, "ema21": 50025.0, "ema50": 49980.0, "ema200": 49500.0}

        confidence = ConfidenceCalculator.calculate_confidence(
            "momentum_pulse", df, metadata
        )
        assert confidence == pytest.approx(0.8)

    def test_calculate_confidence_unknown_strategy_returns_default(self):
        """Test confidence calculation for unknown strategy returns default."""
        df = pd.DataFrame({"close": [50000]})
        metadata = {"rsi": 55.0}

        confidence = ConfidenceCalculator.calculate_confidence(
            "unknown_strategy", df, metadata
        )
        assert confidence == 0.5  # Default confidence


class TestConfidenceTracing:
    """Test cases for OpenTelemetry tracing in confidence calculator."""

    @pytest.fixture
    def mock_tracer(self):
        """Create a mock tracer."""
        with patch("ta_bot.core.confidence.tracer") as mock:
            mock_span = MagicMock()
            mock.start_as_current_span.return_value.__enter__.return_value = mock_span
            yield mock, mock_span

    def test_momentum_pulse_confidence_creates_span(self, mock_tracer):
        """Test that momentum pulse confidence calculation creates span with attributes."""
        mock_tracer_obj, mock_span = mock_tracer

        df = pd.DataFrame({"close": [50000]})
        metadata = {"rsi": 55.0, "ema21": 50025.0, "ema50": 49980.0, "ema200": 49500.0}

        with mock_tracer_obj:
            confidence = ConfidenceCalculator.momentum_pulse_confidence(df, metadata)

        # Verify span was created
        mock_tracer_obj.start_as_current_span.assert_called_once_with(
            "calculate_momentum_pulse_confidence"
        )

        # Verify span attributes were set
        mock_span.set_attribute.assert_any_call("rsi", 55.0)
        mock_span.set_attribute.assert_any_call("ema21", 50025.0)
        mock_span.set_attribute.assert_any_call("ema50", 49980.0)
        mock_span.set_attribute.assert_any_call("ema200", 49500.0)
        mock_span.set_attribute.assert_any_call("confidence_score", pytest.approx(0.8))

    def test_calculate_confidence_creates_span(self, mock_tracer):
        """Test that calculate_confidence creates span with attributes."""
        mock_tracer_obj, mock_span = mock_tracer

        df = pd.DataFrame({"close": [50000]})
        metadata = {"rsi": 55.0, "ema21": 50025.0, "ema50": 49980.0, "ema200": 49500.0}

        with mock_tracer_obj:
            confidence = ConfidenceCalculator.calculate_confidence(
                "momentum_pulse", df, metadata
            )

        # Verify outer span was created
        mock_tracer_obj.start_as_current_span.assert_any_call(
            "calculate_confidence"
        )

        # Verify inner span was also created
        mock_tracer_obj.start_as_current_span.assert_any_call(
            "calculate_momentum_pulse_confidence"
        )

        # Verify span attributes were set
        mock_span.set_attribute.assert_any_call("strategy_name", "momentum_pulse")
        mock_span.set_attribute.assert_any_call("confidence_score", pytest.approx(0.8))

    def test_calculate_confidence_unknown_strategy_sets_default_flag(self, mock_tracer):
        """Test that calculate_confidence sets default flag for unknown strategy."""
        mock_tracer_obj, mock_span = mock_tracer

        df = pd.DataFrame({"close": [50000]})
        metadata = {"rsi": 55.0}

        with mock_tracer_obj:
            confidence = ConfidenceCalculator.calculate_confidence(
                "unknown_strategy", df, metadata
            )

        # Verify span attributes were set
        mock_span.set_attribute.assert_any_call("strategy_name", "unknown_strategy")
        mock_span.set_attribute.assert_any_call("used_default", True)
        mock_span.set_attribute.assert_any_call("confidence_score", 0.5)
