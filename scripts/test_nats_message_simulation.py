#!/usr/bin/env python3
"""
Test script to simulate NATS messages and verify signal generation.

This script simulates the exact NATS message format that the data extractor
sends and tests if the TA Bot can generate signals with perfect market conditions.
"""

import asyncio
import logging
import sys
from datetime import UTC, datetime, timezone
from typing import Any, Dict

# Add project root to path
sys.path.insert(0, ".")

from ta_bot.core.signal_engine import SignalEngine
from ta_bot.services.mysql_client import MySQLClient
from ta_bot.services.publisher import SignalPublisher

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NATSMessageSimulator:
    """Simulate NATS message processing for testing."""

    def __init__(self):
        """Initialize the simulator."""
        self.signal_engine = SignalEngine()
        self.mysql_client = MySQLClient()
        self.publisher = SignalPublisher(
            api_endpoint="http://localhost:8080/signals",  # Local test endpoint
            nats_url=None,  # No NATS for local testing
        )

    async def setup(self):
        """Setup connections."""
        try:
            await self.mysql_client.connect()
            await self.publisher.start()
            logger.info("✅ Setup completed successfully")
        except Exception as e:
            logger.error(f"❌ Setup failed: {e}")
            return False
        return True

    async def cleanup(self):
        """Cleanup connections."""
        try:
            await self.mysql_client.disconnect()
            await self.publisher.stop()
            logger.info("✅ Cleanup completed successfully")
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")

    def create_nats_message(self, symbol: str, period: str) -> dict[str, Any]:
        """Create a NATS message in the exact format sent by data extractor."""
        return {
            "event_type": "extraction_completed",
            "extraction_type": "klines",
            "symbol": symbol,
            "period": period,
            "timestamp": datetime.now(UTC).isoformat() + "Z",
            "success": True,
            "metrics": {
                "records_fetched": 7,
                "records_written": 1,
                "duration_seconds": 6.69,
                "gaps_found": 0,
                "gaps_filled": 0,
            },
            "errors": [],
        }

    async def process_nats_message(self, message: dict[str, Any]) -> bool:
        """Process a NATS message exactly like the TA Bot does."""
        try:
            # Extract message information
            symbol = message.get("symbol")
            period = message.get("period") or message.get("timeframe")

            if not symbol or not period:
                logger.warning(
                    f"Invalid message format - missing symbol or period: {message}"
                )
                return False

            logger.info(f"Processing extraction completion for {symbol} {period}")

            # Fetch candle data from MySQL
            df = await self.mysql_client.fetch_candles(symbol, period, limit=100)

            if df is None or len(df) == 0:
                logger.warning(f"No candle data available for {symbol} {period}")
                return False

            logger.info(f"Fetched {len(df)} candles for {symbol} {period}")

            # Analyze all strategies on the candle data
            signals = self.signal_engine.analyze_candles(df, symbol, period)

            if signals:
                logger.info(f"Generated {len(signals)} signals for {symbol} {period}")

                # Persist signals to MySQL
                signal_data_list = []
                for signal in signals:
                    signal_data = signal.to_dict()
                    signal_data_list.append(signal_data)

                success = await self.mysql_client.persist_signals_batch(
                    signal_data_list
                )
                if success:
                    logger.info(f"✅ Persisted {len(signals)} signals to MySQL")
                else:
                    logger.error("❌ Failed to persist signals to MySQL")

                # Publish signals
                await self.publisher.publish_signals(signals)
                logger.info(f"✅ Published {len(signals)} signals")

                return True
            else:
                logger.info(
                    f"No signals generated for {symbol} {period} - all strategies conditions not met"
                )
                return False

        except Exception as e:
            logger.error(f"Error processing NATS message: {e}")
            return False

    async def test_with_real_data(self):
        """Test with real market data from MySQL."""
        logger.info("🧪 Testing with real market data...")

        # Test with different symbols and timeframes
        test_cases = [
            ("BTCUSDT", "5m"),
            ("ETHUSDT", "5m"),
            ("ADAUSDT", "5m"),
            ("BTCUSDT", "15m"),
            ("ETHUSDT", "15m"),
        ]

        results = []
        for symbol, period in test_cases:
            logger.info(f"\n--- Testing {symbol} {period} ---")

            # Create NATS message
            message = self.create_nats_message(symbol, period)

            # Process the message
            success = await self.process_nats_message(message)
            results.append((symbol, period, success))

            # Small delay between tests
            await asyncio.sleep(1)

        # Summary
        logger.info("\n" + "=" * 50)
        logger.info("📊 TEST RESULTS SUMMARY")
        logger.info("=" * 50)

        successful_tests = sum(1 for _, _, success in results if success)
        total_tests = len(results)

        for symbol, period, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"{status} {symbol} {period}")

        logger.info(f"\nOverall: {successful_tests}/{total_tests} tests passed")

        if successful_tests > 0:
            logger.info("🎉 TA Bot is working correctly and generating signals!")
        else:
            logger.info(
                "⚠️  TA Bot is not generating signals - market conditions may not be suitable"
            )

        return successful_tests > 0


async def main():
    """Main test function."""
    logger.info("🚀 Starting NATS Message Simulation Test")

    simulator = NATSMessageSimulator()

    try:
        # Setup
        if not await simulator.setup():
            logger.error("❌ Failed to setup simulator")
            return False

        # Run tests
        success = await simulator.test_with_real_data()

        return success

    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False

    finally:
        # Cleanup
        await simulator.cleanup()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
