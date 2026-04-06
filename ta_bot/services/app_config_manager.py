"""
Application Configuration Manager.

Manages runtime configuration for the TA Bot application with:
- Dual database persistence (MongoDB primary, MySQL fallback)
- TTL-based caching for performance
- Full audit trail
- Configuration validation
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

try:
    from datetime import UTC
except ImportError:
    from datetime import timezone

    UTC = timezone.utc  # noqa: UP017
from typing import Any

from ta_bot.db.mongodb_client import MongoDBClient
from ta_bot.models.app_config import AppConfig, AppConfigAudit
from ta_bot.services.app_config_validator import validate_app_config
from ta_bot.services.data_manager_config_client import DataManagerConfigClient
from ta_bot.services.mysql_client import MySQLClient

logger = logging.getLogger(__name__)


class AppConfigManager:
    """
    Application configuration manager with dual persistence and caching.

    Configuration Resolution Priority:
    1. Cache (if not expired)
    2. MongoDB app config
    3. MySQL app config
    4. Defaults from Config class
    """

    def __init__(
        self,
        mongodb_client: MongoDBClient | None = None,
        mysql_client: MySQLClient | None = None,
        data_manager_client: DataManagerConfigClient | None = None,
        cache_ttl_seconds: int = 60,
    ):
        """
        Initialize application configuration manager.

        Args:
            mongodb_client: MongoDB client (will create if None) - DEPRECATED
            mysql_client: MySQL client (will create if None) - DEPRECATED
            data_manager_client: Data Manager client (preferred)
            cache_ttl_seconds: Cache TTL in seconds (default: 60)
        """
        self.mongodb_client = mongodb_client
        self.mysql_client = mysql_client
        self.data_manager_client = data_manager_client
        self.cache_ttl_seconds = cache_ttl_seconds
        self.audit_history_limit = 1000

        # Cache: (config, timestamp)
        self._cache: tuple[dict[str, Any], float] | None = None

        # Background tasks
        self._cache_refresh_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start the configuration manager and background tasks."""
        # Initialize database connections
        if self.mongodb_client:
            await self.mongodb_client.connect()

        if self.mysql_client:
            await self.mysql_client.connect()

        # Start cache refresh task
        self._running = True
        self._cache_refresh_task = asyncio.create_task(self._cache_refresh_loop())

        logger.info("Application configuration manager started")

    async def stop(self) -> None:
        """Stop the configuration manager and clean up."""
        self._running = False

        if self._cache_refresh_task:
            self._cache_refresh_task.cancel()
            try:
                await self._cache_refresh_task
            except asyncio.CancelledError:
                pass

        if self.mongodb_client:
            await self.mongodb_client.disconnect()

        if self.mysql_client:
            await self.mysql_client.disconnect()

        logger.info("Application configuration manager stopped")

    async def get_config(self) -> dict[str, Any]:
        """
        Get application configuration.

        Implements priority resolution:
        1. Check cache
        2. MongoDB config
        3. MySQL config
        4. Default config (from environment/hardcoded)

        Returns:
            Dictionary containing:
                - enabled_strategies: List of enabled strategy IDs
                - symbols: List of trading symbols
                - candle_periods: List of timeframes
                - min_confidence: Minimum confidence threshold
                - max_confidence: Maximum confidence threshold
                - max_positions: Maximum concurrent positions
                - position_sizes: Available position sizes
                - version: Config version
                - source: Where config came from
                - created_at: When created
                - updated_at: When last updated
        """
        start_time = time.time()

        # Check cache first
        cached = self._get_from_cache()
        if cached:
            cached["cache_hit"] = True
            cached["load_time_ms"] = (time.time() - start_time) * 1000
            return cached

        # Try Data Manager Service (preferred)
        if self.data_manager_client:
            try:
                config_doc = await self.data_manager_client.get_app_config()
                if config_doc and config_doc.get("version", 0) > 0:
                    result = self._doc_to_config_result(config_doc, "data_manager")
                    self._set_cache(result)
                    result["cache_hit"] = False
                    result["load_time_ms"] = (time.time() - start_time) * 1000
                    return result
            except Exception as e:
                logger.warning(f"Data Manager service unavailable: {e}")

        # Fallback to direct database access (deprecated)
        # Try MongoDB
        if self.mongodb_client and self.mongodb_client.is_connected:
            config_doc = await self.mongodb_client.get_app_config()
            if config_doc:
                result = self._doc_to_config_result(config_doc, "mongodb")
                self._set_cache(result)
                result["cache_hit"] = False
                result["load_time_ms"] = (time.time() - start_time) * 1000
                return result

        # Try MySQL
        if self.mysql_client:
            config_doc = await self._get_mysql_config()
            if config_doc:
                result = self._doc_to_config_result(config_doc, "mysql")
                self._set_cache(result)
                result["cache_hit"] = False
                result["load_time_ms"] = (time.time() - start_time) * 1000
                return result

        # Return defaults (should be provided by caller if no config exists)
        logger.warning("No application configuration found in database, using defaults")
        result = {
            "enabled_strategies": [],
            "symbols": [],
            "candle_periods": [],
            "min_confidence": 0.6,
            "max_confidence": 0.95,
            "max_positions": 10,
            "position_sizes": [100, 200, 500, 1000],
            "version": 0,
            "source": "default",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "cache_hit": False,
            "load_time_ms": (time.time() - start_time) * 1000,
        }
        return result

    async def set_config(
        self,
        config: dict[str, Any],
        changed_by: str,
        reason: str | None = None,
        validate_only: bool = False,
    ) -> tuple[bool, AppConfig | None, list[str]]:
        """
        Create or update application configuration.

        Implements dual persistence:
        1. Validate configuration
        2. Write to MongoDB (primary)
        3. Write to MySQL (fallback)
        4. Create audit record
        5. Invalidate cache

        Args:
            config: New configuration values
            changed_by: Who is making the change
            reason: Optional reason for the change
            validate_only: If True, only validate without saving

        Returns:
            Tuple of (success, config, errors)
        """
        # Validate configuration
        is_valid, errors = validate_app_config(config)
        if not is_valid:
            return False, None, errors

        if validate_only:
            return True, None, []

        # Get existing config for audit trail
        existing = await self.get_config()
        old_config = {
            k: v
            for k, v in existing.items()
            if k
            not in [
                "version",
                "source",
                "created_at",
                "updated_at",
                "cache_hit",
                "load_time_ms",
            ]
        }

        metadata = {
            "created_by": changed_by,
            "reason": reason,
            "updated_at": datetime.now(UTC).isoformat(),
        }

        config_id = None
        success = False

        # Try Data Manager Service (preferred)
        if self.data_manager_client:
            try:
                success = await self.data_manager_client.set_app_config(
                    config, changed_by, reason
                )
                if success:
                    config_id = "data_manager"
                    logger.info("Configuration updated via Data Manager service")
            except Exception as e:
                logger.error(f"Failed to update config via Data Manager: {e}")

        # Fallback to direct database access (deprecated)
        if not success:
            success_mongo = False
            success_mysql = False

            # Write to MongoDB (primary)
            if self.mongodb_client and self.mongodb_client.is_connected:
                try:
                    config_id = await self.mongodb_client.upsert_app_config(
                        config, metadata
                    )
                    success_mongo = config_id is not None
                except Exception as e:
                    logger.error(f"Failed to write app config to MongoDB: {e}")

            # Write to MySQL (fallback)
            if self.mysql_client:
                try:
                    success_mysql = await self._upsert_mysql_config(config, metadata)
                except Exception as e:
                    logger.error(f"Failed to write app config to MySQL: {e}")

            success = success_mongo or success_mysql

        if not success:
            return False, None, ["Failed to persist configuration to any service"]

        # Create audit record
        new_version = existing.get("version", 0) + 1
        action = "UPDATE" if existing.get("version", 0) > 0 else "CREATE"
        audit_data = {
            "config_id": config_id,
            "action": action,
            "old_config": old_config if action == "UPDATE" else None,
            "new_config": {
                **config,
                "version": new_version,
            },  # Include version in the snapshot
            "changed_by": changed_by,
            "reason": reason,
        }

        if self.mongodb_client and self.mongodb_client.is_connected:
            try:
                await self.mongodb_client.create_app_audit_record(audit_data)
            except Exception as e:
                logger.warning(f"Failed to create app config audit record: {e}")

        # Invalidate cache
        self._invalidate_cache()

        # Build response config
        app_config = AppConfig(
            id=config_id,
            enabled_strategies=config.get("enabled_strategies", []),
            symbols=config.get("symbols", []),
            candle_periods=config.get("candle_periods", []),
            min_confidence=config.get("min_confidence", 0.6),
            max_confidence=config.get("max_confidence", 0.95),
            max_positions=config.get("max_positions", 10),
            position_sizes=config.get("position_sizes", [100, 200, 500, 1000]),
            version=existing.get("version", 0) + 1,
            created_by=changed_by,
            metadata={"reason": reason} if reason else {},
        )

        logger.info(
            f"Application configuration {'updated' if action == 'UPDATE' else 'created'} by {changed_by}"
        )

        return True, app_config, []

    async def get_audit_history(self, limit: int = 100) -> list[AppConfigAudit]:
        """
        Get application configuration change history.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of audit records (most recent first)
        """
        return await self.get_audit_trail(limit)

    async def get_previous_config(self) -> dict[str, Any] | None:
        """
        Get the immediately preceding configuration version.

        Returns:
            Dictionary of configuration values or None if no history exists
        """
        history = await self.get_audit_history(limit=2)
        if len(history) < 1:
            return None

        # The first entry is the current config (if last action was UPDATE/CREATE)
        latest = history[0]
        if latest.action == "UPDATE" and latest.old_config:
            return latest.old_config

        if len(history) >= 2:
            return history[1].new_config

        return None

    async def get_config_by_version(self, version: int) -> dict[str, Any] | None:
        """
        Get a specific configuration version from audit history.

        Args:
            version: Version number to find

        Returns:
            Dictionary of configuration values or None if not found
        """
        if version < 1:
            return None

        # Query history for a record where new_config.version == target_version
        history = await self.get_audit_trail(limit=self.audit_history_limit)
        for record in history:
            # We now persist version in new_config during set_config
            if record.new_config and record.new_config.get("version") == version:
                return record.new_config

        return None

    async def get_config_by_id(self, audit_id: str) -> dict[str, Any] | None:
        """
        Get a specific configuration from a specific audit record.

        Args:
            audit_id: Audit record unique identifier

        Returns:
            Dictionary of configuration values or None if not found
        """
        history = await self.get_audit_trail(limit=self.audit_history_limit)
        for record in history:
            if record.id == audit_id:
                return record.new_config

        return None

    async def rollback_config(
        self,
        changed_by: str,
        target_version: int | None = None,
        rollback_id: str | None = None,
        reason: str | None = None,
    ) -> tuple[bool, AppConfig | None, list[str]]:
        """
        Rollback application configuration to a previous version.

        Args:
            changed_by: Who is performing the rollback
            target_version: Optional specific version to rollback to
            rollback_id: Optional specific audit ID to rollback to
            reason: Optional reason for the rollback

        Returns:
            Tuple of (success, config, errors)
        """
        # 1. Determine configuration to restore
        config_to_restore = None

        if rollback_id:
            config_to_restore = await self.get_config_by_id(rollback_id)
            if not config_to_restore:
                return (
                    False,
                    None,
                    [f"Configuration with ID {rollback_id} not found in history"],
                )
        elif target_version is not None:
            if target_version < 1:
                return False, None, ["Invalid version number (must be >= 1)"]
            config_to_restore = await self.get_config_by_version(target_version)
            if not config_to_restore:
                # If not found in history, try Data Manager fallback if available
                if self.data_manager_client:
                    try:
                        success = await self.data_manager_client.rollback_app_config(
                            changed_by=changed_by,
                            target_version=target_version,
                            reason=reason,
                        )
                        if success:
                            self._invalidate_cache()
                            result = await self.get_config()
                            return True, AppConfig(**result), []
                    except Exception:
                        pass
                return (
                    False,
                    None,
                    [f"Configuration version {target_version} not found in history"],
                )
        else:
            # Default to previous
            config_to_restore = await self.get_previous_config()
            if not config_to_restore:
                # If no previous found in history, try Data Manager fallback
                if self.data_manager_client:
                    try:
                        success = await self.data_manager_client.rollback_app_config(
                            changed_by=changed_by, reason=reason
                        )
                        if success:
                            self._invalidate_cache()
                            result = await self.get_config()
                            return True, AppConfig(**result), []
                    except Exception:
                        pass
                return False, None, ["No previous configuration found to rollback to"]

        # 2. Perform rollback using set_config
        # This handles validation, audit record creation, and cache invalidation
        rollback_reason = (
            reason
            or f"Rollback to {'version ' + str(target_version) if target_version is not None else ('ID ' + rollback_id if rollback_id else 'previous')}"
        )

        success, config, errors = await self.set_config(
            config=config_to_restore,
            changed_by=changed_by,
            reason=rollback_reason,
        )

        return success, config, errors

    async def get_audit_trail(self, limit: int = 100) -> list[AppConfigAudit]:
        """
        Get application configuration change history.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of audit records (most recent first)
        """
        if not self.mongodb_client or not self.mongodb_client.is_connected:
            return []

        try:
            records = await self.mongodb_client.get_app_audit_trail(limit)

            # Convert to Pydantic models
            audit_records = []
            for record in records:
                audit_records.append(
                    AppConfigAudit(
                        id=str(record.get("_id")),
                        config_id=record.get("config_id"),
                        action=record["action"],
                        old_config=record.get("old_config"),
                        new_config=record.get("new_config"),
                        changed_by=record["changed_by"],
                        changed_at=record["changed_at"],
                        reason=record.get("reason"),
                        metadata=record.get("metadata", {}),
                    )
                )

            return audit_records

        except Exception as e:
            logger.error(f"Failed to get app config audit trail: {e}")
            return []

    async def refresh_cache(self) -> None:
        """Force refresh of cached configuration."""
        self._invalidate_cache()
        logger.info("Application configuration cache cleared")

    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------

    def _get_from_cache(self) -> dict[str, Any] | None:
        """Get configuration from cache if not expired."""
        if self._cache is None:
            return None

        config, timestamp = self._cache
        if time.time() - timestamp > self.cache_ttl_seconds:
            # Expired
            self._cache = None
            return None

        return config.copy()

    def _set_cache(self, config: dict[str, Any]) -> None:
        """Set configuration in cache."""
        self._cache = (config.copy(), time.time())

    def _invalidate_cache(self) -> None:
        """Invalidate cache."""
        self._cache = None

    def _doc_to_config_result(self, doc: dict[str, Any], source: str) -> dict[str, Any]:
        """Convert database document to config result."""
        return {
            "enabled_strategies": doc.get("enabled_strategies", []),
            "symbols": doc.get("symbols", []),
            "candle_periods": doc.get("candle_periods", []),
            "min_confidence": doc.get("min_confidence", 0.6),
            "max_confidence": doc.get("max_confidence", 0.95),
            "max_positions": doc.get("max_positions", 10),
            "position_sizes": doc.get("position_sizes", [100, 200, 500, 1000]),
            "version": doc.get("version", 1),
            "source": source,
            "created_at": (
                doc.get("created_at", datetime.now(UTC)).isoformat()
                if isinstance(doc.get("created_at"), datetime)
                else doc.get("created_at", datetime.now(UTC).isoformat())
            ),
            "updated_at": (
                doc.get("updated_at", datetime.now(UTC)).isoformat()
                if isinstance(doc.get("updated_at"), datetime)
                else doc.get("updated_at", datetime.now(UTC).isoformat())
            ),
        }

    async def _cache_refresh_loop(self) -> None:
        """Background task to periodically refresh cache."""
        while self._running:
            try:
                await asyncio.sleep(self.cache_ttl_seconds)
                # Cache entries auto-expire, no action needed
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache refresh loop: {e}")

    # -------------------------------------------------------------------------
    # MySQL Helper Methods (Simplified - Real implementation would use MySQLClient)
    # -------------------------------------------------------------------------

    async def _get_mysql_config(self) -> dict[str, Any] | None:
        """Get config from MySQL."""
        # TODO: Implement MySQL query
        return None

    async def _upsert_mysql_config(
        self, config: dict[str, Any], metadata: dict[str, Any]
    ) -> bool:
        """Upsert config to MySQL."""
        # TODO: Implement MySQL upsert
        return False
