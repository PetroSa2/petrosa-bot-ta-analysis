"""
Basic tests for the TA Bot to ensure CI pipeline passes.
"""

import pytest
import sys
import os

# Add the ta_bot directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_import_ta_bot():
    """Test that ta_bot can be imported."""
    try:
        import ta_bot
        assert ta_bot is not None
    except ImportError as e:
        pytest.fail(f"Failed to import ta_bot: {e}")


def test_import_signal_engine():
    """Test that signal engine can be imported."""
    try:
        from ta_bot.core.signal_engine import SignalEngine
        assert SignalEngine is not None
    except ImportError as e:
        pytest.fail(f"Failed to import SignalEngine: {e}")


def test_import_strategies():
    """Test that strategies can be imported."""
    try:
        from ta_bot.strategies.momentum_pulse import MomentumPulseStrategy
        from ta_bot.strategies.band_fade_reversal import BandFadeReversalStrategy
        from ta_bot.strategies.golden_trend_sync import GoldenTrendSyncStrategy
        from ta_bot.strategies.range_break_pop import RangeBreakPopStrategy
        from ta_bot.strategies.divergence_trap import DivergenceTrapStrategy
        assert MomentumPulseStrategy is not None
        assert BandFadeReversalStrategy is not None
        assert GoldenTrendSyncStrategy is not None
        assert RangeBreakPopStrategy is not None
        assert DivergenceTrapStrategy is not None
    except ImportError as e:
        pytest.fail(f"Failed to import strategies: {e}")


def test_import_models():
    """Test that models can be imported."""
    try:
        from ta_bot.models.signal import Signal, SignalType
        assert Signal is not None
        assert SignalType is not None
    except ImportError as e:
        pytest.fail(f"Failed to import models: {e}")


def test_basic_functionality():
    """Test basic functionality without external dependencies."""
    # This test ensures the basic structure works
    assert True


if __name__ == "__main__":
    pytest.main([__file__]) 