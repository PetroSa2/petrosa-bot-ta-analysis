"""
Strategy Configuration Manager.

Manages runtime configuration for trading strategies with:
 - Data-manager gateway persistence
- Configuration inheritance (global + per-symbol overrides)
- TTL-based caching for performance
- Full audit trail
- Automatic default persistence
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

from petrosa_otel import get_meter

from ta_bot.models.strategy_config import StrategyConfig, StrategyConfigAudit
from ta_bot.services.strategy_config_store import DataManagerStrategyConfigStore
from ta_bot.strategies.defaults import (
    get_strategy_defaults,
    get_strategy_metadata,
    list_all_strategies,
    validate_parameters,
)

logger = logging.getLogger(__name__)


class StrategyConfigManager:
    """
    Strategy configuration manager with data-manager persistence and caching.

    Configuration Resolution Priority:
    1. Cache (if not expired)
    2. Data-manager symbol-specific config
    3. Data-manager global config
    4. Hardcoded defaults (auto-persisted through data-manager)
    """

    def __init__(
        self,
        store: DataManagerStrategyConfigStore,
        cache_ttl_seconds: int = 60,
    ):
        """
        Initialize configuration manager.

        Args:
            store: Data-manager-backed strategy configuration store
            cache_ttl_seconds: Cache TTL in seconds (default: 60)
        """
        self.store = store
        self.cache_ttl_seconds = cache_ttl_seconds

        # Cache: key = f"{strategy_id}:{symbol or 'global'}", value = (config, timestamp)
        self._cache: dict[str, tuple[dict[str, Any], float]] = {}

        # Background tasks
        self._cache_refresh_task: asyncio.Task | None = None
        self._running = False

        # Initialize OpenTelemetry metrics
        meter = get_meter("ta_bot.services.config_manager")

        # Counter for configuration changes (by strategy, action, symbol)
        self.config_change_counter = meter.create_counter(
            name="ta_bot.config.changes",
            description="Number of configuration changes",
            unit="1",
        )

    async def start(self) -> None:
        """Start the configuration manager and background tasks."""
        # Initialize database connections
        await self.store.connect()

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

        await self.store.disconnect()

        logger.info("Configuration manager stopped")

    async def get_config(
        self, strategy_id: str, symbol: str | None = None
    ) -> dict[str, Any]:
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

        # Try data-manager symbol-specific
        if symbol and self.store.is_connected:
            config_doc = await self.store.get_symbol_config(
                strategy_id, symbol
            )
            if config_doc:
                result = self._doc_to_config_result(config_doc, "mongodb", True)
                self._set_cache(cache_key, result)
                result["cache_hit"] = False
                result["load_time_ms"] = (time.time() - start_time) * 1000
                return result

        # Try data-manager global
        if self.store.is_connected:
            config_doc = await self.store.get_global_config(strategy_id)
            if config_doc:
                result = self._doc_to_config_result(config_doc, "mongodb", False)
                self._set_cache(cache_key, result)
                result["cache_hit"] = False
                result["load_time_ms"] = (time.time() - start_time) * 1000
                return result

        # Fall back to hardcoded defaults and auto-persist
        defaults = get_strategy_defaults(strategy_id)
        if defaults:
            # Auto-persist defaults through data-manager (best effort)
            if self.store.is_connected:
                try:
                    await self.store.upsert_global_config(
                        strategy_id,
                        defaults,
                        {
                            "created_by": "system_default",
                            "auto_persisted": True,
                            "persisted_at": datetime.now(UTC).isoformat(),
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
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
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
        parameters: dict[str, Any],
        changed_by: str,
        symbol: str | None = None,
        reason: str | None = None,
        validate_only: bool = False,
    ) -> tuple[bool, StrategyConfig | None, list[str]]:
        """
        Create or update configuration.

        Persist through data-manager and create its audit record.
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
            "updated_at": datetime.now(UTC).isoformat(),
        }

        config_id = None
        success_store = False
        if self.store.is_connected:
            try:
                if symbol:
                    config_id = await self.store.upsert_symbol_config(
                        strategy_id, symbol, parameters, metadata
                    )
                else:
                    config_id = await self.store.upsert_global_config(
                        strategy_id, parameters, metadata
                    )
                success_store = config_id is not None
            except Exception as e:
                logger.error(f"Failed to write config through data-manager: {e}")

        if not success_store:
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

        if self.store.is_connected:
            try:
                await self.store.create_audit_record(audit_data)
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

        # Record configuration change metric
        self.config_change_counter.add(
            1,
            {
                "strategy_id": strategy_id,
                "action": action.lower(),
                "scope": "symbol" if symbol else "global",
                "symbol": symbol or "global",
                "changed_by": changed_by,
            },
        )

        return True, config, []

    async def rollback_config(
        self,
        strategy_id: str,
        changed_by: str,
        symbol: str | None = None,
        target_version: int | None = None,
        reason: str | None = None,
    ) -> tuple[bool, StrategyConfig | None, list[str]]:
        """
        Rollback strategy configuration to a previous version.

        Args:
            strategy_id: Strategy identifier
            changed_by: Who is performing the rollback
            symbol: Optional symbol for symbol-specific config
            target_version: Optional specific version to rollback to
            reason: Optional reason for the rollback

        Returns:
            Tuple of (success, config, errors)
        """
        if self.store.is_connected:
            try:
                success = await self.store.rollback_strategy_config(
                    strategy_id, changed_by, symbol, target_version, reason
                )
                if success:
                    # Invalidate cache
                    cache_key = self._make_cache_key(strategy_id, symbol)
                    self._invalidate_cache(cache_key)
                    # Get the new config
                    result = await self.get_config(strategy_id, symbol)
                    config = StrategyConfig(
                        strategy_id=strategy_id,
                        symbol=symbol,
                        parameters=result.get("parameters", {}),
                        version=result.get("version", 0),
                        created_by=changed_by,
                    )
                    return True, config, []
                else:
                    return False, None, ["Rollback failed in Data Manager service"]
            except Exception as e:
                logger.error(f"Failed to rollback via Data Manager: {e}")
                return False, None, [str(e)]

        return False, None, ["Data Manager service is not connected"]

    async def delete_config(
        self,
        strategy_id: str,
        changed_by: str,
        symbol: str | None = None,
        reason: str | None = None,
    ) -> tuple[bool, list[str]]:
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

        success_store = False
        if self.store.is_connected:
            try:
                if symbol:
                    success_store = await self.store.delete_symbol_config(
                        strategy_id, symbol
                    )
                else:
                    success_store = await self.store.delete_global_config(
                        strategy_id
                    )
            except Exception as e:
                logger.error(f"Failed to delete config from MongoDB: {e}")

        if not success_store:
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

        if self.store.is_connected:
            try:
                await self.store.create_audit_record(audit_data)
            except Exception as e:
                logger.warning(f"Failed to create audit record: {e}")

        # Invalidate cache
        cache_key = self._make_cache_key(strategy_id, symbol)
        self._invalidate_cache(cache_key)

        logger.info(
            f"Configuration deleted: {strategy_id}" + (f"/{symbol}" if symbol else "")
        )

        # Record configuration change metric
        self.config_change_counter.add(
            1,
            {
                "strategy_id": strategy_id,
                "action": "delete",
                "scope": "symbol" if symbol else "global",
                "symbol": symbol or "global",
                "changed_by": changed_by,
            },
        )

        return True, []

    async def get_audit_trail(
        self, strategy_id: str, symbol: str | None = None, limit: int = 100
    ) -> list[StrategyConfigAudit]:
        """
        Get configuration change history.

        Args:
            strategy_id: Strategy identifier
            symbol: Optional symbol filter
            limit: Maximum number of records

        Returns:
            List of audit records
        """
        if not self.store.is_connected:
            return []

        try:
            records = await self.store.get_audit_trail(
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

    async def list_strategies(self) -> list[dict[str, Any]]:
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
            if self.store.is_connected:
                config = await self.store.get_global_config(strategy_id)
                has_global = config is not None

            # Get symbol overrides
            symbol_overrides = []
            if self.store.is_connected:
                symbol_overrides = await self.store.list_symbol_overrides(
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

    def _make_cache_key(self, strategy_id: str, symbol: str | None) -> str:
        """Make cache key from strategy_id and symbol."""
        return f"{strategy_id}:{symbol or 'global'}"

    def _get_from_cache(self, key: str) -> dict[str, Any] | None:
        """Get configuration from cache if not expired."""
        if key not in self._cache:
            return None

        config, timestamp = self._cache[key]
        if time.time() - timestamp > self.cache_ttl_seconds:
            # Expired
            del self._cache[key]
            return None

        return config.copy()

    def _set_cache(self, key: str, config: dict[str, Any]) -> None:
        """Set configuration in cache."""
        self._cache[key] = (config.copy(), time.time())

    def _invalidate_cache(self, key: str) -> None:
        """Invalidate specific cache entry."""
        if key in self._cache:
            del self._cache[key]

    def _doc_to_config_result(
        self, doc: dict[str, Any], source: str, is_override: bool
    ) -> dict[str, Any]:
        """Convert database document to config result."""
        return {
            "parameters": doc.get("parameters", {}),
            "version": doc.get("version", 1),
            "source": source,
            "is_override": is_override,
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
