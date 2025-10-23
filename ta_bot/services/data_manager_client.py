"""
Data Manager client for petrosa-bot-ta-analysis.

This module provides a client for interacting with the petrosa-data-manager API
for fetching candle data and persisting signals.
"""

import os
from typing import Any, Dict, List, Optional

import pandas as pd
from data_manager_client import DataManagerClient as BaseDataManagerClient
from data_manager_client.exceptions import APIError, ConnectionError, TimeoutError

logger = None


def get_logger():
    """Get logger instance."""
    global logger
    if logger is None:
        import logging

        logger = logging.getLogger(__name__)
    return logger


class DataManagerClient:
    """
    Data Manager client for the TA Bot.

    Provides methods for fetching candle data and persisting signals
    through the petrosa-data-manager API.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize the Data Manager client.

        Args:
            base_url: Data Manager API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url or os.getenv(
            "DATA_MANAGER_URL", "http://petrosa-data-manager:8000"
        )
        self.timeout = timeout
        self.max_retries = max_retries

        # Initialize the base client
        self._client = BaseDataManagerClient(
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

        self._logger = get_logger()
        self._logger.info(f"Initialized Data Manager client: {self.base_url}")

    async def connect(self):
        """Connect to the Data Manager service."""
        try:
            # Test connection with health check
            health = await self._client.health()
            if health.get("status") != "healthy":
                raise ConnectionError(f"Data Manager health check failed: {health}")

            self._logger.info("Connected to Data Manager service")

        except Exception as e:
            self._logger.error(f"Failed to connect to Data Manager: {e}")
            raise

    async def disconnect(self):
        """Disconnect from the Data Manager service."""
        try:
            await self._client.close()
            self._logger.info("Disconnected from Data Manager service")
        except Exception as e:
            self._logger.warning(f"Error disconnecting from Data Manager: {e}")

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
        try:
            self._logger.info(f"Fetching {limit} candles for {symbol} ({period})")

            # Use the domain-specific candles endpoint
            result = await self._client.get_candles(
                pair=symbol,
                period=period,
                limit=limit,
                sort_order="desc",  # Most recent first
            )

            if not result.get("data"):
                self._logger.warning(f"No candle data found for {symbol} ({period})")
                return pd.DataFrame()

            # Convert to DataFrame
            candles_data = result["data"]
            df = pd.DataFrame(candles_data)

            # Ensure we have the required columns
            required_columns = ["timestamp", "open", "high", "low", "close", "volume"]
            if not all(col in df.columns for col in required_columns):
                self._logger.error(
                    f"Missing required columns in candle data: {df.columns.tolist()}"
                )
                return pd.DataFrame()

            # Convert timestamp to datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Convert numeric columns to float
            numeric_columns = ["open", "high", "low", "close", "volume"]
            for col in numeric_columns:
                df[col] = df[col].astype(float)

            # Sort by timestamp (oldest first for technical analysis)
            df = df.sort_values("timestamp").reset_index(drop=True)

            self._logger.info(f"Retrieved {len(df)} candles for {symbol} ({period})")
            return df

        except APIError as e:
            self._logger.error(
                f"API error fetching candles for {symbol} ({period}): {e}"
            )
            return pd.DataFrame()
        except ConnectionError as e:
            self._logger.error(
                f"Connection error fetching candles for {symbol} ({period}): {e}"
            )
            return pd.DataFrame()
        except TimeoutError as e:
            self._logger.error(
                f"Timeout error fetching candles for {symbol} ({period}): {e}"
            )
            return pd.DataFrame()
        except Exception as e:
            self._logger.error(
                f"Unexpected error fetching candles for {symbol} ({period}): {e}"
            )
            return pd.DataFrame()

    async def persist_signal(self, signal_data: Dict[str, Any]) -> bool:
        """
        Persist a single signal to Data Manager.

        Args:
            signal_data: Signal data dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            self._logger.info(f"Persisting signal for {signal_data.get('symbol')}")

            # Use the generic insert endpoint for signals
            result = await self._client.insert(
                database="mongodb",  # Use MongoDB for signals
                collection="signals",
                data=signal_data,
                validate=True,
            )

            inserted_count = result.get("inserted_count", 0)
            if inserted_count > 0:
                self._logger.info(
                    f"Successfully persisted signal for {signal_data.get('symbol')}"
                )
                return True
            else:
                self._logger.warning(
                    f"No signal was inserted for {signal_data.get('symbol')}"
                )
                return False

        except Exception as e:
            self._logger.error(
                f"Error persisting signal for {signal_data.get('symbol')}: {e}"
            )
            return False

    async def persist_signals_batch(self, signals: List[Dict[str, Any]]) -> bool:
        """
        Persist multiple signals to Data Manager in a batch.

        Args:
            signals: List of signal data dictionaries

        Returns:
            True if successful, False otherwise
        """
        if not signals:
            self._logger.warning("No signals to persist")
            return True

        try:
            self._logger.info(f"Persisting batch of {len(signals)} signals")

            # Use the generic insert endpoint for signals
            result = await self._client.insert(
                database="mongodb",  # Use MongoDB for signals
                collection="signals",
                data=signals,
                validate=True,
            )

            inserted_count = result.get("inserted_count", 0)
            if inserted_count == len(signals):
                self._logger.info(f"Successfully persisted all {len(signals)} signals")
                return True
            else:
                self._logger.warning(
                    f"Only {inserted_count} of {len(signals)} signals were inserted"
                )
                return False

        except Exception as e:
            self._logger.error(f"Error persisting signal batch: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the Data Manager service.

        Returns:
            Health status information
        """
        try:
            health = await self._client.health()
            self._logger.info(
                f"Data Manager health check: {health.get('status', 'unknown')}"
            )
            return health
        except Exception as e:
            self._logger.error(f"Data Manager health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
