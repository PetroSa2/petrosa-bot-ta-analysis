"""
Signal publisher service for sending trading signals to Trade Engine.
"""

import json
from typing import List

import aiohttp
import nats  # Added to use nats.connect
import nats.aio.client
import structlog

from ta_bot.models.signal import Signal

logger = structlog.get_logger()


class SignalPublisher:
    """Publish trading signals to Trade Engine via REST API and NATS."""

    def __init__(
        self,
        api_endpoint: str,
        nats_url: str = None,
        enable_rest_publishing: bool = False,
    ):
        """Initialize the signal publisher.

        Args:
            api_endpoint: HTTP endpoint for REST API publishing
            nats_url: NATS server URL for NATS publishing
            enable_rest_publishing: Enable REST API publishing (default: False to prevent duplicates)
        """
        self.api_endpoint = api_endpoint
        self.nats_url = nats_url
        self.enable_rest_publishing = enable_rest_publishing
        self.session = None
        self.nats_client = None

    async def start(self):
        """Start the publisher session."""
        # Only create HTTP session if REST publishing is enabled
        if self.enable_rest_publishing:
            self.session = aiohttp.ClientSession()
            logger.info("REST API publishing enabled")
        else:
            logger.info("REST API publishing disabled (NATS-only mode)")

        # Initialize NATS connection if URL is provided
        if self.nats_url:
            try:
                self.nats_client = await nats.connect(self.nats_url)
                logger.info(f"Connected to NATS server: {self.nats_url}")
            except Exception as e:
                logger.error(f"Failed to connect to NATS: {e}")
                self.nats_client = None

    async def stop(self):
        """Stop the publisher session."""
        if self.session:
            await self.session.close()

        if self.nats_client:
            await self.nats_client.close()

    async def publish_signals(self, signals: List[Signal]):
        """Publish signals to the Trade Engine."""
        if not signals:
            logger.info("No signals to publish")
            return

        logger.info(
            f"📤 PUBLISH REQUEST: {len(signals)} signals | "
            f"NATS Connected: {self.nats_client is not None} | "
            f"REST Enabled: {self.enable_rest_publishing}"
        )

        # Publish via REST API (only if enabled)
        if self.enable_rest_publishing:
            await self._publish_via_rest(signals)
        else:
            logger.debug("REST API publishing skipped (disabled)")

        # Publish via NATS
        await self._publish_via_nats(signals)

        logger.info(f"✅ PUBLISH COMPLETE: {len(signals)} signals dispatched")

    async def _publish_via_rest(self, signals: List[Signal]):
        """Publish signals via REST API."""
        if not self.session:
            logger.warning("REST session not started")
            return

        for signal in signals:
            try:
                # Convert signal to Trade Engine format
                signal_data = signal.to_dict()

                logger.info(
                    f"Publishing signal via REST: {signal.strategy_id} - {signal.action}"
                )

                async with self.session.post(
                    self.api_endpoint,
                    json=signal_data,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        logger.info(
                            f"Signal published successfully via REST: {signal.strategy_id}"
                        )
                    else:
                        response_text = await response.text()
                        logger.error(
                            f"Failed to publish signal via REST: {response.status} - {response_text}"
                        )

            except Exception as e:
                logger.error(f"Error publishing signal via REST: {e}")

    async def _publish_via_nats(self, signals: List[Signal]):
        """Publish signals via NATS."""
        if not self.nats_client:
            logger.error(
                "❌ CRITICAL: Cannot publish to NATS - client not connected. "
                "Signals will be LOST! Check NATS_URL and connectivity."
            )
            return

        for signal in signals:
            try:
                # Convert signal to Trade Engine format
                signal_data = signal.to_dict()

                # DEBUG: Log the signal data including stop_loss/take_profit
                logger.info(
                    f"🔍 DEBUG SIGNAL DATA: {signal.strategy_id} | "
                    f"SL: {signal_data.get('stop_loss')} | TP: {signal_data.get('take_profit')}"
                )

                # Publish to NATS subject that Trade Engine listens to
                subject = "signals.trading"
                message = json.dumps(signal_data).encode()

                logger.info(
                    f"Publishing signal via NATS: {signal.strategy_id} - {signal.action}"
                )

                logger.info(
                    f"🔍 NATS PUBLISH DETAILS: Subject={subject} | "
                    f"Message size={len(message)} bytes | "
                    f"NATS client connected={self.nats_client.is_connected if self.nats_client else False}"
                )

                await self.nats_client.publish(subject, message)

                logger.info(
                    f"Signal published successfully via NATS: {signal.strategy_id}"
                )

            except Exception as e:
                logger.error(f"Error publishing signal via NATS: {e}")

    async def publish_batch(self, signals: List[Signal]):
        """Publish multiple signals in a batch."""
        if not signals:
            logger.info("No signals to publish in batch")
            return

        logger.info(f"Publishing batch of {len(signals)} signals")

        # Publish via REST API (only if enabled)
        if self.enable_rest_publishing:
            await self._publish_batch_via_rest(signals)
        else:
            logger.debug("REST API batch publishing skipped (disabled)")

        # Publish via NATS
        await self._publish_batch_via_nats(signals)

    async def _publish_batch_via_rest(self, signals: List[Signal]):
        """Publish signals batch via REST API."""
        if not self.session:
            logger.warning("REST session not started")
            return

        try:
            # Convert signals to Trade Engine format
            signals_data = [signal.to_dict() for signal in signals]

            async with self.session.post(
                self.api_endpoint,
                json={"signals": signals_data},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    logger.info(
                        f"Batch published successfully via REST: {len(signals)} signals"
                    )
                else:
                    response_text = await response.text()
                    logger.error(
                        f"Failed to publish batch via REST: {response.status} - {response_text}"
                    )

        except Exception as e:
            logger.error(f"Error publishing batch via REST: {e}")

    async def _publish_batch_via_nats(self, signals: List[Signal]):
        """Publish signals batch via NATS."""
        if not self.nats_client:
            logger.warning("NATS client not connected")
            return

        try:
            subject = "signals.trading"

            for signal in signals:
                signal_data = signal.to_dict()
                message = json.dumps(signal_data).encode()
                await self.nats_client.publish(subject, message)

            logger.info(
                f"Batch published successfully via NATS: {len(signals)} signals"
            )

        except Exception as e:
            logger.error(f"Error publishing batch via NATS: {e}")
