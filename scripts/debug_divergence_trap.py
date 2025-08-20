#!/usr/bin/env python3
"""
Debug script for Divergence Trap strategy.
"""

import logging
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, ".")

from ta_bot.core.indicators import Indicators  # noqa: E402

from ta_bot.strategies.divergence_trap import DivergenceTrapStrategy  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def generate_divergence_trap_data():
    """Generate data specifically designed for divergence trap."""
    dates = pd.date_range(
        start=datetime.now() - timedelta(hours=8), periods=100, freq="5min"
    )
    base_price = 50000.0

    prices = []
    for i in range(100):
        if i < 80:
            # Initial uptrend followed by decline
            if i < 40:
                price = base_price * (1.005**i)
            else:
                # Start declining
                decline_factor = 0.995 ** (i - 40)
                price = base_price * (1.005**40) * decline_factor
        elif i < 90:
            # Continue decline to create oversold RSI
            decline_factor = 0.99 ** (i - 80)
            price = base_price * (1.005**40) * (0.995**40) * decline_factor
        elif i < 95:
            # Create the pattern: recent_lows[-1] should be lower than recent_lows[-5]
            # This means the last low should be lower than the low 5 periods ago
            if i == 90:
                # First low in the pattern
                price = base_price * (1.005**40) * (0.995**40) * (0.99**10) * 0.98
            elif i == 91:
                # Slight bounce
                price = (
                    base_price
                    * (1.005**40)
                    * (0.995**40)
                    * (0.99**10)
                    * 0.98
                    * 1.002
                )
            elif i == 92:
                # Continue bounce
                price = (
                    base_price
                    * (1.005**40)
                    * (0.995**40)
                    * (0.99**10)
                    * 0.98
                    * 1.002
                    * 1.002
                )
            elif i == 93:
                # Continue bounce
                price = (
                    base_price
                    * (1.005**40)
                    * (0.995**40)
                    * (0.99**10)
                    * 0.98
                    * 1.002
                    * 1.002
                    * 1.002
                )
            elif i == 94:
                # Continue bounce
                price = (
                    base_price
                    * (1.005**40)
                    * (0.995**40)
                    * (0.99**10)
                    * 0.98
                    * 1.002
                    * 1.002
                    * 1.002
                    * 1.002
                )
        else:
            # Final phase: create a lower low than 5 periods ago
            if i == 95:
                # This should be lower than the low at i=90
                price = (
                    base_price
                    * (1.005**40)
                    * (0.995**40)
                    * (0.99**10)
                    * 0.98
                    * 0.97
                )
            elif i == 96:
                # Slight recovery
                price = (
                    base_price
                    * (1.005**40)
                    * (0.995**40)
                    * (0.99**10)
                    * 0.98
                    * 0.97
                    * 1.001
                )
            elif i == 97:
                # Continue recovery
                price = (
                    base_price
                    * (1.005**40)
                    * (0.995**40)
                    * (0.99**10)
                    * 0.98
                    * 0.97
                    * 1.001
                    * 1.001
                )
            elif i == 98:
                # Continue recovery
                price = (
                    base_price
                    * (1.005**40)
                    * (0.995**40)
                    * (0.99**10)
                    * 0.98
                    * 0.97
                    * 1.001
                    * 1.001
                    * 1.001
                )
            else:
                # Final recovery with momentum
                price = (
                    base_price
                    * (1.005**40)
                    * (0.995**40)
                    * (0.99**10)
                    * 0.98
                    * 0.97
                    * 1.001
                    * 1.001
                    * 1.001
                    * 1.001
                )
        prices.append(price)

    # Create DataFrame
    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        open_price = price * (1 + np.random.uniform(-0.002, 0.002))
        high_price = max(open_price, price) * (1 + np.random.uniform(0, 0.005))
        low_price = min(open_price, price) * (1 - np.random.uniform(0, 0.005))
        close_price = price
        volume = np.random.uniform(100, 1000)

        data.append(
            {
                "timestamp": date,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
            }
        )

    df = pd.DataFrame(data)
    df.set_index("timestamp", inplace=True)
    return df


def debug_divergence_trap():
    """Debug the divergence trap strategy."""
    logger.info("🔍 Debugging Divergence Trap Strategy")

    # Generate test data
    df = generate_divergence_trap_data()
    logger.info(f"Generated DataFrame with shape: {df.shape}")
    logger.info(f"Last 10 closes: {df['close'].iloc[-10:].tolist()}")

    # Calculate indicators
    indicators = Indicators()
    rsi = indicators.rsi(df)
    logger.info(f"Last 10 RSI values: {rsi.iloc[-10:].tolist()}")

    # Create metadata
    metadata = {
        "rsi": rsi,
        "close": df["close"],
        "symbol": "BTCUSDT",
        "timeframe": "5m",
    }

    # Test strategy
    strategy = DivergenceTrapStrategy()

    # Debug step by step
    logger.info("\n--- Step by step debugging ---")

    # Check data length
    logger.info(f"Data length: {len(df)} (need >= 30)")

    # Check required indicators
    current_values = strategy._get_current_values(metadata, df)
    logger.info(f"Current values keys: {list(current_values.keys())}")
    logger.info(f"Has RSI: {'rsi' in current_values}")
    logger.info(f"Has close: {'close' in current_values}")

    # Check RSI series
    rsi_series = metadata.get("rsi", [])
    logger.info(f"RSI series type: {type(rsi_series)}")
    logger.info(
        f"RSI series length: {len(rsi_series) if hasattr(rsi_series, '__len__') else 'N/A'}"
    )
    logger.info(
        f"RSI series empty: {rsi_series.empty if hasattr(rsi_series, 'empty') else 'N/A'}"
    )

    # Check divergence conditions
    if len(df) >= 10:
        recent_lows = df["low"].iloc[-10:].values
        logger.info(f"Recent lows: {recent_lows[-5:].tolist()}")

        if hasattr(rsi_series, "iloc"):
            recent_rsi_values = rsi_series.iloc[-10:].tolist()
        else:
            recent_rsi_values = rsi_series[-10:] if rsi_series else []

        logger.info(
            f"Recent RSI values: {recent_rsi_values[-5:] if len(recent_rsi_values) >= 5 else recent_rsi_values}"
        )

        if len(recent_rsi_values) >= 10:
            try:
                price_lower_low = recent_lows[-1] < recent_lows[-5]
                rsi_higher_low = current_values["rsi"] > recent_rsi_values[-5]

                logger.info(f"Price lower low: {price_lower_low}")
                logger.info(f"RSI higher low: {rsi_higher_low}")
                logger.info(
                    f"Hidden bullish divergence: {price_lower_low and rsi_higher_low}"
                )
            except (IndexError, ValueError) as e:
                logger.error(f"Error in divergence calculation: {e}")

    # Check oversold condition
    oversold = current_values["rsi"] < 30
    logger.info(f"RSI oversold (< 30): {oversold} (RSI = {current_values['rsi']:.2f})")

    # Check momentum
    if len(df) >= 3:
        prev_close = df.iloc[-2]["close"]
        momentum = current_values["close"] > prev_close
        logger.info(
            f"Price momentum: {momentum} (current: {current_values['close']:.2f}, prev: {prev_close:.2f})"
        )
    else:
        momentum = False
        logger.info("Not enough data for momentum check")

    # Run the strategy
    logger.info("\n--- Running strategy ---")
    signal = strategy.analyze(df, metadata)

    if signal:
        logger.info(
            f"✅ Signal generated: {signal.action} with confidence {signal.confidence}"
        )
        logger.info(f"Metadata: {signal.metadata}")
    else:
        logger.info("❌ No signal generated")

    return signal is not None


if __name__ == "__main__":
    success = debug_divergence_trap()
    sys.exit(0 if success else 1)
