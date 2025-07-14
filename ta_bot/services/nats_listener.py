"""
NATS listener service for receiving candle data and processing signals.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List
import pandas as pd
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrConnectionClosed, ErrTimeout

from ta_bot.core.signal_engine import SignalEngine
from ta_bot.services.publisher import SignalPublisher
from ta_bot.models.signal import Signal

logger = logging.getLogger(__name__)


class NATSListener:
    """NATS message listener for candle data."""

    def __init__(
        self, nats_url: str, signal_engine: SignalEngine, publisher: SignalPublisher
    ):
        """Initialize the NATS listener."""
        self.nats_url = nats_url
        self.signal_engine = signal_engine
        self.publisher = publisher
        self.nc = NATS()
        self.subscriptions = []

    async def start(self):
        """Start listening for NATS messages."""
        try:
            # Connect to NATS
            await self.nc.connect(self.nats_url)
            logger.info(f"Connected to NATS at {self.nats_url}")

            # Subscribe to candle topics
            await self._subscribe_to_candles()

            # Keep the listener running
            while True:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in NATS listener: {e}")
            raise
        finally:
            await self._cleanup()

    async def _subscribe_to_candles(self):
        """Subscribe to candle update topics."""
        # Subscribe to candle updates for different symbols and timeframes
        topics = [
            "candles.BTCUSDT.15m",
            "candles.BTCUSDT.1h",
            "candles.ETHUSDT.15m",
            "candles.ETHUSDT.1h",
            "candles.ADAUSDT.15m",
            "candles.ADAUSDT.1h",
        ]

        for topic in topics:
            subscription = await self.nc.subscribe(
                topic, cb=self._handle_candle_message
            )
            self.subscriptions.append(subscription)
            logger.info(f"Subscribed to {topic}")

    async def _handle_candle_message(self, msg):
        """Handle incoming candle message."""
        try:
            # Parse message data
            data = json.loads(msg.data.decode())

            # Extract message information
            symbol = data.get("symbol")
            period = data.get("period")
            candles = data.get("candles", [])

            if not symbol or not period or not candles:
                logger.warning(f"Invalid candle message format: {data}")
                return

            logger.info(
                f"Received candle update for {symbol} {period}: {len(candles)} candles"
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
        except Exception as e:
            logger.error(f"Error processing candle message: {e}")

    def _candles_to_dataframe(self, candles: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert candle data to pandas DataFrame."""
        try:
            if not candles:
                return None

            # Extract OHLCV data
            data = []
            for candle in candles:
                data.append(
                    {
                        "timestamp": candle.get("timestamp"),
                        "open": float(candle.get("open", 0)),
                        "high": float(candle.get("high", 0)),
                        "low": float(candle.get("low", 0)),
                        "close": float(candle.get("close", 0)),
                        "volume": float(candle.get("volume", 0)),
                    }
                )

            df = pd.DataFrame(data)

            # Sort by timestamp if available
            if "timestamp" in df.columns:
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
