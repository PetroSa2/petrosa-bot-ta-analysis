#!/usr/bin/env python3
"""
Debug script for Momentum Pulse Strategy
"""

import logging
import os
import sys

import numpy as np
import pandas as pd

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ta_bot.core.indicators import Indicators  # noqa: E402

from ta_bot.strategies.momentum_pulse import MomentumPulseStrategy  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def generate_perfect_momentum_data():
    """Generate perfect data for momentum pulse strategy."""
    logger.info("Generating perfect momentum pulse data")

    # Create 100 candles with perfect momentum pulse conditions
    np.random.seed(42)

    # Base price trend
    base_price = 50000
    prices = []
    volumes = []

    for i in range(100):
        # Create an uptrend with some volatility
        trend = 1 + (i * 0.001)  # Gradual uptrend
        noise = np.random.normal(0, 0.005)  # Small noise
        price = base_price * trend * (1 + noise)
        prices.append(price)
        volumes.append(np.random.uniform(1000, 5000))

    # Create OHLCV data
    df = pd.DataFrame(
        {
            "open": prices,
            "high": [p * 1.01 for p in prices],
            "low": [p * 0.99 for p in prices],
            "close": prices,
            "volume": volumes,
        }
    )

    return df


def debug_momentum_pulse():
    """Debug the momentum pulse strategy step by step."""
    logger.info("=== Debugging Momentum Pulse Strategy ===")

    # Generate data
    df = generate_perfect_momentum_data()
    logger.info(f"Data shape: {df.shape}")

    # Calculate indicators
    indicators = Indicators()
    rsi = indicators.rsi(df)
    macd, macd_signal, macd_hist = indicators.macd(df)
    adx = indicators.adx(df)
    ema21 = indicators.ema(df, 21)
    ema50 = indicators.ema(df, 50)

    # Print current values
    logger.info(f"Current close: {df['close'].iloc[-1]:.2f}")
    logger.info(f"Current RSI: {rsi.iloc[-1]:.2f}")
    logger.info(f"Current MACD hist: {macd_hist.iloc[-1]:.6f}")
    logger.info(f"Previous MACD hist: {macd_hist.iloc[-2]:.6f}")
    logger.info(f"Current ADX: {adx.iloc[-1]:.2f}")
    logger.info(f"Current EMA21: {ema21.iloc[-1]:.2f}")
    logger.info(f"Current EMA50: {ema50.iloc[-1]:.2f}")

    # Check momentum pulse conditions manually
    logger.info("\n=== Checking Momentum Pulse Conditions ===")

    # 1. MACD Histogram crosses from negative to positive
    macd_hist_cross = macd_hist.iloc[-2] <= 0 and macd_hist.iloc[-1] > 0
    logger.info(
        f"1. MACD Hist cross: {macd_hist_cross} (prev: {macd_hist.iloc[-2]:.6f}, curr: {macd_hist.iloc[-1]:.6f})"
    )

    # 2. RSI between 50-65
    rsi_ok = 50 <= rsi.iloc[-1] <= 65
    logger.info(f"2. RSI in range: {rsi_ok} (RSI: {rsi.iloc[-1]:.2f})")

    # 3. ADX > 20
    adx_ok = adx.iloc[-1] > 20
    logger.info(f"3. ADX > 20: {adx_ok} (ADX: {adx.iloc[-1]:.2f})")

    # 4. Price above EMA21 and EMA50
    close = df["close"].iloc[-1]
    price_above_emas = close > ema21.iloc[-1] and close > ema50.iloc[-1]
    logger.info(
        f"4. Price above EMAs: {price_above_emas} (close: {close:.2f}, EMA21: {ema21.iloc[-1]:.2f}, EMA50: {ema50.iloc[-1]:.2f})"
    )

    # All conditions
    all_conditions = macd_hist_cross and rsi_ok and adx_ok and price_above_emas
    logger.info(f"\nAll conditions met: {all_conditions}")

    # Test strategy directly
    logger.info("\n=== Testing Strategy Directly ===")
    strategy = MomentumPulseStrategy()

    # Prepare metadata
    metadata = {
        "rsi": rsi,
        "macd": macd,
        "macd_signal": macd_signal,
        "macd_hist": macd_hist,
        "adx": adx,
        "ema21": ema21,
        "ema50": ema50,
        "symbol": "BTCUSDT",
        "timeframe": "15m",
    }

    signal = strategy.analyze(df, metadata)
    logger.info(f"Strategy returned signal: {signal is not None}")

    if signal:
        logger.info(
            f"Signal details: {signal.strategy_id} - {signal.action} - {signal.confidence}"
        )
    else:
        logger.info("No signal generated")


if __name__ == "__main__":
    debug_momentum_pulse()
