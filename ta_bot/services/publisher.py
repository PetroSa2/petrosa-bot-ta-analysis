"""
REST publisher service for sending trading signals to external API.
"""

import asyncio
import json
import logging
from typing import List

import aiohttp
import structlog

from ta_bot.models.signal import Signal

logger = structlog.get_logger()


class SignalPublisher:
    """Publish trading signals to external API."""

    def __init__(self, api_endpoint: str):
        """Initialize the signal publisher."""
        self.api_endpoint = api_endpoint
        self.session = None

    async def start(self):
        """Start the publisher session."""
        self.session = aiohttp.ClientSession()

    async def stop(self):
        """Stop the publisher session."""
        if self.session:
            await self.session.close()

    async def publish_signals(self, signals: List[Signal]):
        """Publish signals to the external API."""
        if not signals:
            return

        try:
            # Convert signals to JSON
            signal_data = [signal.to_dict() for signal in signals]

            # Send to API
            async with self.session.post(
                f"{self.api_endpoint}/signals",
                json=signal_data,
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status == 200:
                    logger.info(f"Successfully published {len(signals)} signals to API")
                else:
                    logger.error(
                        f"Failed to publish signals: {response.status} - "
                        f"{await response.text()}"
                    )

        except Exception as e:
            logger.error(f"Error publishing signals: {e}")

    async def publish_signal(self, signal: Signal):
        """Publish a single signal to the external API."""
        try:
            # Convert signal to JSON
            signal_data = signal.to_dict()

            # Send to API
            async with self.session.post(
                f"{self.api_endpoint}/signal",
                json=signal_data,
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status == 200:
                    logger.info(
                        f"Successfully published signal {signal.symbol} "
                        f"{signal.signal_type.value}"
                    )
                else:
                    logger.error(
                        f"Failed to publish signal: {response.status} - "
                        f"{await response.text()}"
                    )

        except Exception as e:
            logger.error(f"Error publishing signal: {e}")
