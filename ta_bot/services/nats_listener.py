"""
NATS listener service for receiving candle data and processing signals.
"""

import json
import logging
from typing import Dict, Any, List
import pandas as pd
from nats.aio.client import Client as NATS
from nats.aio.subscription import Subscription
import asyncio

from ta_bot.core.signal_engine import SignalEngine
from ta_bot.services.publisher import SignalPublisher
from ta_bot.services.leader_election import LeaderElection

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
        supported_symbols: List[str] = None,
        supported_timeframes: List[str] = None
    ):
        """Initialize the NATS listener."""
        self.nats_url = nats_url
        self.signal_engine = signal_engine
        self.publisher = publisher
        self.nats_subject_prefix = nats_subject_prefix
        self.nats_subject_prefix_production = nats_subject_prefix_production
        self.supported_symbols = supported_symbols or ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
        self.supported_timeframes = supported_timeframes or ["15m", "1h"]
        self.nc = NATS()
        self.subscriptions: List[Any] = []
        self.leader_election = None

    async def start(self):
        """Start the NATS listener."""
        try:
            # Connect to NATS
            await self.nc.connect(self.nats_url)
            logger.info(f"Connected to NATS at {self.nats_url}")

            # Initialize leader election
            self.leader_election = LeaderElection(self.nc)
            asyncio.create_task(self.leader_election.start_election())

            # Subscribe to candle updates using production subject prefix
            subscriptions: List[Subscription] = []

            for symbol in self.supported_symbols:
                for timeframe in self.supported_timeframes:
                    # Use the production subject prefix for candle data with klines
                    subject = f"{self.nats_subject_prefix_production}.klines.{symbol}.{timeframe}"
                    # Use queue group to ensure only one replica processes each message
                    sub = await self.nc.subscribe(
                        subject, cb=self._handle_candle_message, queue="ta-bot-workers"
                    )
                    subscriptions.append(sub)
                    logger.info(f"Subscribed to {subject}")

            self.subscriptions = subscriptions
            logger.info(f"NATS listener started successfully with {len(subscriptions)} subscriptions")

        except Exception as e:
            logger.error(f"Error starting NATS listener: {e}")
            raise

    async def _handle_candle_message(self, msg):
        """Handle incoming candle message."""
        try:
            # Only process messages if this replica is the leader
            if not self.leader_election or not self.leader_election.is_current_leader():
                logger.debug(f"Skipping message processing - not the leader")
                return

            # Log every message received with subject and data length
            subject = msg.subject
            data_length = len(msg.data)
            logger.info(f"Received NATS message - Subject: {subject}, Data length: {data_length} bytes")
            
            # Log the raw message data for debugging
            raw_data = msg.data.decode()
            logger.info(f"Raw message data: {raw_data[:200]}..." if len(raw_data) > 200 else f"Raw message data: {raw_data}")

            # Parse message data
            data = json.loads(raw_data)

            # Extract message information
            symbol = data.get("symbol")
            period = data.get("period") or data.get("timeframe")
            candles = data.get("candles", [])
            
            # Handle different message formats
            if not candles and "data" in data:
                candles = data.get("data", [])

            if not symbol or not period:
                logger.warning(f"Invalid message format - missing symbol or period: {data}")
                return

            logger.info(
                f"Processing candle update for {symbol} {period}: {len(candles)} candles"
            )

            # Convert candles to DataFrame
            df = self._candles_to_dataframe(candles)

            if df is None or len(df) == 0:
                logger.warning(f"No valid candle data for {symbol} {period}")
                return

            # Analyze candles for signals
            signals = self.signal_engine.analyze_candles(df, symbol, period)

            if signals:
                logger.info(f"Generated {len(signals)} signals for {symbol} {period}")

                # Publish signals
                await self.publisher.publish_signals(signals)
            else:
                logger.debug(f"No signals generated for {symbol} {period}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse NATS message: {e}")
            logger.error(f"Raw message: {msg.data.decode()}")
        except Exception as e:
            logger.error(f"Error processing candle message: {e}")
            logger.error(f"Subject: {msg.subject}, Data: {msg.data.decode()[:200]}...")

    def _candles_to_dataframe(self, candles: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert candle data to pandas DataFrame."""
        try:
            if not candles:
                return None

            # Extract OHLCV data
            data = []
            for candle in candles:
                # Handle different candle formats
                if isinstance(candle, dict):
                    data.append(
                        {
                            "timestamp": candle.get("timestamp") or candle.get("time"),
                            "open": float(candle.get("open", 0)),
                            "high": float(candle.get("high", 0)),
                            "low": float(candle.get("low", 0)),
                            "close": float(candle.get("close", 0)),
                            "volume": float(candle.get("volume", 0)),
                        }
                    )
                else:
                    logger.warning(f"Unexpected candle format: {candle}")

            df = pd.DataFrame(data)

            # Sort by timestamp if available
            if "timestamp" in df.columns and not df.empty:
                df = df.sort_values("timestamp")

            return df

        except Exception as e:
            logger.error(f"Error converting candles to DataFrame: {e}")
            return None

    async def _cleanup(self):
        """Clean up NATS connections and subscriptions."""
        try:
            # Unsubscribe from all topics
            for subscription in self.subscriptions:
                await subscription.unsubscribe()

            # Close NATS connection
            await self.nc.close()
            logger.info("NATS listener cleaned up")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def stop(self):
        """Stop the NATS listener."""
        await self._cleanup()
