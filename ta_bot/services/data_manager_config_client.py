"""
Data Manager Configuration Client.
Handles interaction with the Data Manager service for runtime configuration.
"""

import logging
import os
from datetime import datetime
from typing import Any

import aiohttp
from aiohttp import ClientSession, ClientTimeout

logger = logging.getLogger(__name__)


class DataManagerConfigClient:
    """
    Client for interacting with the Data Manager Configuration API.
    Replaces direct database access with HTTP API calls to the data management service.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
        max_retries: int = 3,
    ):
        """
        Initialize the Data Manager configuration client.

        Args:
            base_url: Data Manager API base URL. Defaults to DATA_MANAGER_URL env var.
            timeout: Request timeout in seconds. Precedence: explicit arg > DATA_MANAGER_TIMEOUT env var > 30s.
            max_retries: Maximum number of retry attempts.
        """
        # Resolve timeout with robust parsing and validation
        if timeout is None:
            env_timeout = os.getenv("DATA_MANAGER_TIMEOUT")
            if env_timeout:
                try:
                    parsed_timeout = int(env_timeout)
                    if parsed_timeout > 0:
                        timeout = parsed_timeout
                    else:
                        logger.warning(
                            f"Invalid DATA_MANAGER_TIMEOUT value '{env_timeout}': must be > 0. Falling back to default 30s."
                        )
                        timeout = 30
                except (ValueError, TypeError):
                    logger.warning(
                        f"Failed to parse DATA_MANAGER_TIMEOUT '{env_timeout}': must be an integer. Falling back to default 30s."
                    )
                    timeout = 30
            else:
                timeout = 30

        self.base_url = (
            base_url or os.getenv("DATA_MANAGER_URL", "http://petrosa-data-manager:80")
        ).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._session: aiohttp.ClientSession | None = None

        logger.info(
            f"Initialized Data Manager config client: {self.base_url} (timeout={self.timeout}s)"
        )

    async def connect(self):
        """Connect to the Data Manager service."""
        try:
            if not self._session:
                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                )

            # Simple health check to verify connectivity
            async with self._session.get(
                f"{self.base_url}/health/liveness",
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                if response.status == 200:
                    logger.info("Successfully connected to Data Manager service")
                    return True
                else:
                    logger.error(f"Data Manager health check failed: {response.status}")
                    raise ConnectionError(f"Health check failed: {response.status}")

        except Exception as e:
            logger.error(f"Failed to connect to Data Manager: {e}")
            if self._session:
                await self._session.close()
                self._session = None
            raise ConnectionError(f"Could not connect to Data Manager: {e}") from e

    async def disconnect(self):
        """Disconnect from the Data Manager service."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("Disconnected from Data Manager service")

    async def get_app_config(self) -> dict[str, Any]:
        """
        Fetch global application configuration.

        Returns:
            Dictionary containing the application configuration
        """
        if not self._session:
            await self.connect()

        try:
            async with self._session.get(
                f"{self.base_url}/api/v1/config/application",
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(
                        f"Failed to fetch application config: {response.status}"
                    )
                    return self._get_default_config()

        except Exception as e:
            logger.error(f"Error fetching application config: {e}")
            return self._get_default_config()

    async def set_app_config(
        self, config_data: dict[str, Any], changed_by: str, reason: str | None = None
    ) -> bool:
        """
        Update global application configuration.

        Args:
            config_data: Configuration changes to apply
            changed_by: User or system identifier making the change
            reason: Optional reason for the change

        Returns:
            True if successful, False otherwise
        """
        if not self._session:
            await self.connect()

        try:
            # Ensure mandatory fields are present
            payload = {
                "enabled_strategies": config_data.get("enabled_strategies", []),
                "symbols": config_data.get("symbols", []),
                "candle_periods": config_data.get("candle_periods", []),
                "min_confidence": config_data.get("min_confidence", 0.6),
                "max_confidence": config_data.get("max_confidence", 0.95),
                "max_positions": config_data.get("max_positions", 10),
                "position_sizes": config_data.get(
                    "position_sizes", [100, 200, 500, 1000]
                ),
                "changed_by": changed_by,
                "reason": reason or "Config update via TA Bot",
            }

            async with self._session.post(
                f"{self.base_url}/api/v1/config/application",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"Error updating application config: {e}")
            return False

    async def get_strategy_config(
        self, strategy_id: str, symbol: str | None = None
    ) -> dict[str, Any]:
        """
        Fetch configuration for a specific strategy.

        Args:
            strategy_id: Unique identifier for the strategy
            symbol: Optional symbol for pair-specific configuration

        Returns:
            Dictionary containing the strategy configuration
        """
        if not self._session:
            await self.connect()

        url = f"{self.base_url}/api/v1/config/strategies/{strategy_id}"
        if symbol:
            url += f"?symbol={symbol}"

        try:
            async with self._session.get(
                url, timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.debug(
                        f"No specific config found for {strategy_id} ({symbol or 'global'})"
                    )
                    return self._get_default_strategy_config()

        except Exception as e:
            logger.error(f"Error fetching strategy config for {strategy_id}: {e}")
            return self._get_default_strategy_config()

    async def set_strategy_config(
        self,
        strategy_id: str,
        parameters: dict[str, Any],
        changed_by: str,
        symbol: str | None = None,
        reason: str | None = None,
    ) -> bool:
        """
        Update configuration for a specific strategy.

        Args:
            strategy_id: Unique identifier for the strategy
            parameters: Parameter overrides to apply
            changed_by: User or system identifier making the change
            symbol: Optional symbol for pair-specific configuration
            reason: Optional reason for the change

        Returns:
            True if successful, False otherwise
        """
        if not self._session:
            await self.connect()

        url = f"{self.base_url}/api/v1/config/strategies/{strategy_id}"
        if symbol:
            url += f"?symbol={symbol}"

        try:
            payload = {
                "parameters": parameters,
                "changed_by": changed_by,
                "reason": reason or f"Strategy config update for {strategy_id}",
            }

            async with self._session.post(
                url, json=payload, timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"Error updating strategy config for {strategy_id}: {e}")
            return False

    async def list_strategy_configs(self) -> list[str]:
        """
        Fetch list of all strategies with custom configurations.

        Returns:
            List of strategy identifiers
        """
        if not self._session:
            await self.connect()

        try:
            async with self._session.get(
                f"{self.base_url}/api/v1/config/strategies",
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("strategy_ids", [])
                else:
                    return []

        except Exception as e:
            logger.error(f"Error listing strategy configs: {e}")
            return []

    async def delete_strategy_config(
        self, strategy_id: str, symbol: str | None = None
    ) -> bool:
        """
        Delete configuration for a specific strategy.

        Args:
            strategy_id: Unique identifier for the strategy
            symbol: Optional symbol for pair-specific configuration

        Returns:
            True if successful, False otherwise
        """
        if not self._session:
            await self.connect()

        url = f"{self.base_url}/api/v1/config/strategies/{strategy_id}"
        if symbol:
            url += f"?symbol={symbol}"

        try:
            async with self._session.delete(
                url, timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"Error deleting strategy config for {strategy_id}: {e}")
            return False

    def _get_default_config(self) -> dict[str, Any]:
        """Return a safe default application configuration."""
        return {
            "enabled_strategies": [],
            "symbols": [],
            "candle_periods": [],
            "min_confidence": 0.6,
            "max_confidence": 0.95,
            "max_positions": 10,
            "position_sizes": [100, 200, 500, 1000],
            "version": 0,
            "source": "default",
        }

    def _get_default_strategy_config(self) -> dict[str, Any]:
        """Return a safe default strategy configuration."""
        return {
            "parameters": {},
            "version": 0,
            "source": "none",
            "is_override": False,
        }
