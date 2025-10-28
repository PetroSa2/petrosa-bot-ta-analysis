#!/usr/bin/env python3
"""
Technical Analysis Bot for Crypto Trading
Main entry point for the TA bot microservice.
"""

import asyncio
import logging

# Import OpenTelemetry initialization early
import otel_init  # noqa: F401
from ta_bot.api import config_routes
from ta_bot.config import Config
from ta_bot.core.signal_engine import SignalEngine
from ta_bot.db.mongodb_client import MongoDBClient
from ta_bot.health import start_health_server
from ta_bot.services.app_config_manager import AppConfigManager
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
        # 1. Setup OpenTelemetry FIRST (before any logging configuration)
        from petrosa_otel import attach_logging_handler, initialize_telemetry_standard

        initialize_telemetry_standard(
            service_name="ta-bot",
            service_type="fastapi",
            enable_fastapi=True,
            enable_mongodb=True,
            enable_mysql=True,
        )

        # 2. Setup logging (may call basicConfig)
        # Note: logging is already configured at module level

        # 3. Attach OTel logging handler LAST (after logging is configured)
        attach_logging_handler()

        # Initialize components
        config = Config()
        signal_engine = SignalEngine()

        # Initialize Data Manager client for configuration (preferred)
        from ta_bot.services.data_manager_config_client import DataManagerConfigClient

        data_manager_client = DataManagerConfigClient()
        await data_manager_client.connect()
        logger.info("Data Manager client initialized")

        # Initialize MongoDB client for fallback configuration persistence
        mongodb_client = MongoDBClient()
        await mongodb_client.connect()
        logger.info("MongoDB client initialized")

        # Initialize Application Configuration Manager
        app_config_manager = AppConfigManager(
            mongodb_client=mongodb_client,  # Fallback
            data_manager_client=data_manager_client,  # Preferred
            cache_ttl_seconds=60,  # 60 second cache TTL
        )
        await app_config_manager.start()
        logger.info("Application configuration manager initialized")

        # Register configuration manager with API routes
        config_routes.set_app_config_manager(app_config_manager)
        logger.info("Configuration manager registered with API routes")

        # Try to load runtime configuration, fallback to startup config
        runtime_config = await app_config_manager.get_config()
        if runtime_config.get("version", 0) > 0:
            logger.info(
                f"Loaded runtime configuration version {runtime_config['version']} from database"
            )
            # Use runtime config as defaults
            supported_symbols = runtime_config.get(
                "symbols", [s.strip() for s in config.symbols]
            )
            supported_timeframes = runtime_config.get(
                "candle_periods", [t.strip() for t in config.candle_periods]
            )
        else:
            logger.info("No runtime configuration found, using startup defaults")
            # Use startup config
            supported_symbols = [s.strip() for s in config.symbols]
            supported_timeframes = [t.strip() for t in config.candle_periods]

            # Optionally persist startup config as initial runtime config
            initial_config = {
                "enabled_strategies": config.enabled_strategies,
                "symbols": supported_symbols,
                "candle_periods": supported_timeframes,
                "min_confidence": config.min_confidence,
                "max_confidence": config.max_confidence,
                "max_positions": config.max_positions,
                "position_sizes": config.position_sizes,
            }
            success, _, errors = await app_config_manager.set_config(
                config=initial_config,
                changed_by="system_startup",
                reason="Initial configuration from environment variables",
            )
            if success:
                logger.info("Persisted startup configuration to database")
            else:
                logger.warning(f"Failed to persist startup configuration: {errors}")

        # Initialize publisher with both REST API and NATS capabilities
        publisher = SignalPublisher(
            api_endpoint=config.api_endpoint,
            nats_url=config.nats_url if config.nats_enabled else None,
            nats_signal_topic=config.nats_signal_topic,
            enable_rest_publishing=config.enable_rest_publishing,
        )

        nats_listener = NATSListener(
            nats_url=config.nats_url,
            signal_engine=signal_engine,
            publisher=publisher,
            nats_subject_prefix=config.nats_subject_prefix,
            nats_subject_prefix_production=config.nats_subject_prefix_production,
            supported_symbols=supported_symbols,
            supported_timeframes=supported_timeframes,
            app_config_manager=app_config_manager,  # Pass runtime config manager
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
