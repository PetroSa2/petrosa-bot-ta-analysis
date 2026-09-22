"""
Unit tests for strategy risk metadata validation.
"""

import logging
import warnings

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


def test_corrupted_hourly_sweep_skips_affected_strategies_cleanly(caplog):
    """Regression coverage for the #316 production failure path."""
    closes = [200.0 - (index * 1.5) for index in range(130)]
    frame = pd.DataFrame(
        {
            "open": closes,
            "high": [close + 0.5 for close in closes],
            "low": [close - 0.5 for close in closes],
            "close": closes,
            "volume": [1000.0] * len(closes),
        }
    )
    frame.loc[frame.index[-1], "close"] = 0.0

    caplog.set_level(logging.ERROR)
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        signals = SignalEngine().analyze_candles(
            frame,
            "BTCUSDT",
            "1h",
            enabled_strategies=["ema_alignment_bearish", "rsi_extreme_reversal"],
        )

    assert signals == []
    assert not any(
        "float division by zero" in record.message
        or "risk parameters must be positive" in record.message
        for record in caplog.records
    )
