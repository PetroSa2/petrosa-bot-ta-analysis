#!/usr/bin/env python3
"""
NATS Flow Checker for Petrosa TA Bot
Checks NATS connectivity and data flow to identify why signals aren't being generated.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime

import nats.aio.client as nats

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ta_bot.config import Config  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NATSFlowChecker:
    """Check NATS connectivity and data flow."""

    def __init__(self):
        """Initialize the checker."""
        self.config = Config()
        self.nc = nats.Client()
        self.message_count = 0
        self.last_message_time = None

    async def connect_to_nats(self):
        """Connect to NATS server."""
        try:
            await self.nc.connect(self.config.nats_url)
            logger.info(f"✅ Connected to NATS server: {self.config.nats_url}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to NATS: {e}")
            return False

    async def subscribe_to_candle_data(self):
        """Subscribe to candle data subjects."""
        subjects = [
            f"{self.config.nats_subject_prefix}.klines.*.*",
            f"{self.config.nats_subject_prefix_production}.klines.*.*",
        ]

        for subject in subjects:
            try:
                await self.nc.subscribe(
                    subject, cb=self._handle_message, queue="flow_checker"
                )
                logger.info(f"✅ Subscribed to: {subject}")
            except Exception as e:
                logger.error(f"❌ Failed to subscribe to {subject}: {e}")

    async def _handle_message(self, msg):
        """Handle incoming NATS messages."""
        try:
            self.message_count += 1
            self.last_message_time = datetime.now()

            subject = msg.subject
            data_length = len(msg.data)

            logger.info(f"📨 Message #{self.message_count} received:")
            logger.info(f"   Subject: {subject}")
            logger.info(f"   Data length: {data_length} bytes")

            # Try to parse the message
            try:
                data = json.loads(msg.data.decode())
                logger.info(f"   Symbol: {data.get('symbol', 'N/A')}")
                logger.info(f"   Timeframe: {data.get('timeframe', 'N/A')}")
                logger.info(f"   Candles count: {len(data.get('candles', []))}")

                # Check if this is a supported symbol/timeframe
                if (
                    data.get("symbol") in self.config.symbols
                    and data.get("timeframe") in self.config.candle_periods
                ):
                    logger.info(
                        "   ✅ Supported symbol/timeframe - would trigger analysis"
                    )
                else:
                    logger.info("   ⚠️ Not a supported symbol/timeframe")

            except json.JSONDecodeError:
                logger.warning("   ⚠️ Failed to parse JSON data")
            except Exception as e:
                logger.warning(f"   ⚠️ Error parsing message: {e}")

        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")

    async def check_nats_status(self):
        """Check NATS server status."""
        try:
            # Get server info
            server_info = self.nc.server_info
            logger.info("✅ NATS Server Info:")
            logger.info(f"   Server ID: {server_info.server_id}")
            logger.info(f"   Version: {server_info.version}")
            logger.info(f"   Go Version: {server_info.go}")
            logger.info(f"   Host: {server_info.host}")
            logger.info(f"   Port: {server_info.port}")

            # Get connection stats
            stats = self.nc.stats
            logger.info("✅ Connection Stats:")
            logger.info(f"   In Messages: {stats.in_msgs}")
            logger.info(f"   Out Messages: {stats.out_msgs}")
            logger.info(f"   In Bytes: {stats.in_bytes}")
            logger.info(f"   Out Bytes: {stats.out_bytes}")

            return True
        except Exception as e:
            logger.error(f"❌ Failed to get NATS status: {e}")
            return False

    async def monitor_for_messages(self, duration_seconds: int = 60):
        """Monitor for messages for a specified duration."""
        logger.info(f"🔍 Monitoring for messages for {duration_seconds} seconds...")
        logger.info("Press Ctrl+C to stop early")

        start_time = datetime.now()

        try:
            while True:
                elapsed = (datetime.now() - start_time).total_seconds()

                if elapsed >= duration_seconds:
                    break

                # Print status every 10 seconds
                if int(elapsed) % 10 == 0 and elapsed > 0:
                    logger.info(
                        f"⏱️  Elapsed: {elapsed:.0f}s, Messages: {self.message_count}"
                    )

                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("🛑 Monitoring stopped by user")

        # Final summary
        total_time = (datetime.now() - start_time).total_seconds()
        logger.info("📊 Monitoring Summary:")
        logger.info(f"   Total time: {total_time:.1f} seconds")
        logger.info(f"   Messages received: {self.message_count}")
        logger.info(f"   Messages per second: {self.message_count / total_time:.2f}")

        if self.last_message_time:
            time_since_last = (datetime.now() - self.last_message_time).total_seconds()
            logger.info(f"   Time since last message: {time_since_last:.1f} seconds")

    async def check_environment(self):
        """Check environment configuration."""
        logger.info("🔧 Environment Configuration:")
        logger.info(f"   NATS_URL: {self.config.nats_url}")
        logger.info(f"   NATS_ENABLED: {self.config.nats_enabled}")
        logger.info(f"   NATS_SUBJECT_PREFIX: {self.config.nats_subject_prefix}")
        logger.info(
            f"   NATS_SUBJECT_PREFIX_PROD: {self.config.nats_subject_prefix_production}"
        )
        logger.info(f"   SUPPORTED_SYMBOLS: {self.config.symbols}")
        logger.info(f"   SUPPORTED_TIMEFRAMES: {self.config.candle_periods}")

        # Check if NATS is enabled
        if not self.config.nats_enabled:
            logger.warning("⚠️ NATS is disabled in configuration!")
            return False

        return True

    async def run_diagnostic(self):
        """Run complete NATS diagnostic."""
        logger.info("🚀 Starting NATS Flow Diagnostic")
        logger.info("=" * 50)

        # Step 1: Check environment
        env_ok = await self.check_environment()
        if not env_ok:
            logger.error("❌ Environment configuration issues detected")
            return

        # Step 2: Connect to NATS
        connected = await self.connect_to_nats()
        if not connected:
            logger.error("❌ Cannot connect to NATS - stopping diagnostic")
            return

        # Step 3: Check NATS status
        await self.check_nats_status()

        # Step 4: Subscribe to subjects
        await self.subscribe_to_candle_data()

        # Step 5: Monitor for messages
        await self.monitor_for_messages(60)  # Monitor for 60 seconds

        # Step 6: Analysis
        logger.info("=" * 50)
        logger.info("📋 DIAGNOSTIC ANALYSIS")
        logger.info("=" * 50)

        if self.message_count == 0:
            logger.error("❌ NO MESSAGES RECEIVED")
            logger.error("   Possible issues:")
            logger.error("   1. Data extractor is not running")
            logger.error("   2. Data extractor is not publishing to NATS")
            logger.error("   3. Wrong NATS subjects")
            logger.error("   4. NATS server issues")
        elif self.message_count < 10:
            logger.warning("⚠️ FEW MESSAGES RECEIVED")
            logger.warning("   Possible issues:")
            logger.warning("   1. Data extractor is running slowly")
            logger.warning("   2. Limited symbols/timeframes being processed")
        else:
            logger.info("✅ GOOD MESSAGE FLOW DETECTED")
            logger.info("   If TA Bot is not generating signals, the issue is likely:")
            logger.info("   1. Strategy conditions not being met")
            logger.info("   2. Signal engine issues")
            logger.info("   3. Publisher problems")

        # Cleanup
        await self.nc.close()


async def main():
    """Main entry point."""
    checker = NATSFlowChecker()
    await checker.run_diagnostic()


if __name__ == "__main__":
    asyncio.run(main())
