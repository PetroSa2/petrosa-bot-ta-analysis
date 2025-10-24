"""
NATS listener service for receiving candle data and processing signals.
"""

import asyncio
import json
import logging
from typing import Any

from nats.aio.client import Client as NATS

from ta_bot.core.signal_engine import SignalEngine
from ta_bot.services.app_config_manager import AppConfigManager
from ta_bot.services.leader_election import LeaderElection
from ta_bot.services.mysql_client import MySQLClient
from ta_bot.services.publisher import SignalPublisher

logger = logging.getLogger(__name__)


class NATSListener:
    """NATS message listener for candle data."""

    def __init__(
        self,
        nats_url: str,
        signal_engine: SignalEngine,
        publisher: SignalPublisher,
        nats_subject_prefix: str = "binance.extraction",
        nats_subject_prefix_production: str = "binance.extraction.production",
        supported_symbols: list[str] | None = None,
        supported_timeframes: list[str] | None = None,
        app_config_manager: AppConfigManager | None = None,
    ):
        """
        Initialize the NATS listener.

        Args:
            nats_url: NATS server URL
            signal_engine: SignalEngine instance for analyzing candles
            publisher: SignalPublisher for publishing signals
            nats_subject_prefix: NATS subject prefix
            nats_subject_prefix_production: NATS subject prefix for production
            supported_symbols: Default symbols (fallback if no runtime config)
            supported_timeframes: Default timeframes (fallback if no runtime config)
            app_config_manager: Optional AppConfigManager for runtime configuration
        """
        self.nats_url = nats_url
        self.signal_engine = signal_engine
        self.publisher = publisher
        self.nats_subject_prefix = nats_subject_prefix
        self.nats_subject_prefix_production = nats_subject_prefix_production
        self.supported_symbols = supported_symbols or ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
        self.supported_timeframes = supported_timeframes or ["15m", "1h"]
        self.app_config_manager = app_config_manager
        self.nc = NATS()
        self.subscriptions: list[Any] = []
        self.leader_election = None
        self.mysql_client = MySQLClient()

    async def start(self):
        """Start the NATS listener."""
        try:
            # Connect to NATS
            await self.nc.connect(self.nats_url)
            logger.info(f"Connected to NATS server: {self.nats_url}")

            # Initialize leader election
            self.leader_election = LeaderElection(self.nc)
            # Start leader election in background
            asyncio.create_task(self.leader_election.start_election())

            # Initialize MySQL client
            await self.mysql_client.connect()

            # Initialize publisher
            await self.publisher.start()

            # Subscribe to candle data subjects
            await self._subscribe_to_candle_data()

            logger.info("NATS listener started successfully")

        except Exception as e:
            logger.error(f"Error starting NATS listener: {e}")
            raise

    async def _subscribe_to_candle_data(self):
        """Subscribe to candle data subjects."""
        # Subscribe to both development and production subjects
        # Updated to match the actual subjects published by the data extractor
        subjects = [
            f"{self.nats_subject_prefix}.klines.*.*",  # binance.klines.*.*
            f"{self.nats_subject_prefix_production}.klines.*.*",  # binance.production.klines.*.*
        ]

        for subject in subjects:
            subscription = await self.nc.subscribe(
                subject,
                cb=self._handle_candle_message,
                queue="ta_bot_workers",  # Load balancing across instances
            )
            self.subscriptions.append(subscription)
            logger.info(f"Subscribed to NATS subject: {subject}")

    async def _handle_candle_message(self, msg):
        """Handle incoming candle message."""
        try:
            # Only process messages if this replica is the leader
            if not self.leader_election or not self.leader_election.is_current_leader():
                logger.debug("Skipping message processing - not the leader")
                return

            # Log every message received with subject and data length
            subject = msg.subject
            data_length = len(msg.data)
            logger.info(
                f"Received NATS message - Subject: {subject}, Data length: {data_length} bytes"
            )

            # Log the raw message data for debugging
            raw_data = msg.data.decode()
            logger.info(
                f"Raw message data: {raw_data[:200]}..."
                if len(raw_data) > 200
                else f"Raw message data: {raw_data}"
            )

            # Parse message data
            data = json.loads(raw_data)

            # Extract message information
            symbol = data.get("symbol")
            period = data.get("period") or data.get("timeframe")

            if not symbol or not period:
                logger.warning(
                    f"Invalid message format - missing symbol or period: {data}"
                )
                return

            # Load runtime configuration if available
            runtime_config = None
            if self.app_config_manager:
                try:
                    runtime_config = await self.app_config_manager.get_config()
                    logger.debug(
                        f"Loaded runtime config version {runtime_config.get('version', 0)}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to load runtime config, using defaults: {e}"
                    )

            # Determine symbols and timeframes from runtime config or defaults
            if runtime_config and runtime_config.get("symbols"):
                active_symbols = runtime_config["symbols"]
            else:
                active_symbols = self.supported_symbols

            if runtime_config and runtime_config.get("candle_periods"):
                active_timeframes = runtime_config["candle_periods"]
            else:
                active_timeframes = self.supported_timeframes

            # Check if symbol and timeframe are supported
            if symbol not in active_symbols:
                logger.debug(
                    f"Skipping unsupported symbol: {symbol} (active: {active_symbols})"
                )
                return

            if period not in active_timeframes:
                logger.debug(
                    f"Skipping unsupported timeframe: {period} (active: {active_timeframes})"
                )
                return

            logger.info(f"Processing extraction completion for {symbol} {period}")

            # Fetch candle data from MySQL
            df = await self.mysql_client.fetch_candles(symbol, period, limit=100)

            if df is None or len(df) == 0:
                logger.warning(f"No candle data available for {symbol} {period}")
                return

            logger.info(f"Fetched {len(df)} candles for {symbol} {period}")

            # Extract runtime configuration parameters
            enabled_strategies = None
            min_confidence = None
            max_confidence = None

            if runtime_config:
                enabled_strategies = runtime_config.get("enabled_strategies")
                min_confidence = runtime_config.get("min_confidence")
                max_confidence = runtime_config.get("max_confidence")

            # Analyze candles with runtime configuration
            signals = self.signal_engine.analyze_candles(
                df=df,
                symbol=symbol,
                period=period,
                enabled_strategies=enabled_strategies,
                min_confidence=min_confidence,
                max_confidence=max_confidence,
            )

            if signals:
                logger.info(f"Generated {len(signals)} signals for {symbol} {period}")

                # Persist signals to MySQL (using new format)
                signal_data_list = []
                for signal in signals:
                    signal_data = signal.to_dict()
                    signal_data_list.append(signal_data)

                success = await self.mysql_client.persist_signals_batch(
                    signal_data_list
                )

                if success:
                    logger.info(
                        f"Successfully persisted {len(signals)} signals to MySQL"
                    )
                else:
                    logger.error(
                        f"Failed to persist signals to MySQL for {symbol} {period}"
                    )

                # Publish signals to Trade Engine regardless of DB persistence outcome
                logger.info(
                    f"🚀 PUBLISHING {len(signals)} signals to Trade Engine via publisher"
                )
                await self.publisher.publish_signals(signals)
                logger.info(f"✅ Publisher call completed for {len(signals)} signals")

            else:
                logger.info(
                    f"No signals generated for {symbol} {period} - all strategies conditions not met"
                )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse NATS message: {e}")
            logger.error(f"Raw message: {msg.data.decode()}")
        except Exception as e:
            logger.error(f"Error processing candle message: {e}")
            logger.error(f"Subject: {msg.subject}, Data: {msg.data.decode()[:200]}...")

    async def _cleanup(self):
        """Clean up NATS connections and subscriptions."""
        try:
            # Stop publisher
            await self.publisher.stop()

            # Unsubscribe from all topics
            for subscription in self.subscriptions:
                await subscription.unsubscribe()

            # Close NATS connection
            await self.nc.close()

            # Close MySQL connection
            await self.mysql_client.disconnect()

            logger.info("NATS listener cleaned up")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def stop(self):
        """Stop the NATS listener."""
        await self._cleanup()
