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
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ta_bot.db.mongodb_client import MongoDBClient
from ta_bot.models.app_config import AppConfig, AppConfigAudit
from ta_bot.services.app_config_validator import validate_app_config
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
        mongodb_client: Optional[MongoDBClient] = None,
        mysql_client: Optional[MySQLClient] = None,
        cache_ttl_seconds: int = 60,
    ):
        """
        Initialize application configuration manager.

        Args:
            mongodb_client: MongoDB client (will create if None)
            mysql_client: MySQL client (will create if None)
            cache_ttl_seconds: Cache TTL in seconds (default: 60)
        """
        self.mongodb_client = mongodb_client
        self.mysql_client = mysql_client
        self.cache_ttl_seconds = cache_ttl_seconds

        # Cache: (config, timestamp)
        self._cache: Optional[Tuple[Dict[str, Any], float]] = None

        # Background tasks
        self._cache_refresh_task: Optional[asyncio.Task] = None
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

    async def get_config(self) -> Dict[str, Any]:
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
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "cache_hit": False,
            "load_time_ms": (time.time() - start_time) * 1000,
        }
        return result

    async def set_config(
        self,
        config: Dict[str, Any],
        changed_by: str,
        reason: Optional[str] = None,
        validate_only: bool = False,
    ) -> Tuple[bool, Optional[AppConfig], List[str]]:
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
            "updated_at": datetime.utcnow().isoformat(),
        }

        config_id = None
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

        if not success_mongo and not success_mysql:
            return False, None, ["Failed to persist configuration to any database"]

        # Create audit record
        action = "UPDATE" if existing.get("version", 0) > 0 else "CREATE"
        audit_data = {
            "config_id": config_id,
            "action": action,
            "old_config": old_config if action == "UPDATE" else None,
            "new_config": config,
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

    async def get_audit_trail(self, limit: int = 100) -> List[AppConfigAudit]:
        """
        Get application configuration change history.

        Args:
            limit: Maximum number of records

        Returns:
            List of audit records
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

    def _get_from_cache(self) -> Optional[Dict[str, Any]]:
        """Get configuration from cache if not expired."""
        if self._cache is None:
            return None

        config, timestamp = self._cache
        if time.time() - timestamp > self.cache_ttl_seconds:
            # Expired
            self._cache = None
            return None

        return config.copy()

    def _set_cache(self, config: Dict[str, Any]) -> None:
        """Set configuration in cache."""
        self._cache = (config.copy(), time.time())

    def _invalidate_cache(self) -> None:
        """Invalidate cache."""
        self._cache = None

    def _doc_to_config_result(self, doc: Dict[str, Any], source: str) -> Dict[str, Any]:
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
            "created_at": doc.get("created_at", datetime.utcnow()).isoformat()
            if isinstance(doc.get("created_at"), datetime)
            else doc.get("created_at", datetime.utcnow().isoformat()),
            "updated_at": doc.get("updated_at", datetime.utcnow()).isoformat()
            if isinstance(doc.get("updated_at"), datetime)
            else doc.get("updated_at", datetime.utcnow().isoformat()),
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

    async def _get_mysql_config(self) -> Optional[Dict[str, Any]]:
        """Get config from MySQL."""
        # TODO: Implement MySQL query
        return None

    async def _upsert_mysql_config(
        self, config: Dict[str, Any], metadata: Dict[str, Any]
    ) -> bool:
        """Upsert config to MySQL."""
        # TODO: Implement MySQL upsert
        return False
