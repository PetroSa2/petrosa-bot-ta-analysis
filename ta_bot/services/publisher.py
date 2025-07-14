"""
REST publisher service for sending trading signals to external API.
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Any, List
from ta_bot.models.signal import Signal

logger = logging.getLogger(__name__)


class SignalPublisher:
    """Publishes trading signals to external API endpoint."""
    
    def __init__(self, api_endpoint: str):
        """Initialize the publisher with API endpoint."""
        self.api_endpoint = api_endpoint
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def publish_signal(self, signal: Signal) -> bool:
        """Publish a single signal to the API."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            signal_data = signal.to_dict()
            
            async with self.session.post(
                self.api_endpoint,
                json=signal_data,
                headers={'Content-Type': 'application/json'},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    logger.info(f"Signal published successfully: {signal.strategy} for {signal.symbol}")
                    return True
                else:
                    logger.error(f"Failed to publish signal. Status: {response.status}")
                    return False
        
        except asyncio.TimeoutError:
            logger.error(f"Timeout publishing signal to {self.api_endpoint}")
            return False
        except Exception as e:
            logger.error(f"Error publishing signal: {e}")
            return False
    
    async def publish_signals(self, signals: List[Signal]) -> Dict[str, int]:
        """Publish multiple signals and return success/failure counts."""
        if not signals:
            return {'success': 0, 'failure': 0}
        
        results = await asyncio.gather(
            *[self.publish_signal(signal) for signal in signals],
            return_exceptions=True
        )
        
        success_count = sum(1 for result in results if result is True)
        failure_count = len(results) - success_count
        
        logger.info(f"Published {success_count} signals, {failure_count} failures")
        
        return {
            'success': success_count,
            'failure': failure_count
        } 