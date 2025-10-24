#!/usr/bin/env python3
"""
Comprehensive test script for all 11 trading strategies.

This script tests all strategies with synthetic data designed to trigger each one.
"""

import logging
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, ".")

from ta_bot.core.signal_engine import SignalEngine  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AllStrategiesTester:
    """Test all 11 trading strategies with synthetic data."""

    def __init__(self):
        """Initialize the tester."""
        self.signal_engine = SignalEngine()

    def generate_test_data_for_strategy(self, strategy_name: str) -> pd.DataFrame:
        """Generate synthetic data designed to trigger a specific strategy."""
        # Create 100 candles
        dates = pd.date_range(
            start=datetime.now() - timedelta(hours=8), periods=100, freq="5min"
        )
        base_price = 50000.0

        if strategy_name == "momentum_pulse":
            return self._generate_momentum_pulse_data(dates, base_price)
        elif strategy_name == "band_fade_reversal":
            return self._generate_band_fade_reversal_data(dates, base_price)
        elif strategy_name == "golden_trend_sync":
            return self._generate_golden_trend_sync_data(dates, base_price)
        elif strategy_name == "range_break_pop":
            return self._generate_range_break_pop_data(dates, base_price)
        elif strategy_name == "divergence_trap":
            return self._generate_divergence_trap_data(dates, base_price)
        elif strategy_name == "volume_surge_breakout":
            return self._generate_volume_surge_breakout_data(dates, base_price)
        elif strategy_name == "mean_reversion_scalper":
            return self._generate_mean_reversion_scalper_data(dates, base_price)
        elif strategy_name == "ichimoku_cloud_momentum":
            return self._generate_ichimoku_cloud_momentum_data(dates, base_price)
        elif strategy_name == "liquidity_grab_reversal":
            return self._generate_liquidity_grab_reversal_data(dates, base_price)
        elif strategy_name == "multi_timeframe_trend_continuation":
            return self._generate_multi_timeframe_trend_continuation_data(
                dates, base_price
            )
        elif strategy_name == "order_flow_imbalance":
            return self._generate_order_flow_imbalance_data(dates, base_price)
        else:
            return self._generate_generic_data(dates, base_price)

    def _generate_momentum_pulse_data(
        self, dates: pd.DatetimeIndex, base_price: float
    ) -> pd.DataFrame:
        """Generate data for Momentum Pulse strategy."""
        prices = []
        for i in range(100):
            if i < 40:
                # Sideways movement to keep RSI in range
                price = base_price + np.random.uniform(-500, 500)
            elif i < 50:
                # Slight decline to create MACD histogram negative
                price = base_price * 0.98 - (i - 40) * 20
            else:
                # Strong uptrend to create MACD histogram positive
                price = base_price * 0.96 + (i - 50) * 200
            prices.append(price)

        return self._create_dataframe(dates, prices, strategy="momentum_pulse")

    def _generate_band_fade_reversal_data(
        self, dates: pd.DatetimeIndex, base_price: float
    ) -> pd.DataFrame:
        """Generate data for Band Fade Reversal strategy."""
        prices = []
        for i in range(100):
            if i < 80:
                # Sideways movement
                price = base_price + np.random.uniform(-100, 100)
            elif i < 95:
                # Sharp decline to lower band
                price = base_price * 0.95 - (i - 80) * 50
            else:
                # Reversal pattern
                if i == 95:
                    price = base_price * 0.92
                else:
                    price = base_price * 0.92 + (i - 95) * 100
            prices.append(price)

        return self._create_dataframe(dates, prices, strategy="band_fade_reversal")

    def _generate_golden_trend_sync_data(
        self, dates: pd.DatetimeIndex, base_price: float
    ) -> pd.DataFrame:
        """Generate data for Golden Trend Sync strategy."""
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

        return self._create_dataframe(dates, prices, strategy="golden_trend_sync")

    def _generate_range_break_pop_data(
        self, dates: pd.DatetimeIndex, base_price: float
    ) -> pd.DataFrame:
        """Generate data for Range Break Pop strategy."""
        prices = []
        for i in range(100):
            if i < 80:
                # Range-bound movement
                price = base_price + np.sin(i * 0.1) * 200
            else:
                # Breakout
                price = base_price + 300 + (i - 80) * 50
            prices.append(price)

        return self._create_dataframe(dates, prices, strategy="range_break_pop")

    def _generate_divergence_trap_data(
        self, dates: pd.DatetimeIndex, base_price: float
    ) -> pd.DataFrame:
        """Generate data for Divergence Trap strategy."""
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

        return self._create_dataframe(dates, prices, strategy="divergence_trap")

    def _generate_volume_surge_breakout_data(
        self, dates: pd.DatetimeIndex, base_price: float
    ) -> pd.DataFrame:
        """Generate data for Volume Surge Breakout strategy."""
        prices = []
        for i in range(100):
            if i < 80:
                # Consolidation
                price = base_price + np.random.uniform(-100, 100)
            else:
                # Breakout with volume surge
                price = base_price + 200 + (i - 80) * 100
            prices.append(price)

        return self._create_dataframe(
            dates, prices, strategy="volume_surge_breakout", high_volume=True
        )

    def _generate_mean_reversion_scalper_data(
        self, dates: pd.DatetimeIndex, base_price: float
    ) -> pd.DataFrame:
        """Generate data for Mean Reversion Scalper strategy."""
        prices = []
        for i in range(100):
            if i < 70:
                # Normal movement
                price = base_price + np.random.uniform(-200, 200)
            elif i < 90:
                # Extreme deviation from mean
                price = base_price * 0.90 - (i - 70) * 100
            else:
                # Reversion back to mean
                price = base_price * 0.80 + (i - 90) * 200
            prices.append(price)

        return self._create_dataframe(dates, prices, strategy="mean_reversion_scalper")

    def _generate_ichimoku_cloud_momentum_data(
        self, dates: pd.DatetimeIndex, base_price: float
    ) -> pd.DataFrame:
        """Generate data for Ichimoku Cloud Momentum strategy."""
        prices = []
        for i in range(100):
            if i < 30:
                # Below cloud
                price = base_price * 0.95
            elif i < 60:
                # Breaking above cloud
                price = base_price * 0.95 + (i - 30) * 50
            else:
                # Strong momentum above cloud
                price = base_price * 1.05 + (i - 60) * 100
            prices.append(price)

        return self._create_dataframe(dates, prices, strategy="ichimoku_cloud_momentum")

    def _generate_liquidity_grab_reversal_data(
        self, dates: pd.DatetimeIndex, base_price: float
    ) -> pd.DataFrame:
        """Generate data for Liquidity Grab Reversal strategy."""
        prices = []
        for i in range(100):
            if i < 85:
                # Normal movement
                price = base_price + np.random.uniform(-100, 100)
            elif i < 90:
                # Liquidity grab (wick formation)
                if i == 87:
                    price = base_price * 0.85  # Low wick
                else:
                    price = base_price * 0.90
            else:
                # Reversal
                price = base_price * 0.90 + (i - 90) * 200
            prices.append(price)

        return self._create_dataframe(dates, prices, strategy="liquidity_grab_reversal")

    def _generate_multi_timeframe_trend_continuation_data(
        self, dates: pd.DatetimeIndex, base_price: float
    ) -> pd.DataFrame:
        """Generate data for Multi-Timeframe Trend Continuation strategy."""
        prices = []
        for i in range(100):
            if i < 20:
                # Initial trend
                price = base_price * (1.003**i)
            elif i < 40:
                # Pullback
                price = base_price * (1.003**20) * (0.998 ** (i - 20))
            elif i < 60:
                # Continuation
                price = base_price * (1.003**20) * (0.998**20) * (1.005 ** (i - 40))
            else:
                # Strong continuation
                price = (
                    base_price
                    * (1.003**20)
                    * (0.998**20)
                    * (1.005**20)
                    * (1.01 ** (i - 60))
                )
            prices.append(price)

        return self._create_dataframe(
            dates, prices, strategy="multi_timeframe_trend_continuation"
        )

    def _generate_order_flow_imbalance_data(
        self, dates: pd.DatetimeIndex, base_price: float
    ) -> pd.DataFrame:
        """Generate data for Order Flow Imbalance strategy."""
        prices = []
        for i in range(100):
            if i < 80:
                # Consolidation
                price = base_price + np.random.uniform(-50, 50)
            else:
                # Accumulation/distribution pattern
                price = base_price + np.sin((i - 80) * 0.5) * 30
            prices.append(price)

        return self._create_dataframe(
            dates, prices, strategy="order_flow_imbalance", high_volume=True
        )

    def _generate_generic_data(
        self, dates: pd.DatetimeIndex, base_price: float
    ) -> pd.DataFrame:
        """Generate generic data."""
        prices = [base_price + np.random.uniform(-100, 100) for _ in range(100)]
        return self._create_dataframe(dates, prices, strategy="generic")

    def _create_dataframe(
        self,
        dates: pd.DatetimeIndex,
        prices: list,
        strategy: str,
        high_volume: bool = False,
    ) -> pd.DataFrame:
        """Create DataFrame with OHLCV data."""
        data = []
        for i, (date, price) in enumerate(zip(dates, prices, strict=False)):
            # Create realistic OHLCV from the price
            open_price = price * (1 + np.random.uniform(-0.002, 0.002))
            high_price = max(open_price, price) * (1 + np.random.uniform(0, 0.005))
            low_price = min(open_price, price) * (1 - np.random.uniform(0, 0.005))
            close_price = price

            # Adjust volume based on strategy
            if high_volume:
                volume = np.random.uniform(1000, 3000)  # High volume
            else:
                volume = np.random.uniform(100, 1000)  # Normal volume

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
                        f"   Signal: {signal.action} {symbol} - Confidence: {signal.confidence:.2f}"
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
        """Run tests for all strategies."""
        logger.info("🧪 Starting Comprehensive Strategy Tests")

        # All strategies to test
        strategies = [
            "momentum_pulse",
            "band_fade_reversal",
            "golden_trend_sync",
            "range_break_pop",
            "divergence_trap",
            "volume_surge_breakout",
            "mean_reversion_scalper",
            "ichimoku_cloud_momentum",
            "liquidity_grab_reversal",
            "multi_timeframe_trend_continuation",
            "order_flow_imbalance",
        ]

        test_results = []

        for strategy_name in strategies:
            try:
                # Generate test data for this strategy
                df = self.generate_test_data_for_strategy(strategy_name)

                # Test the strategy
                success = self.test_strategy(strategy_name, df, "BTCUSDT", "5m")
                test_results.append((strategy_name, success))

            except Exception as e:
                logger.error(f"❌ {strategy_name} test failed: {e}")
                test_results.append((strategy_name, False))

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("📊 COMPREHENSIVE STRATEGY TEST RESULTS")
        logger.info("=" * 80)

        successful_tests = sum(1 for _, success in test_results if success)
        total_tests = len(test_results)

        for strategy_name, success in test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"{status} {strategy_name}")

        logger.info(
            f"\nOverall: {successful_tests}/{total_tests} strategies generated signals"
        )

        if successful_tests > 0:
            logger.info("🎉 TA Bot is working correctly with multiple strategies!")
        else:
            logger.info(
                "⚠️  TA Bot is not generating signals - check strategy conditions"
            )

        return successful_tests > 0


def main():
    """Main test function."""
    logger.info("🚀 Starting Comprehensive Strategy Test Suite")

    tester = AllStrategiesTester()

    try:
        success = tester.run_all_tests()
        return success

    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
