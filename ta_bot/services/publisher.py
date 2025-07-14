"""
REST publisher service for sending trading signals to external API.
"""

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
        if not self.session:
            logger.warning("Publisher session not started")
            return

        for signal in signals:
            try:
                # Convert signal to JSON
                signal_data = {
                    "symbol": signal.symbol,
                    "period": signal.period,
                    "signal": signal.signal_type.value,
                    "confidence": signal.confidence,
                    "strategy": signal.strategy,
                    "metadata": signal.metadata
                }

                async with self.session.post(
                    self.api_endpoint,
                    json=signal_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Signal published successfully: {signal.symbol}")
                    else:
                        logger.error(f"Failed to publish signal: {response.status}")
                        
            except Exception as e:
                logger.error(f"Error publishing signal: {e}")

    async def publish_batch(self, signals: List[Signal]):
        """Publish multiple signals in a batch."""
        if not self.session:
            logger.warning("Publisher session not started")
            return

        try:
            # Convert signals to JSON
            signals_data = []
            for signal in signals:
                signal_data = {
                    "symbol": signal.symbol,
                    "period": signal.period,
                    "signal": signal.signal_type.value,
                    "confidence": signal.confidence,
                    "strategy": signal.strategy,
                    "metadata": signal.metadata
                }
                signals_data.append(signal_data)

            async with self.session.post(
                self.api_endpoint,
                json={"signals": signals_data},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    logger.info(f"Batch published successfully: {len(signals)} signals")
                else:
                    logger.error(f"Failed to publish batch: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error publishing batch: {e}")
