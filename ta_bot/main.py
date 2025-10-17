#!/usr/bin/env python3
"""
Technical Analysis Bot for Crypto Trading
Main entry point for the TA bot microservice.
"""

import asyncio
import logging

# Import OpenTelemetry initialization early
import otel_init  # noqa: F401
from ta_bot.config import Config
from ta_bot.core.signal_engine import SignalEngine
from ta_bot.health import start_health_server
from ta_bot.services.nats_listener import NATSListener
from ta_bot.services.publisher import SignalPublisher

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point for the TA bot."""
    try:
        # Set up OpenTelemetry and attach OTLP logging handler for log export
        otel_init.setup_telemetry()
        otel_init.attach_logging_handler_simple()

        # Initialize components
        config = Config()
        signal_engine = SignalEngine()

        # Initialize publisher with both REST API and NATS capabilities
        publisher = SignalPublisher(
            api_endpoint=config.api_endpoint,
            nats_url=config.nats_url if config.nats_enabled else None,
            enable_rest_publishing=config.enable_rest_publishing,
        )

        # Parse supported symbols and timeframes
        supported_symbols = [s.strip() for s in config.symbols]
        supported_timeframes = [t.strip() for t in config.candle_periods]

        nats_listener = NATSListener(
            nats_url=config.nats_url,
            signal_engine=signal_engine,
            publisher=publisher,
            nats_subject_prefix=config.nats_subject_prefix,
            nats_subject_prefix_production=config.nats_subject_prefix_production,
            supported_symbols=supported_symbols,
            supported_timeframes=supported_timeframes,
        )

        logger.info("Starting TA Bot...")

        # Start health server in background
        health_server = await start_health_server(
            nats_url=config.nats_url,
            api_endpoint=config.api_endpoint,
            port=8000,
            publisher=publisher,
        )

        # Start the health server in a separate task
        health_task = asyncio.create_task(health_server.start())

        # Start listening for NATS messages if enabled
        if config.nats_enabled:
            logger.info("NATS is enabled, starting NATS listener...")
            # Start NATS listener in a separate task
            nats_task = asyncio.create_task(nats_listener.start())

            # CRITICAL: Wait briefly for publisher to initialize, then verify NATS connection
            await asyncio.sleep(2)  # Give publisher time to connect
            if publisher.nats_client is None:
                logger.error(
                    "CRITICAL: Publisher failed to connect to NATS at %s",
                    config.nats_url,
                )
                raise RuntimeError(
                    "Signal publishing will not work - NATS connection failed. "
                    "Check NATS_URL configuration and network connectivity."
                )
            logger.info("✅ Publisher NATS connection verified successfully")

            # Wait for both health server and NATS listener
            await asyncio.gather(health_task, nats_task)
        else:
            logger.info("NATS is disabled, skipping NATS listener startup")
            # Keep the application running for health checks
            await health_task

    except Exception as e:
        logger.error(f"Failed to start TA Bot: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
