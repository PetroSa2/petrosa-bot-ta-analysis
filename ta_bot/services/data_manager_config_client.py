"""
Data Manager Configuration Client for TA Bot.

Provides configuration management through the data management service instead of direct database access.
"""

import logging
from datetime import datetime
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)


class DataManagerConfigClient:
    """
    Configuration client that communicates with the data management service.

    Replaces direct database access with HTTP API calls to the data management service.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize the Data Manager configuration client.

        Args:
            base_url: Data Manager API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = base_url or "http://petrosa-data-manager:8000"
        self.timeout = timeout
        self.max_retries = max_retries
        self._session: aiohttp.ClientSession | None = None

        logger.info(f"Initialized Data Manager config client: {self.base_url}")

    async def connect(self):
        """Connect to the Data Manager service."""
        try:
            if not self._session:
                self._session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                )

            # Test connection with health check
            async with self._session.get(
                f"{self.base_url}/health/liveness"
            ) as response:
                if response.status != 200:
                    raise ConnectionError(
                        f"Data Manager health check failed: {response.status}"
                    )

            logger.info("Connected to Data Manager service")

        except Exception as e:
            logger.error(f"Failed to connect to Data Manager: {e}")
            raise

    async def disconnect(self):
        """Disconnect from the Data Manager service."""
        try:
            if self._session:
                await self._session.close()
                self._session = None
            logger.info("Disconnected from Data Manager service")
        except Exception as e:
            logger.warning(f"Error disconnecting from Data Manager: {e}")

    async def get_app_config(self) -> dict[str, Any]:
        """
        Get application configuration from data management service.

        Returns:
            Application configuration dictionary
        """
        if not self._session:
            await self.connect()

        try:
            async with self._session.get(
                f"{self.base_url}/config/application"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.error(f"Failed to get app config: {response.status}")
                    return self._get_default_config()
        except Exception as e:
            logger.error(f"Error fetching app config: {e}")
            return self._get_default_config()

    async def set_app_config(
        self,
        config: dict[str, Any],
        changed_by: str,
        reason: str | None = None,
    ) -> bool:
        """
        Set application configuration through data management service.

        Args:
            config: Configuration values
            changed_by: Who is making the change
            reason: Optional reason for the change

        Returns:
            True if successful, False otherwise
        """
        if not self._session:
            await self.connect()

        try:
            payload = {
                "enabled_strategies": config.get("enabled_strategies", []),
                "symbols": config.get("symbols", []),
                "candle_periods": config.get("candle_periods", []),
                "min_confidence": config.get("min_confidence", 0.6),
                "max_confidence": config.get("max_confidence", 0.95),
                "max_positions": config.get("max_positions", 10),
                "position_sizes": config.get("position_sizes", [100, 200, 500, 1000]),
                "changed_by": changed_by,
                "reason": reason,
            }

            async with self._session.post(
                f"{self.base_url}/config/application", json=payload
            ) as response:
                if response.status == 200:
                    logger.info("Application config updated successfully")
                    return True
                else:
                    logger.error(f"Failed to update app config: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Error updating app config: {e}")
            return False

    async def get_strategy_config(
        self, strategy_id: str, symbol: str | None = None
    ) -> dict[str, Any]:
        """
        Get strategy configuration from data management service.

        Args:
            strategy_id: Strategy identifier
            symbol: Optional symbol for symbol-specific config

        Returns:
            Strategy configuration dictionary
        """
        if not self._session:
            await self.connect()

        try:
            url = f"{self.base_url}/config/strategies/{strategy_id}"
            if symbol:
                url += f"?symbol={symbol}"

            async with self._session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.warning(f"No config found for strategy {strategy_id}")
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
        Set strategy configuration through data management service.

        Args:
            strategy_id: Strategy identifier
            parameters: Strategy parameters
            changed_by: Who is making the change
            symbol: Optional symbol for symbol-specific config
            reason: Optional reason for the change

        Returns:
            True if successful, False otherwise
        """
        if not self._session:
            await self.connect()

        try:
            payload = {
                "parameters": parameters,
                "changed_by": changed_by,
                "reason": reason,
            }

            url = f"{self.base_url}/config/strategies/{strategy_id}"
            if symbol:
                url += f"?symbol={symbol}"

            async with self._session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Strategy config updated: {strategy_id}")
                    return True
                else:
                    logger.error(f"Failed to update strategy config: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Error updating strategy config for {strategy_id}: {e}")
            return False

    async def list_strategy_configs(self) -> list[str]:
        """
        List all strategy configurations.

        Returns:
            List of strategy IDs
        """
        if not self._session:
            await self.connect()

        try:
            async with self._session.get(
                f"{self.base_url}/config/strategies"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("strategy_ids", [])
                else:
                    logger.error(f"Failed to list strategy configs: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error listing strategy configs: {e}")
            return []

    async def delete_strategy_config(
        self, strategy_id: str, symbol: str | None = None
    ) -> bool:
        """
        Delete strategy configuration.

        Args:
            strategy_id: Strategy identifier
            symbol: Optional symbol for symbol-specific config

        Returns:
            True if successful, False otherwise
        """
        if not self._session:
            await self.connect()

        try:
            url = f"{self.base_url}/config/strategies/{strategy_id}"
            if symbol:
                url += f"?symbol={symbol}"

            async with self._session.delete(url) as response:
                if response.status == 200:
                    logger.info(f"Strategy config deleted: {strategy_id}")
                    return True
                else:
                    logger.error(f"Failed to delete strategy config: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Error deleting strategy config for {strategy_id}: {e}")
            return False

    def _get_default_config(self) -> dict[str, Any]:
        """Get default application configuration."""
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
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

    def _get_default_strategy_config(self) -> dict[str, Any]:
        """Get default strategy configuration."""
        return {
            "parameters": {},
            "version": 0,
            "source": "none",
            "is_override": False,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
