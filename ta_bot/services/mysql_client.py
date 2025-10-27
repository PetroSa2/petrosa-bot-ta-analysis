"""
MySQL client for fetching candle data and persisting signals.

This client uses Data Manager API exclusively for all data access.
Data Manager is the centralized data access layer that provides:
- Connection pooling and retry logic
- Circuit breaker protection
- Centralized data quality and integrity
- Query from MongoDB for better time-series performance
"""

import logging
from typing import Any

import pandas as pd

from .data_manager_client import DataManagerClient

logger = logging.getLogger(__name__)


class MySQLClient:
    """
    MySQL client for database operations via Data Manager API.

    This class now exclusively uses Data Manager API for all data operations.
    Direct MySQL connections have been removed to enforce proper service architecture.

    Fail-fast behavior: If Data Manager is unavailable, the service will not start.
    """

    def __init__(self):
        """
        Initialize MySQL client with Data Manager.

        Note: All parameters for direct MySQL connection have been removed.
        Data Manager handles all database connectivity internally.
        """
        self.data_manager_client = DataManagerClient()
        logger.info("Initialized MySQL client using Data Manager API")

    async def connect(self):
        """Connect to Data Manager API."""
        try:
            await self.data_manager_client.connect()
            logger.info("Connected to Data Manager successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Data Manager: {e}")
            logger.error("Cannot start TA-BOT without Data Manager - failing startup")
            raise RuntimeError(
                "Data Manager connection required for TA-BOT operation"
            ) from e

    async def disconnect(self):
        """Disconnect from Data Manager API."""
        await self.data_manager_client.disconnect()
        logger.info("Disconnected from Data Manager")

    async def health_check(self) -> bool:
        """
        Verify Data Manager is available and healthy.

        Returns:
            bool: True if Data Manager is healthy, False otherwise
        """
        try:
            result = await self.data_manager_client._client.health()
            is_healthy = result.get("status") == "healthy"
            if is_healthy:
                logger.debug("Data Manager health check: OK")
            else:
                logger.warning(f"Data Manager health check failed: {result}")
            return is_healthy
        except Exception as e:
            logger.error(f"Data Manager health check error: {e}")
            return False

    async def fetch_candles(
        self, symbol: str, period: str, limit: int = 100
    ) -> pd.DataFrame:
        """
        Fetch candle data from Data Manager.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            period: Timeframe (e.g., '15m', '1h')
            limit: Maximum number of candles to fetch

        Returns:
            DataFrame with OHLCV data
        """
        return await self.data_manager_client.fetch_candles(symbol, period, limit)

    async def persist_signal(self, signal_data: dict[str, Any]) -> bool:
        """
        Persist a single signal via Data Manager.

        Args:
            signal_data: Signal data dictionary

        Returns:
            bool: True if successful, False otherwise
        """
        return await self.data_manager_client.persist_signal(signal_data)

    async def persist_signals_batch(self, signals: list[dict[str, Any]]) -> bool:
        """
        Persist multiple signals via Data Manager in a batch.

        Args:
            signals: List of signal data dictionaries

        Returns:
            bool: True if successful, False otherwise
        """
        return await self.data_manager_client.persist_signals_batch(signals)
