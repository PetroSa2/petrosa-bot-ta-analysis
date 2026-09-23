"""
Data Manager client for petrosa-bot-ta-analysis.

This module provides a client for interacting with the petrosa-data-manager API
for fetching candle data and persisting signals.
"""

import asyncio  # noqa: I001
import os
from typing import Any

import pandas as pd

# Vendored locally — see ta_bot/services/dm_sdk/__init__.py for rationale
# (petrosa-bot-ta-analysis#267): the external `data_manager_client` package
# this used to import was never actually installable.
from ta_bot.services.dm_sdk import DataManagerClient as BaseDataManagerClient
from ta_bot.services.dm_sdk.exceptions import APIError, ConnectionError, TimeoutError


# Minimum warm-up candles fetched for every analysis cycle.
#
# The hungriest registered strategy is ``minervini_trend_template`` at
# ``min_periods = 265`` (its 260/252-bar "52-week" windows). 400 applies the
# 1.5x safety margin from the data-manager candle retention contract
# (petrosa-bot-ta-analysis#303).
#
# This is the single source of truth for the fetch size -- do not re-declare
# the limit at call sites. ``tests/test_candle_warmup_limit.py`` fails CI if a
# strategy is registered whose ``min_periods`` exceeds it.
MIN_WARMUP_CANDLES = 400

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
        base_url: str | None = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff_base: float = 0.5,
    ):
        """
        Initialize the Data Manager client.

        Args:
            base_url: Data Manager API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff_base: Base seconds for the exponential backoff used
                by connect() between "not ready yet" retries
                (petrosa-bot-ta-analysis#269)
        """
        self.base_url = base_url or os.getenv(
            "DATA_MANAGER_URL", "http://petrosa-data-manager:80"
        )
        self.timeout = timeout
        self.max_retries = max_retries
        self._retry_backoff_base = retry_backoff_base

        # Initialize the base client
        self._client = BaseDataManagerClient(
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

        self._logger = get_logger()
        self._logger.info(f"Initialized Data Manager client: {self.base_url}")

    async def connect(self):
        """Connect to the Data Manager service.

        Retries a "not ready" response with exponential backoff before
        giving up — data-manager can still be starting its own dependencies
        at pod startup, which is a transient condition, not a contract
        break. On final failure (whether unreachable or still-not-ready
        after all retries) the underlying HTTP client is closed so a failed
        startup never leaks an open Data Manager connection
        (petrosa-bot-ta-analysis#269).
        """
        last_health: dict[str, Any] | None = None
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                # Test connection with health check. Data Manager's real
                # `/health/readiness` response is `{ready: bool, components: dict,
                # timestamp: ...}` — it never returns a `status` key (see
                # petrosa-data-manager/data_manager/api/routes/health.py's
                # `ReadinessStatus` model). petrosa-bot-ta-analysis#270.
                health = await self._client.health()
            except Exception as e:
                last_error = e
                last_health = None
                self._logger.warning(
                    f"Data Manager unreachable (attempt {attempt}/"
                    f"{self.max_retries}): {e}"
                )
            else:
                last_error = None
                last_health = health
                if health.get("ready", False):
                    self._logger.info("Connected to Data Manager service")
                    return
                self._logger.warning(
                    f"Data Manager not ready yet (attempt {attempt}/"
                    f"{self.max_retries}): {health}"
                )

            if attempt < self.max_retries:
                await asyncio.sleep(self._retry_backoff_base * (2 ** (attempt - 1)))

        await self._close_silently()

        if last_error is not None:
            self._logger.error(
                f"Failed to connect to Data Manager after {self.max_retries} "
                f"attempts: {last_error}"
            )
            raise ConnectionError(
                f"Data Manager unreachable after {self.max_retries} attempts: "
                f"{last_error}"
            ) from last_error

        self._logger.error(
            f"Data Manager health-check contract not satisfied after "
            f"{self.max_retries} attempts: {last_health}"
        )
        raise ConnectionError(
            f"Data Manager health check failed after {self.max_retries} "
            f"attempts: {last_health}"
        )

    async def _close_silently(self):
        """Close the underlying HTTP client, swallowing close-time errors.

        Used on the connect() failure path so a failed startup never leaves
        an open HTTP session/connector behind (petrosa-bot-ta-analysis#269).
        """
        try:
            await self._client.close()
        except Exception as close_err:
            self._logger.warning(
                f"Error closing Data Manager client after failed connect: {close_err}"
            )

    async def disconnect(self):
        """Disconnect from the Data Manager service."""
        try:
            await self._client.close()
            self._logger.info("Disconnected from Data Manager service")
        except Exception as e:
            self._logger.warning(f"Error disconnecting from Data Manager: {e}")

    async def fetch_candles(
        self, symbol: str, period: str, limit: int = MIN_WARMUP_CANDLES
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
            df = df.sort_values("timestamp")
            df = df.set_index("timestamp")

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

    async def persist_signal(self, signal_data: dict[str, Any]) -> bool:
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

    async def persist_signals_batch(self, signals: list[dict[str, Any]]) -> bool:
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

    async def health_check(self) -> dict[str, Any]:
        """
        Check the health of the Data Manager service.

        Returns:
            Health status information
        """
        try:
            health = await self._client.health()
            self._logger.info(
                f"Data Manager health check: ready={health.get('ready', 'unknown')}"
            )
            return health
        except Exception as e:
            self._logger.error(f"Data Manager health check failed: {e}")
            return {"ready": False, "error": str(e)}

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
