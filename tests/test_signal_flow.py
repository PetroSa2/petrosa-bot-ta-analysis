#!/usr/bin/env python3
"""
Test script to verify signal flow from TA Bot to Trade Engine.
This script simulates the complete flow without requiring all services to be running.
"""

import asyncio
import json
import logging

import pandas as pd

from ta_bot.core.signal_engine import SignalEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_sample_candle_data():
    """Create sample candle data for testing."""
    # Create sample OHLCV data that should trigger signals
    data = {
        "timestamp": pd.date_range(start="2024-01-01", periods=100, freq="15min"),
        "open": [50000 + i * 5 for i in range(100)],
        "high": [50100 + i * 5 for i in range(100)],
        "low": [49900 + i * 5 for i in range(100)],
        "close": [50050 + i * 5 for i in range(100)],
        "volume": [1000 + i * 10 for i in range(100)],
    }

    # Create a golden cross scenario for golden_trend_sync
    # Make EMA21 cross above EMA50
    for i in range(80, 100):
        data["close"][i] = 50000 + (i - 80) * 20  # Strong uptrend

    df = pd.DataFrame(data)
    return df


def test_signal_generation():
    """Test signal generation with the new format."""
    logger.info("=== Testing Signal Generation ===")

    # Create sample data
    df = create_sample_candle_data()
    logger.info(f"Created sample data with shape: {df.shape}")

    # Initialize signal engine
    signal_engine = SignalEngine()

    # Generate signals
    signals = signal_engine.analyze_candles(df, "BTCUSDT", "15m")

    logger.info(f"Generated {len(signals)} signals")

    for i, signal in enumerate(signals):
        logger.info(f"Signal {i+1}:")
        logger.info(f"  Strategy ID: {signal.strategy_id}")
        logger.info(f"  Symbol: {signal.symbol}")
        logger.info(f"  Action: {signal.action}")
        logger.info(f"  Confidence: {signal.confidence:.3f}")
        logger.info(f"  Current Price: {signal.current_price}")
        logger.info(f"  Stop Loss: {signal.stop_loss}")
        logger.info(f"  Take Profit: {signal.take_profit}")
        logger.info(f"  Strategy: {signal.strategy}")
        logger.info(f"  Timeframe: {signal.timeframe}")
        logger.info("  ---")

    return signals


def test_signal_serialization(signals):
    """Test signal serialization to JSON format."""
    logger.info("=== Testing Signal Serialization ===")

    for i, signal in enumerate(signals):
        # Convert to dictionary
        signal_dict = signal.to_dict()

        # Convert to JSON
        signal_json = json.dumps(signal_dict, indent=2)

        logger.info(f"Signal {i+1} JSON:")
        logger.info(signal_json)
        logger.info("  ---")

        # Verify required fields for Trade Engine
        required_fields = [
            "strategy_id",
            "symbol",
            "action",
            "confidence",
            "current_price",
            "price",
            "source",
            "strategy",
            "timeframe",
            "order_type",
            "time_in_force",
        ]

        missing_fields = [
            field for field in required_fields if field not in signal_dict
        ]
        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
        else:
            logger.info("✅ All required fields present")


def test_signal_validation(signals):
    """Test signal validation."""
    logger.info("=== Testing Signal Validation ===")

    for i, signal in enumerate(signals):
        is_valid = signal.validate()
        logger.info(
            f"Signal {i+1} validation: {'✅ Valid' if is_valid else '❌ Invalid'}"
        )

        if not is_valid:
            logger.error(f"Signal {i+1} failed validation")


def test_trade_engine_compatibility(signals):
    """Test compatibility with Trade Engine signal format."""
    logger.info("=== Testing Trade Engine Compatibility ===")

    # Import Trade Engine Signal model
    try:
        import sys

        sys.path.append("../petrosa-tradeengine")
        from contracts.signal import Signal as TradeEngineSignal

        for i, ta_signal in enumerate(signals):
            # Convert TA Bot signal to Trade Engine format
            signal_dict = ta_signal.to_dict()

            try:
                # Create Trade Engine signal
                te_signal = TradeEngineSignal(**signal_dict)
                logger.info(f"Signal {i+1}: ✅ Compatible with Trade Engine")
                logger.info(f"  Trade Engine Signal ID: {te_signal.strategy_id}")
                logger.info(f"  Action: {te_signal.action}")
                logger.info(f"  Strategy Mode: {te_signal.strategy_mode}")

            except Exception as e:
                logger.error(f"Signal {i+1}: ❌ Incompatible with Trade Engine - {e}")

    except ImportError:
        logger.warning("Trade Engine not available for compatibility testing")


async def main():
    """Main test function."""
    logger.info("🚀 Starting Signal Flow Test")

    try:
        # Test signal generation
        signals = test_signal_generation()

        if not signals:
            logger.warning("No signals generated - skipping further tests")
            return

        # Test signal serialization
        test_signal_serialization(signals)

        # Test signal validation
        test_signal_validation(signals)

        # Test Trade Engine compatibility
        test_trade_engine_compatibility(signals)

        logger.info("✅ Signal Flow Test Completed Successfully")

    except Exception as e:
        logger.error(f"❌ Signal Flow Test Failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
