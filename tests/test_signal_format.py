#!/usr/bin/env python3
"""
Simple test to verify signal format works correctly.
"""

import json
import logging

from ta_bot.models.signal import Signal

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_signal_creation():
    """Test creating a signal with the new format."""
    logger.info("=== Testing Signal Creation ===")

    # Create a sample signal
    signal = Signal(
        strategy_id="test_strategy_15m",
        symbol="BTCUSDT",
        action="buy",
        confidence=0.75,
        current_price=50000.0,
        price=50000.0,
        source="ta_bot",
        strategy="test_strategy",
        timeframe="15m",
        position_size_pct=0.1,
        stop_loss=49000.0,
        take_profit=51000.0,
        metadata={"rsi": 65.5, "macd_hist": 0.0012, "adx": 27.3},
    )

    logger.info(f"Created signal: {signal.strategy_id}")
    logger.info(f"Action: {signal.action}")
    logger.info(f"Confidence: {signal.confidence}")
    logger.info(f"Current Price: {signal.current_price}")
    logger.info(f"Stop Loss: {signal.stop_loss}")
    logger.info(f"Take Profit: {signal.take_profit}")

    return signal


def test_signal_serialization(signal):
    """Test signal serialization to JSON format."""
    logger.info("=== Testing Signal Serialization ===")

    # Convert to dictionary
    signal_dict = signal.to_dict()

    # Convert to JSON
    signal_json = json.dumps(signal_dict, indent=2)

    logger.info("Signal JSON:")
    logger.info(signal_json)

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

    missing_fields = [field for field in required_fields if field not in signal_dict]
    if missing_fields:
        logger.error(f"Missing required fields: {missing_fields}")
        return False
    else:
        logger.info("✅ All required fields present")
        return True


def test_signal_validation(signal):
    """Test signal validation."""
    logger.info("=== Testing Signal Validation ===")

    is_valid = signal.validate()
    logger.info(f"Signal validation: {'✅ Valid' if is_valid else '❌ Invalid'}")

    return is_valid


def test_trade_engine_compatibility(signal):
    """Test compatibility with Trade Engine signal format."""
    logger.info("=== Testing Trade Engine Compatibility ===")

    # Import Trade Engine Signal model
    try:
        import sys

        sys.path.append("../petrosa-tradeengine")
        from contracts.signal import Signal as TradeEngineSignal

        # Convert TA Bot signal to Trade Engine format
        signal_dict = signal.to_dict()

        try:
            # Create Trade Engine signal
            te_signal = TradeEngineSignal(**signal_dict)
            logger.info("✅ Compatible with Trade Engine")
            logger.info(f"  Trade Engine Signal ID: {te_signal.strategy_id}")
            logger.info(f"  Action: {te_signal.action}")
            logger.info(f"  Strategy Mode: {te_signal.strategy_mode}")
            return True

        except Exception as e:
            logger.error(f"❌ Incompatible with Trade Engine - {e}")
            return False

    except ImportError:
        logger.warning("Trade Engine not available for compatibility testing")
        return True


def main():
    """Main test function."""
    logger.info("🚀 Starting Signal Format Test")

    try:
        # Test signal creation
        signal = test_signal_creation()

        # Test signal serialization
        serialization_ok = test_signal_serialization(signal)

        # Test signal validation
        validation_ok = test_signal_validation(signal)

        # Test Trade Engine compatibility
        compatibility_ok = test_trade_engine_compatibility(signal)

        if serialization_ok and validation_ok and compatibility_ok:
            logger.info("✅ Signal Format Test Completed Successfully")
        else:
            logger.error("❌ Signal Format Test Failed")

    except Exception as e:
        logger.error(f"❌ Signal Format Test Failed: {e}")
        raise


if __name__ == "__main__":
    main()
