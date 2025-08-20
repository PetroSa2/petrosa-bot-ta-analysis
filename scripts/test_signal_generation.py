#!/usr/bin/env python3
"""
Test script to verify signal generation with synthetic data.

This script tests if the TA Bot can generate signals with perfect market conditions
without requiring external dependencies like MySQL or NATS.
"""

import logging
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, ".")

from ta_bot.core.signal_engine import SignalEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SignalGenerationTester:
    """Test signal generation with synthetic data."""

    def __init__(self):
        """Initialize the tester."""
        self.signal_engine = SignalEngine()

    def generate_perfect_momentum_pulse_data(
        self, symbol: str = "BTCUSDT"
    ) -> pd.DataFrame:
        """Generate synthetic data that should trigger Momentum Pulse strategy."""
        # Create 100 candles with perfect conditions for momentum pulse
        dates = pd.date_range(
            start=datetime.now() - timedelta(hours=8), periods=100, freq="5min"
        )

        # Start with a base price
        base_price = 50000.0

        # Generate price data that creates perfect momentum pulse conditions
        prices = []
        for i in range(100):
            if i < 50:
                # Declining trend
                price = base_price * (0.99 ** (50 - i))
            else:
                # Strong uptrend with momentum
                price = base_price * (1.01 ** (i - 50))
            prices.append(price)

        # Create OHLCV data
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            # Create realistic OHLCV from the price
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

        # Ensure the last few candles create perfect momentum pulse conditions
        # Force MACD histogram to cross from negative to positive
        df.loc[df.index[-2], "close"] = (
            df.loc[df.index[-2], "close"] * 0.995
        )  # Lower previous close
        df.loc[df.index[-1], "close"] = (
            df.loc[df.index[-1], "close"] * 1.005
        )  # Higher current close

        return df

    def generate_perfect_band_fade_reversal_data(
        self, symbol: str = "BTCUSDT"
    ) -> pd.DataFrame:
        """Generate synthetic data that should trigger Band Fade Reversal strategy."""
        # Create 100 candles with perfect conditions for band fade reversal
        dates = pd.date_range(
            start=datetime.now() - timedelta(hours=8), periods=100, freq="5min"
        )

        # Start with a base price
        base_price = 50000.0

        # Generate price data that creates perfect band fade reversal conditions
        prices = []
        for i in range(100):
            if i < 80:
                # Sideways movement
                price = base_price + np.random.uniform(-100, 100)
            elif i < 95:
                # Sharp decline to lower band
                price = base_price * 0.95 - (i - 80) * 50
            else:
                # Reversal pattern - price was declining but now moving up
                if i == 95:
                    price = base_price * 0.92  # Bottom
                else:
                    price = base_price * 0.92 + (i - 95) * 100  # Reversal up
            prices.append(price)

        # Create OHLCV data
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            open_price = price * (1 + np.random.uniform(-0.001, 0.001))
            high_price = max(open_price, price) * (1 + np.random.uniform(0, 0.003))
            low_price = min(open_price, price) * (1 - np.random.uniform(0, 0.003))
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

    def generate_perfect_golden_trend_sync_data(
        self, symbol: str = "BTCUSDT"
    ) -> pd.DataFrame:
        """Generate synthetic data that should trigger Golden Trend Sync strategy."""
        # Create 100 candles with perfect conditions for golden trend sync
        dates = pd.date_range(
            start=datetime.now() - timedelta(hours=8), periods=100, freq="5min"
        )

        # Start with a base price
        base_price = 50000.0

        # Generate price data that creates perfect golden trend sync conditions
        prices = []
        for i in range(100):
            if i < 30:
                # Initial uptrend
                price = base_price * (1.005**i)
            elif i < 60:
                # Consolidation
                price = base_price * (1.005**30) + np.random.uniform(-200, 200)
            else:
                # Strong uptrend with golden cross conditions
                price = base_price * (1.005**30) * (1.01 ** (i - 60))
            prices.append(price)

        # Create OHLCV data
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            open_price = price * (1 + np.random.uniform(-0.001, 0.001))
            high_price = max(open_price, price) * (1 + np.random.uniform(0, 0.003))
            low_price = min(open_price, price) * (1 - np.random.uniform(0, 0.003))
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

    def test_strategy(
        self, strategy_name: str, df: pd.DataFrame, symbol: str, period: str
    ) -> bool:
        """Test a specific strategy with the given data."""
        logger.info(f"\n--- Testing {strategy_name} with {symbol} {period} ---")

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

    def run_all_tests(self):
        """Run all strategy tests."""
        logger.info("🧪 Starting Signal Generation Tests")

        test_results = []

        # Test 1: Momentum Pulse Strategy
        try:
            df = self.generate_perfect_momentum_pulse_data("BTCUSDT")
            success = self.test_strategy("Momentum Pulse", df, "BTCUSDT", "5m")
            test_results.append(("Momentum Pulse", success))
        except Exception as e:
            logger.error(f"❌ Momentum Pulse test failed: {e}")
            test_results.append(("Momentum Pulse", False))

        # Test 2: Band Fade Reversal Strategy
        try:
            df = self.generate_perfect_band_fade_reversal_data("ETHUSDT")
            success = self.test_strategy("Band Fade Reversal", df, "ETHUSDT", "5m")
            test_results.append(("Band Fade Reversal", success))
        except Exception as e:
            logger.error(f"❌ Band Fade Reversal test failed: {e}")
            test_results.append(("Band Fade Reversal", False))

        # Test 3: Golden Trend Sync Strategy
        try:
            df = self.generate_perfect_golden_trend_sync_data("ADAUSDT")
            success = self.test_strategy("Golden Trend Sync", df, "ADAUSDT", "5m")
            test_results.append(("Golden Trend Sync", success))
        except Exception as e:
            logger.error(f"❌ Golden Trend Sync test failed: {e}")
            test_results.append(("Golden Trend Sync", False))

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("📊 SIGNAL GENERATION TEST RESULTS")
        logger.info("=" * 60)

        successful_tests = sum(1 for _, success in test_results if success)
        total_tests = len(test_results)

        for strategy_name, success in test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"{status} {strategy_name}")

        logger.info(
            f"\nOverall: {successful_tests}/{total_tests} strategies generated signals"
        )

        if successful_tests > 0:
            logger.info("🎉 TA Bot signal generation is working correctly!")
        else:
            logger.info(
                "⚠️  TA Bot is not generating signals - check strategy conditions"
            )

        return successful_tests > 0


def main():
    """Main test function."""
    logger.info("🚀 Starting Signal Generation Test")

    tester = SignalGenerationTester()

    try:
        success = tester.run_all_tests()
        return success

    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
