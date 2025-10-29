"""
Tests for the confidence calculator module.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ta_bot.core.confidence import ConfidenceCalculator


class TestConfidenceCalculator:
    """Test cases for the ConfidenceCalculator class."""

    @patch("ta_bot.core.confidence.tracer")
    def test_momentum_pulse_confidence_basic(self, mock_tracer):
        """Test momentum pulse confidence calculation."""
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
            mock_span
        )

        df = pd.DataFrame({"close": list(range(100, 150))})
        metadata = {
            "rsi": 55,
            "ema21": 110,
            "ema50": 105,
            "ema200": 100,
        }

        confidence = ConfidenceCalculator.momentum_pulse_confidence(df, metadata)

        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        # Should be 0.6 + 0.1 (RSI < 60) + 0.1 (EMA aligned) = 0.8
        assert confidence == pytest.approx(0.8)

    @patch("ta_bot.core.confidence.tracer")
    def test_momentum_pulse_confidence_low_rsi_only(self, mock_tracer):
        """Test momentum pulse confidence with only RSI condition met."""
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
            mock_span
        )

        df = pd.DataFrame({"close": list(range(100, 150))})
        metadata = {
            "rsi": 55,
            "ema21": 100,
            "ema50": 105,
            "ema200": 110,
        }

        confidence = ConfidenceCalculator.momentum_pulse_confidence(df, metadata)

        # Should be 0.6 + 0.1 (RSI < 60) = 0.7
        assert confidence == 0.7

    @patch("ta_bot.core.confidence.tracer")
    def test_calculate_confidence_with_known_strategy(self, mock_tracer):
        """Test calculate_confidence for known strategy."""
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
            mock_span
        )

        df = pd.DataFrame({"close": list(range(100, 150))})
        metadata = {"rsi": 55, "ema21": 110, "ema50": 105, "ema200": 100}

        confidence = ConfidenceCalculator.calculate_confidence(
            "momentum_pulse", df, metadata
        )

        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0

    @patch("ta_bot.core.confidence.tracer")
    def test_calculate_confidence_unknown_strategy_returns_default(self, mock_tracer):
        """Test calculate_confidence returns default for unknown strategy."""
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
            mock_span
        )

        df = pd.DataFrame({"close": list(range(100, 150))})
        metadata = {}

        confidence = ConfidenceCalculator.calculate_confidence(
            "unknown_strategy", df, metadata
        )

        # Should return default 0.5
        assert confidence == 0.5


class TestConfidenceTracing:
    """Test cases for OpenTelemetry tracing in ConfidenceCalculator."""

    @patch("ta_bot.core.confidence.tracer")
    def test_momentum_pulse_confidence_creates_span(self, mock_tracer):
        """Test that confidence calculation creates span with attributes."""
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
            mock_span
        )

        df = pd.DataFrame({"close": list(range(100, 150))})
        metadata = {
            "rsi": 55,
            "ema21": 110,
            "ema50": 105,
            "ema200": 100,
        }

        ConfidenceCalculator.momentum_pulse_confidence(df, metadata)

        # Verify span was created
        mock_tracer.start_as_current_span.assert_called_once_with(
            "calculate_momentum_pulse_confidence"
        )

        # Verify span attributes
        mock_span.set_attribute.assert_any_call("rsi", 55)
        mock_span.set_attribute.assert_any_call("ema21", 110)
        mock_span.set_attribute.assert_any_call("ema50", 105)
        mock_span.set_attribute.assert_any_call("ema200", 100)
        # Use ANY for confidence_score due to floating point precision
        calls = [call for call in mock_span.set_attribute.call_args_list]
        conf_calls = [call for call in calls if call[0][0] == "confidence_score"]
        assert len(conf_calls) > 0
        assert conf_calls[0][0][1] == pytest.approx(0.8)

    @patch("ta_bot.core.confidence.tracer")
    def test_calculate_confidence_creates_span(self, mock_tracer):
        """Test that calculate_confidence creates span with strategy name."""
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
            mock_span
        )

        df = pd.DataFrame({"close": list(range(100, 150))})
        metadata = {"rsi": 55}

        ConfidenceCalculator.calculate_confidence("momentum_pulse", df, metadata)

        # Verify outer span was created (calculate_confidence calls the specific method which creates another span)
        calls = [
            call[0][0] for call in mock_tracer.start_as_current_span.call_args_list
        ]
        assert "calculate_confidence" in calls

        # Verify strategy name attribute was set
        mock_span.set_attribute.assert_any_call("strategy_name", "momentum_pulse")

    @patch("ta_bot.core.confidence.tracer")
    def test_calculate_confidence_unknown_strategy_sets_default_flag(self, mock_tracer):
        """Test that unknown strategy sets used_default attribute."""
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = (
            mock_span
        )

        df = pd.DataFrame({"close": list(range(100, 150))})
        metadata = {}

        ConfidenceCalculator.calculate_confidence("unknown_strategy", df, metadata)

        # Verify default flag was set
        mock_span.set_attribute.assert_any_call("used_default", True)
        mock_span.set_attribute.assert_any_call("confidence_score", 0.5)


if __name__ == "__main__":
    pytest.main([__file__])
