#!/usr/bin/env python3
"""
Test script to generate data that meets exact strategy conditions.

This script creates synthetic data specifically designed to trigger each strategy
by meeting their exact technical indicator conditions.
"""

import logging
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, ".")

from ta_bot.core.signal_engine import SignalEngine
from ta_bot.core.indicators import Indicators

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PerfectConditionsTester:
    """Test with data specifically designed to meet strategy conditions."""

    def __init__(self):
        """Initialize the tester."""
        self.signal_engine = SignalEngine()

    def generate_perfect_momentum_pulse_data(self) -> pd.DataFrame:
        """Generate data that meets ALL Momentum Pulse conditions exactly."""
        # Create 100 candles
        dates = pd.date_range(
            start=datetime.now() - timedelta(hours=8), periods=100, freq="5min"
        )

        # Start with a base price
        base_price = 50000.0

        # Generate price data that creates perfect momentum pulse conditions
        prices = []
        for i in range(100):
            if i < 40:
                # Sideways movement to keep RSI in range
                price = base_price + np.random.uniform(-500, 500)
            elif i < 50:
                # Slight decline to create MACD histogram negative
                price = base_price * 0.98 - (i - 40) * 20
            else:
                # Strong uptrend to create MACD histogram positive and keep price above EMAs
                price = base_price * 0.96 + (i - 50) * 200
            prices.append(price)

        # Create OHLCV data
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            # Create realistic OHLCV from the price
            open_price = price * (1 + np.random.uniform(-0.001, 0.001))
            high_price = max(open_price, price) * (1 + np.random.uniform(0, 0.002))
            low_price = min(open_price, price) * (1 - np.random.uniform(0, 0.002))
            close_price = price
            volume = np.random.uniform(
                500, 1500
            )  # Higher volume for trend confirmation

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

        # Force the last two candles to create perfect MACD histogram cross
        # Previous candle: negative MACD histogram
        df.loc[df.index[-2], "close"] = df.loc[df.index[-2], "close"] * 0.995
        # Current candle: positive MACD histogram
        df.loc[df.index[-1], "close"] = df.loc[df.index[-1], "close"] * 1.005

        return df

    def test_momentum_pulse_debug(self, df: pd.DataFrame):
        """Debug the Momentum Pulse strategy step by step."""
        logger.info("\n🔍 DEBUGGING MOMENTUM PULSE STRATEGY")
        logger.info("=" * 50)

        try:
            # Calculate indicators manually to see what we get
            indicators = Indicators()

            # Calculate MACD
            macd, macd_signal, macd_hist = indicators.macd(df)
            logger.info(f"MACD Histogram (last 3): {macd_hist.iloc[-3:].tolist()}")

            # Calculate RSI
            rsi = indicators.rsi(df)
            logger.info(f"RSI (last 3): {rsi.iloc[-3:].tolist()}")

            # Calculate ADX
            adx = indicators.adx(df)
            logger.info(f"ADX (last 3): {adx.iloc[-3:].tolist()}")

            # Calculate EMAs
            ema21 = indicators.ema(df, 21)
            ema50 = indicators.ema(df, 50)
            logger.info(f"EMA21 (last 3): {ema21.iloc[-3:].tolist()}")
            logger.info(f"EMA50 (last 3): {ema50.iloc[-3:].tolist()}")
            logger.info(f"Close (last 3): {df['close'].iloc[-3:].tolist()}")

            # Check conditions
            current_close = df["close"].iloc[-1]
            current_ema21 = ema21.iloc[-1]
            current_ema50 = ema50.iloc[-1]
            current_rsi = rsi.iloc[-1]
            current_adx = adx.iloc[-1]
            current_macd_hist = macd_hist.iloc[-1]
            prev_macd_hist = macd_hist.iloc[-2]

            logger.info("\n📊 CONDITION CHECK:")
            logger.info(
                f"MACD Histogram cross: {prev_macd_hist:.6f} -> {current_macd_hist:.6f} (should be negative to positive)"
            )
            logger.info(f"RSI range (50-65): {current_rsi:.2f} (should be 50-65)")
            logger.info(f"ADX > 20: {current_adx:.2f} (should be > 20)")
            logger.info(
                f"Price above EMA21: {current_close:.2f} > {current_ema21:.2f} = {current_close > current_ema21}"
            )
            logger.info(
                f"Price above EMA50: {current_close:.2f} > {current_ema50:.2f} = {current_close > current_ema50}"
            )

            # Check if conditions are met
            macd_cross = prev_macd_hist < 0 and current_macd_hist > 0
            rsi_ok = 50 <= current_rsi <= 65
            adx_ok = current_adx > 20
            price_above_emas = (
                current_close > current_ema21 and current_close > current_ema50
            )

            logger.info("\n✅ CONDITIONS MET:")
            logger.info(f"MACD cross: {macd_cross}")
            logger.info(f"RSI range: {rsi_ok}")
            logger.info(f"ADX > 20: {adx_ok}")
            logger.info(f"Price above EMAs: {price_above_emas}")

            all_conditions = macd_cross and rsi_ok and adx_ok and price_above_emas
            logger.info(f"ALL CONDITIONS: {all_conditions}")

        except Exception as e:
            logger.error(f"Error during debug: {e}")

    def test_strategy_with_debug(
        self, strategy_name: str, df: pd.DataFrame, symbol: str, period: str
    ) -> bool:
        """Test a strategy with detailed debugging."""
        logger.info(f"\n--- Testing {strategy_name} with {symbol} {period} ---")

        # Debug Momentum Pulse specifically
        if strategy_name == "Momentum Pulse":
            self.test_momentum_pulse_debug(df)

        try:
            # Analyze the data
            signals = self.signal_engine.analyze_candles(df, symbol, period)

            if signals:
                logger.info(f"✅ {strategy_name}: Generated {len(signals)} signals!")
                for signal in signals:
                    logger.info(
                        f"   Signal: {signal.action} {symbol} - Confidence: {signal.confidence}"
                    )
                    if signal.metadata:
                        logger.info(f"   Metadata: {signal.metadata}")
                return True
            else:
                logger.info(f"❌ {strategy_name}: No signals generated")
                return False

        except Exception as e:
            logger.error(f"❌ {strategy_name}: Error during analysis: {e}")
            return False

    def run_momentum_pulse_test(self):
        """Run detailed Momentum Pulse test."""
        logger.info("🧪 Testing Momentum Pulse with Perfect Conditions")

        # Generate perfect data
        df = self.generate_perfect_momentum_pulse_data()

        # Test the strategy
        success = self.test_strategy_with_debug("Momentum Pulse", df, "BTCUSDT", "5m")

        if success:
            logger.info("🎉 Momentum Pulse strategy is working correctly!")
        else:
            logger.info("⚠️  Momentum Pulse strategy conditions are too strict")

        return success


def main():
    """Main test function."""
    logger.info("🚀 Starting Perfect Conditions Test")

    tester = PerfectConditionsTester()

    try:
        success = tester.run_momentum_pulse_test()
        return success

    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
