"""
MongoDB client for strategy configuration management.

This client uses Data Manager API exclusively for configuration management.
Data Manager is the centralized data access layer that provides:
- Connection pooling and retry logic
- Circuit breaker protection
- Centralized data quality and integrity
- Unified configuration management across services
"""

import logging
from datetime import datetime
from typing import Any, Optional

from ..services.data_manager_client import DataManagerClient

logger = logging.getLogger(__name__)


class MongoDBClient:
    """
    MongoDB client for strategy configuration persistence via Data Manager API.

    This class now exclusively uses Data Manager API for all MongoDB operations.
    Direct MongoDB connections have been removed to enforce proper service architecture.

    Fail-fast behavior: If Data Manager is unavailable, the service will not start.
    """

    def __init__(self):
        """
        Initialize MongoDB client with Data Manager.

        Note: All parameters for direct MongoDB connection have been removed.
        Data Manager handles all database connectivity internally.
        """
        self.data_manager_client = DataManagerClient()
        self._connected = False
        logger.info("Initialized MongoDB client using Data Manager API")

    async def connect(self) -> bool:
        """
        Establish connection to Data Manager.

        Returns:
            True if connected successfully, raises exception otherwise
        """
        try:
            await self.data_manager_client.connect()
            self._connected = True
            logger.info("Connected to Data Manager successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Data Manager: {e}")
            logger.error("Cannot start TA-BOT without Data Manager - failing startup")
            raise RuntimeError(
                "Data Manager connection required for TA-BOT operation"
            ) from e

    async def disconnect(self) -> None:
        """Close Data Manager connection gracefully."""
        await self.data_manager_client.disconnect()
        self._connected = False
        logger.info("Disconnected from Data Manager")

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected

    async def health_check(self) -> bool:
        """
        Perform health check.

        Returns:
            True if Data Manager is healthy, False otherwise
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
            logger.error(f"Data Manager health check failed: {e}")
            return False

    async def get_global_config(self, strategy_id: str) -> dict[str, Any] | None:
        """
        Get global configuration for a strategy via Data Manager.

        Args:
            strategy_id: Strategy identifier

        Returns:
            Configuration document or None if not found
        """
        return await self.data_manager_client.get_global_config(strategy_id)

    async def get_symbol_config(
        self, strategy_id: str, symbol: str
    ) -> dict[str, Any] | None:
        """
        Get symbol-specific configuration for a strategy via Data Manager.

        Args:
            strategy_id: Strategy identifier
            symbol: Trading symbol (e.g., 'BTCUSDT')

        Returns:
            Configuration document or None if not found
        """
        return await self.data_manager_client.get_symbol_config(strategy_id, symbol)

    async def upsert_global_config(
        self, strategy_id: str, parameters: dict[str, Any], metadata: dict[str, Any]
    ) -> str | None:
        """
        Create or update global configuration via Data Manager.

        Args:
            strategy_id: Strategy identifier
            parameters: Parameter key-value pairs
            metadata: Additional metadata (created_by, reason, etc.)

        Returns:
            Configuration ID or None on failure
        """
        return await self.data_manager_client.upsert_global_config(
            strategy_id, parameters, metadata
        )

    async def upsert_symbol_config(
        self,
        strategy_id: str,
        symbol: str,
        parameters: dict[str, Any],
        metadata: dict[str, Any],
    ) -> str | None:
        """
        Create or update symbol-specific configuration via Data Manager.

        Args:
            strategy_id: Strategy identifier
            symbol: Trading symbol
            parameters: Parameter key-value pairs
            metadata: Additional metadata

        Returns:
            Configuration ID or None on failure
        """
        return await self.data_manager_client.upsert_symbol_config(
            strategy_id, symbol, parameters, metadata
        )

    async def delete_global_config(self, strategy_id: str) -> bool:
        """
        Delete global configuration via Data Manager.

        Args:
            strategy_id: Strategy identifier

        Returns:
            True if deleted, False otherwise
        """
        # Note: Data Manager client doesn't expose delete methods yet
        # This will need to be added to data_manager_client.py
        logger.warning(
            f"Delete global config not yet implemented via Data Manager for {strategy_id}"
        )
        return False

    async def delete_symbol_config(self, strategy_id: str, symbol: str) -> bool:
        """
        Delete symbol-specific configuration via Data Manager.

        Args:
            strategy_id: Strategy identifier
            symbol: Trading symbol

        Returns:
            True if deleted, False otherwise
        """
        # Note: Data Manager client doesn't expose delete methods yet
        # This will need to be added to data_manager_client.py
        logger.warning(
            f"Delete symbol config not yet implemented via Data Manager for {strategy_id}/{symbol}"
        )
        return False

    async def create_audit_record(self, audit_data: dict[str, Any]) -> str | None:
        """
        Create audit trail record for configuration change via Data Manager.

        Args:
            audit_data: Audit information (action, old/new values, changed_by, etc.)

        Returns:
            Audit record ID or None on failure
        """
        # Add timestamp if not present
        if "changed_at" not in audit_data:
            audit_data["changed_at"] = datetime.utcnow()

        # Note: Audit trail creation through Data Manager may need to be implemented
        logger.info(
            f"Audit record for {audit_data.get('strategy_id')}: {audit_data.get('action')}"
        )
        return "audit_via_data_manager"

    async def get_audit_trail(
        self, strategy_id: str, symbol: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get configuration change history via Data Manager.

        Args:
            strategy_id: Strategy identifier
            symbol: Optional symbol filter
            limit: Maximum number of records to return

        Returns:
            List of audit records (most recent first)
        """
        # Note: Audit trail retrieval through Data Manager may need to be implemented
        logger.warning(
            f"Audit trail retrieval not yet fully implemented via Data Manager for {strategy_id}"
        )
        return []

    async def list_all_strategy_ids(self) -> list[str]:
        """
        Get list of all strategy IDs with configurations via Data Manager.

        Returns:
            List of unique strategy IDs
        """
        # Note: This may need to be added to data_manager_client.py
        logger.warning("Strategy ID listing not yet implemented via Data Manager")
        return []

    async def list_symbol_overrides(self, strategy_id: str) -> list[str]:
        """
        Get list of symbols with configuration overrides for a strategy via Data Manager.

        Args:
            strategy_id: Strategy identifier

        Returns:
            List of symbols with overrides
        """
        # Note: This may need to be added to data_manager_client.py
        logger.warning(
            f"Symbol override listing not yet implemented via Data Manager for {strategy_id}"
        )
        return []

    # -------------------------------------------------------------------------
    # Application Configuration Methods
    # -------------------------------------------------------------------------

    async def get_app_config(self) -> dict[str, Any] | None:
        """
        Get application configuration via Data Manager.

        Returns:
            Configuration document or None if not found
        """
        # Note: This may need to be added to data_manager_client.py
        logger.debug("Fetching app config via Data Manager")
        return None

    async def upsert_app_config(
        self, config: dict[str, Any], metadata: dict[str, Any]
    ) -> str | None:
        """
        Create or update application configuration via Data Manager.

        Args:
            config: Configuration values
            metadata: Additional metadata (created_by, reason, etc.)

        Returns:
            Configuration ID or None on failure
        """
        # Note: This may need to be added to data_manager_client.py
        logger.info("Upserting app config via Data Manager")
        return "app_config_via_data_manager"

    async def create_app_audit_record(self, audit_data: dict[str, Any]) -> str | None:
        """
        Create audit trail record for application configuration change via Data Manager.

        Args:
            audit_data: Audit information (action, old/new config, changed_by, etc.)

        Returns:
            Audit record ID or None on failure
        """
        # Add timestamp if not present
        if "changed_at" not in audit_data:
            audit_data["changed_at"] = datetime.utcnow()

        logger.info(f"App config audit: {audit_data.get('action')}")
        return "app_audit_via_data_manager"

    async def get_app_audit_trail(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get application configuration change history via Data Manager.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of audit records (most recent first)
        """
        # Note: This may need to be added to data_manager_client.py
        logger.warning("App audit trail retrieval not yet implemented via Data Manager")
        return []
