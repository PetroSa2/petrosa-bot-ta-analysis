#!/usr/bin/env python3
"""
Technical Analysis Bot for Crypto Trading
Main entry point for the TA bot microservice.
"""

import asyncio
import logging
from typing import Dict, Any

from core.signal_engine import SignalEngine
from services.nats_listener import NATSListener
from services.publisher import SignalPublisher
from config import Config
from health import start_health_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point for the TA bot."""
    try:
        # Initialize components
        config = Config()
        signal_engine = SignalEngine()
        publisher = SignalPublisher(config.api_endpoint)
        nats_listener = NATSListener(
            nats_url=config.nats_url,
            signal_engine=signal_engine,
            publisher=publisher
        )
        
        logger.info("Starting TA Bot...")
        
        # Start health server
        health_runner = await start_health_server(
            nats_url=config.nats_url,
            api_endpoint=config.api_endpoint,
            port=8000
        )
        
        # Start listening for NATS messages
        await nats_listener.start()
        
    except Exception as e:
        logger.error(f"Failed to start TA Bot: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main()) 