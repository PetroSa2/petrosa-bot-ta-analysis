"""
Strategy Configuration Manager.

Manages runtime configuration for trading strategies with:
- Dual database persistence (MongoDB primary, MySQL fallback)
- Configuration inheritance (global + per-symbol overrides)
- TTL-based caching for performance
- Full audit trail
- Automatic default persistence
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ta_bot.db.mongodb_client import MongoDBClient
from ta_bot.models.strategy_config import StrategyConfig, StrategyConfigAudit
from ta_bot.services.mysql_client import MySQLClient
from ta_bot.strategies.defaults import (
    get_strategy_defaults,
    get_strategy_metadata,
    list_all_strategies,
    validate_parameters,
)

logger = logging.getLogger(__name__)


class StrategyConfigManager:
    """
    Strategy configuration manager with dual persistence and caching.

    Configuration Resolution Priority:
    1. Cache (if not expired)
    2. MongoDB symbol-specific config
    3. MySQL symbol-specific config
    4. MongoDB global config
    5. MySQL global config
    6. Hardcoded defaults (auto-persisted to MongoDB)
    """

    def __init__(
        self,
        mongodb_client: Optional[MongoDBClient] = None,
        mysql_client: Optional[MySQLClient] = None,
        cache_ttl_seconds: int = 60,
    ):
        """
        Initialize configuration manager.

        Args:
            mongodb_client: MongoDB client (will create if None)
            mysql_client: MySQL client (will create if None)
            cache_ttl_seconds: Cache TTL in seconds (default: 60)
        """
        self.mongodb_client = mongodb_client
        self.mysql_client = mysql_client
        self.cache_ttl_seconds = cache_ttl_seconds

        # Cache: key = f"{strategy_id}:{symbol or 'global'}", value = (config, timestamp)
        self._cache: Dict[str, Tuple[Dict[str, Any], float]] = {}

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

        logger.info("Configuration manager started")

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

        logger.info("Configuration manager stopped")

    async def get_config(
        self, strategy_id: str, symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get configuration for a strategy.

        Implements priority resolution:
        1. Check cache
        2. MongoDB symbol-specific (if symbol provided)
        3. MySQL symbol-specific (if symbol provided)
        4. MongoDB global
        5. MySQL global
        6. Hardcoded defaults (auto-persist to MongoDB)

        Args:
            strategy_id: Strategy identifier
            symbol: Optional trading symbol for symbol-specific config

        Returns:
            Dictionary containing:
                - parameters: Dict of parameter values
                - version: Config version
                - source: Where config came from
                - is_override: Whether this is a symbol-specific override
        """
        start_time = time.time()

        # Check cache first
        cache_key = self._make_cache_key(strategy_id, symbol)
        cached = self._get_from_cache(cache_key)
        if cached:
            cached["cache_hit"] = True
            cached["load_time_ms"] = (time.time() - start_time) * 1000
            return cached

        # Try MongoDB symbol-specific
        if symbol and self.mongodb_client and self.mongodb_client.is_connected:
            config_doc = await self.mongodb_client.get_symbol_config(
                strategy_id, symbol
            )
            if config_doc:
                result = self._doc_to_config_result(config_doc, "mongodb", True)
                self._set_cache(cache_key, result)
                result["cache_hit"] = False
                result["load_time_ms"] = (time.time() - start_time) * 1000
                return result

        # Try MySQL symbol-specific
        if symbol and self.mysql_client:
            config_doc = await self._get_mysql_symbol_config(strategy_id, symbol)
            if config_doc:
                result = self._doc_to_config_result(config_doc, "mysql", True)
                self._set_cache(cache_key, result)
                result["cache_hit"] = False
                result["load_time_ms"] = (time.time() - start_time) * 1000
                return result

        # Try MongoDB global
        if self.mongodb_client and self.mongodb_client.is_connected:
            config_doc = await self.mongodb_client.get_global_config(strategy_id)
            if config_doc:
                result = self._doc_to_config_result(config_doc, "mongodb", False)
                self._set_cache(cache_key, result)
                result["cache_hit"] = False
                result["load_time_ms"] = (time.time() - start_time) * 1000
                return result

        # Try MySQL global
        if self.mysql_client:
            config_doc = await self._get_mysql_global_config(strategy_id)
            if config_doc:
                result = self._doc_to_config_result(config_doc, "mysql", False)
                self._set_cache(cache_key, result)
                result["cache_hit"] = False
                result["load_time_ms"] = (time.time() - start_time) * 1000
                return result

        # Fall back to hardcoded defaults and auto-persist
        defaults = get_strategy_defaults(strategy_id)
        if defaults:
            # Auto-persist defaults to MongoDB (best effort, no error if fails)
            if self.mongodb_client and self.mongodb_client.is_connected:
                try:
                    await self.mongodb_client.upsert_global_config(
                        strategy_id,
                        defaults,
                        {
                            "created_by": "system_default",
                            "auto_persisted": True,
                            "persisted_at": datetime.utcnow().isoformat(),
                        },
                    )
                    logger.info(f"Auto-persisted default config for {strategy_id}")
                except Exception as e:
                    logger.warning(
                        f"Failed to auto-persist defaults for {strategy_id}: {e}"
                    )

            result = {
                "parameters": defaults,
                "version": 1,
                "source": "default",
                "is_override": False,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "cache_hit": False,
                "load_time_ms": (time.time() - start_time) * 1000,
            }
            self._set_cache(cache_key, result)
            return result

        # No config found anywhere
        logger.warning(f"No configuration found for strategy: {strategy_id}")
        return {
            "parameters": {},
            "version": 0,
            "source": "none",
            "is_override": False,
            "cache_hit": False,
            "load_time_ms": (time.time() - start_time) * 1000,
        }

    async def set_config(
        self,
        strategy_id: str,
        parameters: Dict[str, Any],
        changed_by: str,
        symbol: Optional[str] = None,
        reason: Optional[str] = None,
        validate_only: bool = False,
    ) -> Tuple[bool, Optional[StrategyConfig], List[str]]:
        """
        Create or update configuration.

        Implements dual persistence:
        1. Write to MongoDB (primary)
        2. Write to MySQL (fallback)
        3. Create audit record
        4. Invalidate cache

        Args:
            strategy_id: Strategy identifier
            parameters: New parameter values
            changed_by: Who is making the change
            symbol: Optional symbol for symbol-specific config
            reason: Optional reason for the change
            validate_only: If True, only validate without saving

        Returns:
            Tuple of (success, config, errors)
        """
        # Validate parameters
        is_valid, errors = validate_parameters(strategy_id, parameters)
        if not is_valid:
            return False, None, errors

        if validate_only:
            return True, None, []

        # Get existing config for audit trail
        existing = await self.get_config(strategy_id, symbol)
        old_parameters = existing.get("parameters", {})

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
                if symbol:
                    config_id = await self.mongodb_client.upsert_symbol_config(
                        strategy_id, symbol, parameters, metadata
                    )
                else:
                    config_id = await self.mongodb_client.upsert_global_config(
                        strategy_id, parameters, metadata
                    )
                success_mongo = config_id is not None
            except Exception as e:
                logger.error(f"Failed to write config to MongoDB: {e}")

        # Write to MySQL (fallback)
        if self.mysql_client:
            try:
                if symbol:
                    success_mysql = await self._upsert_mysql_symbol_config(
                        strategy_id, symbol, parameters, metadata
                    )
                else:
                    success_mysql = await self._upsert_mysql_global_config(
                        strategy_id, parameters, metadata
                    )
            except Exception as e:
                logger.error(f"Failed to write config to MySQL: {e}")

        if not success_mongo and not success_mysql:
            return False, None, ["Failed to persist configuration to any database"]

        # Create audit record
        action = "UPDATE" if old_parameters else "CREATE"
        audit_data = {
            "config_id": config_id,
            "strategy_id": strategy_id,
            "symbol": symbol,
            "action": action,
            "old_parameters": old_parameters if action == "UPDATE" else None,
            "new_parameters": parameters,
            "changed_by": changed_by,
            "reason": reason,
        }

        if self.mongodb_client and self.mongodb_client.is_connected:
            try:
                await self.mongodb_client.create_audit_record(audit_data)
            except Exception as e:
                logger.warning(f"Failed to create audit record: {e}")

        # Invalidate cache
        cache_key = self._make_cache_key(strategy_id, symbol)
        self._invalidate_cache(cache_key)

        # Build response config
        config = StrategyConfig(
            id=config_id,
            strategy_id=strategy_id,
            symbol=symbol,
            parameters=parameters,
            version=existing.get("version", 0) + 1,
            created_by=changed_by,
            metadata={"reason": reason} if reason else {},
        )

        logger.info(
            f"Configuration {'updated' if action == 'UPDATE' else 'created'}: "
            f"{strategy_id}" + (f"/{symbol}" if symbol else "")
        )

        return True, config, []

    async def delete_config(
        self,
        strategy_id: str,
        changed_by: str,
        symbol: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Delete configuration.

        Args:
            strategy_id: Strategy identifier
            changed_by: Who is deleting the config
            symbol: Optional symbol for symbol-specific config
            reason: Optional reason for deletion

        Returns:
            Tuple of (success, errors)
        """
        # Get existing config for audit trail
        existing = await self.get_config(strategy_id, symbol)
        old_parameters = existing.get("parameters", {})

        success_mongo = False
        success_mysql = False

        # Delete from MongoDB
        if self.mongodb_client and self.mongodb_client.is_connected:
            try:
                if symbol:
                    success_mongo = await self.mongodb_client.delete_symbol_config(
                        strategy_id, symbol
                    )
                else:
                    success_mongo = await self.mongodb_client.delete_global_config(
                        strategy_id
                    )
            except Exception as e:
                logger.error(f"Failed to delete config from MongoDB: {e}")

        # Delete from MySQL
        if self.mysql_client:
            try:
                if symbol:
                    success_mysql = await self._delete_mysql_symbol_config(
                        strategy_id, symbol
                    )
                else:
                    success_mysql = await self._delete_mysql_global_config(strategy_id)
            except Exception as e:
                logger.error(f"Failed to delete config from MySQL: {e}")

        if not success_mongo and not success_mysql:
            return False, ["Failed to delete configuration from any database"]

        # Create audit record
        audit_data = {
            "strategy_id": strategy_id,
            "symbol": symbol,
            "action": "DELETE",
            "old_parameters": old_parameters,
            "new_parameters": None,
            "changed_by": changed_by,
            "reason": reason,
        }

        if self.mongodb_client and self.mongodb_client.is_connected:
            try:
                await self.mongodb_client.create_audit_record(audit_data)
            except Exception as e:
                logger.warning(f"Failed to create audit record: {e}")

        # Invalidate cache
        cache_key = self._make_cache_key(strategy_id, symbol)
        self._invalidate_cache(cache_key)

        logger.info(
            f"Configuration deleted: {strategy_id}" + (f"/{symbol}" if symbol else "")
        )

        return True, []

    async def get_audit_trail(
        self, strategy_id: str, symbol: Optional[str] = None, limit: int = 100
    ) -> List[StrategyConfigAudit]:
        """
        Get configuration change history.

        Args:
            strategy_id: Strategy identifier
            symbol: Optional symbol filter
            limit: Maximum number of records

        Returns:
            List of audit records
        """
        if not self.mongodb_client or not self.mongodb_client.is_connected:
            return []

        try:
            records = await self.mongodb_client.get_audit_trail(
                strategy_id, symbol, limit
            )

            # Convert to Pydantic models
            audit_records = []
            for record in records:
                audit_records.append(
                    StrategyConfigAudit(
                        id=str(record.get("_id")),
                        config_id=record.get("config_id"),
                        strategy_id=record["strategy_id"],
                        symbol=record.get("symbol"),
                        action=record["action"],
                        old_parameters=record.get("old_parameters"),
                        new_parameters=record.get("new_parameters"),
                        changed_by=record["changed_by"],
                        changed_at=record["changed_at"],
                        reason=record.get("reason"),
                    )
                )

            return audit_records

        except Exception as e:
            logger.error(f"Failed to get audit trail: {e}")
            return []

    async def list_strategies(self) -> List[Dict[str, Any]]:
        """
        List all strategies with their configuration status.

        Returns:
            List of strategy info dictionaries
        """
        all_strategies = list_all_strategies()
        result = []

        for strategy_id in all_strategies:
            metadata = get_strategy_metadata(strategy_id)
            defaults = get_strategy_defaults(strategy_id)

            # Check if has global config
            has_global = False
            if self.mongodb_client and self.mongodb_client.is_connected:
                config = await self.mongodb_client.get_global_config(strategy_id)
                has_global = config is not None

            # Get symbol overrides
            symbol_overrides = []
            if self.mongodb_client and self.mongodb_client.is_connected:
                symbol_overrides = await self.mongodb_client.list_symbol_overrides(
                    strategy_id
                )

            result.append(
                {
                    "strategy_id": strategy_id,
                    "name": metadata.get("name", strategy_id),
                    "description": metadata.get("description", ""),
                    "has_global_config": has_global,
                    "symbol_overrides": symbol_overrides,
                    "parameter_count": len(defaults),
                }
            )

        return result

    async def refresh_cache(self) -> None:
        """Force refresh of all cached configurations."""
        self._cache.clear()
        logger.info("Configuration cache cleared")

    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------

    def _make_cache_key(self, strategy_id: str, symbol: Optional[str]) -> str:
        """Make cache key from strategy_id and symbol."""
        return f"{strategy_id}:{symbol or 'global'}"

    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get configuration from cache if not expired."""
        if key not in self._cache:
            return None

        config, timestamp = self._cache[key]
        if time.time() - timestamp > self.cache_ttl_seconds:
            # Expired
            del self._cache[key]
            return None

        return config.copy()

    def _set_cache(self, key: str, config: Dict[str, Any]) -> None:
        """Set configuration in cache."""
        self._cache[key] = (config.copy(), time.time())

    def _invalidate_cache(self, key: str) -> None:
        """Invalidate specific cache entry."""
        if key in self._cache:
            del self._cache[key]

    def _doc_to_config_result(
        self, doc: Dict[str, Any], source: str, is_override: bool
    ) -> Dict[str, Any]:
        """Convert database document to config result."""
        return {
            "parameters": doc.get("parameters", {}),
            "version": doc.get("version", 1),
            "source": source,
            "is_override": is_override,
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

    async def _get_mysql_global_config(
        self, strategy_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get global config from MySQL."""
        # TODO: Implement MySQL query
        return None

    async def _get_mysql_symbol_config(
        self, strategy_id: str, symbol: str
    ) -> Optional[Dict[str, Any]]:
        """Get symbol config from MySQL."""
        # TODO: Implement MySQL query
        return None

    async def _upsert_mysql_global_config(
        self, strategy_id: str, parameters: Dict[str, Any], metadata: Dict[str, Any]
    ) -> bool:
        """Upsert global config to MySQL."""
        # TODO: Implement MySQL upsert
        return False

    async def _upsert_mysql_symbol_config(
        self,
        strategy_id: str,
        symbol: str,
        parameters: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> bool:
        """Upsert symbol config to MySQL."""
        # TODO: Implement MySQL upsert
        return False

    async def _delete_mysql_global_config(self, strategy_id: str) -> bool:
        """Delete global config from MySQL."""
        # TODO: Implement MySQL delete
        return False

    async def _delete_mysql_symbol_config(self, strategy_id: str, symbol: str) -> bool:
        """Delete symbol config from MySQL."""
        # TODO: Implement MySQL delete
        return False
