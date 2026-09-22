"""
Unit tests for strategy risk metadata validation.
"""

import pandas as pd
import pytest
from pydantic import ValidationError

from ta_bot.core.signal_engine import SignalEngine
from ta_bot.models.signal import Signal, SignalType


def test_signal_validation_strict_risk():
    """Test Signal.validate_signal(strict_risk=True) method."""
    # Valid BUY signal with SL/TP
    signal = Signal(
        strategy_id="test",
        symbol="BTCUSDT",
        action="buy",
        confidence=0.8,
        current_price=50000.0,
        price=50000.0,
        stop_loss=49000.0,
        take_profit=51000.0,
    )
    assert signal.validate_signal(strict_risk=True) is True

    # Invalid BUY signal without SL/TP
    signal = Signal(
        strategy_id="test",
        symbol="BTCUSDT",
        action="buy",
        confidence=0.8,
        current_price=50000.0,
        price=50000.0,
    )
    assert signal.validate_signal(strict_risk=True) is False

    # Invalid BUY signal with NaN SL
    import math

    signal = Signal(
        strategy_id="test",
        symbol="BTCUSDT",
        action="buy",
        confidence=0.8,
        current_price=50000.0,
        price=50000.0,
        stop_loss=float("nan"),
        take_profit=51000.0,
    )
    assert signal.validate_signal(strict_risk=True) is False

    # HOLD signal doesn't need SL/TP even in strict mode
    signal = Signal(
        strategy_id="test",
        symbol="BTCUSDT",
        action="hold",
        confidence=0.8,
        current_price=50000.0,
        price=50000.0,
    )
    assert signal.validate_signal(strict_risk=True) is True


def test_signal_engine_validation():
    """Test SignalEngine.validate_risk_parameters method."""
    engine = SignalEngine()

    # Valid BUY signal
    signal = Signal(
        strategy_id="test",
        symbol="BTCUSDT",
        action="buy",
        confidence=0.8,
        current_price=50000.0,
        price=50000.0,
        stop_loss=49000.0,
        take_profit=51000.0,
    )
    assert engine.validate_risk_parameters(signal) is True

    # Invalid BUY signal (missing parameters)
    signal = Signal(
        strategy_id="test",
        symbol="BTCUSDT",
        action="buy",
        confidence=0.8,
        current_price=50000.0,
        price=50000.0,
    )
    assert engine.validate_risk_parameters(signal) is False


def test_signal_engine_risk_calculation_rejects_invalid_price_and_atr():
    engine = SignalEngine()

    assert engine._calculate_risk_management(0.0, {}, SignalType.BUY) == (None, None)
    stop_loss, take_profit = engine._calculate_risk_management(
        100.0, {"atr": pd.Series([float("nan")])}, SignalType.BUY
    )
    assert stop_loss == 98.0
    assert take_profit == 105.0

    stop_loss, take_profit = engine._calculate_risk_management(
        100.0, {"atr": float("inf")}, SignalType.SELL
    )
    assert stop_loss == 102.0
    assert take_profit == 95.0

    signal = Signal(
        strategy_id="test",
        symbol="BTCUSDT",
        action="buy",
        confidence=0.8,
        current_price=50000.0,
        price=50000.0,
        stop_loss=float("nan"),
        take_profit=51000.0,
    )
    assert engine.validate_risk_parameters(signal) is False

    signal = Signal(
        strategy_id="test",
        symbol="BTCUSDT",
        action="buy",
        confidence=0.8,
        current_price=50000.0,
        price=50000.0,
        stop_loss=49000.0,
        take_profit=float("inf"),
    )
    assert engine.validate_risk_parameters(signal) is False

    # Invalid SELL signal (negative parameters)
    signal = Signal(
        strategy_id="test",
        symbol="BTCUSDT",
        action="sell",
        confidence=0.8,
        current_price=50000.0,
        price=50000.0,
        stop_loss=-100.0,
        take_profit=51000.0,
    )
    assert engine.validate_risk_parameters(signal) is False
