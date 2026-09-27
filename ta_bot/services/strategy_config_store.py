"""Data-manager-backed strategy configuration persistence."""

from typing import Any

from ta_bot.services.data_manager_config_client import DataManagerConfigClient


class DataManagerStrategyConfigStore:
    """Store strategy configuration exclusively through data-manager."""

    def __init__(self, client: DataManagerConfigClient | None = None):
        self.client = client or DataManagerConfigClient()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        try:
            await self.client.connect()
            self._connected = True
        except Exception:
            self._connected = False
        return self._connected

    async def disconnect(self) -> None:
        await self.client.disconnect()
        self._connected = False

    async def get_global_config(self, strategy_id: str) -> dict[str, Any] | None:
        try:
            return await self.client.get_strategy_config_record(strategy_id)
        except Exception:
            return None

    async def get_symbol_config(
        self, strategy_id: str, symbol: str
    ) -> dict[str, Any] | None:
        try:
            return await self.client.get_strategy_config_record(strategy_id, symbol)
        except Exception:
            return None

    async def upsert_global_config(
        self, strategy_id: str, parameters: dict[str, Any], metadata: dict[str, Any]
    ) -> str | None:
        ok = await self.client.set_strategy_config(
            strategy_id,
            parameters,
            metadata.get("created_by", "system"),
            reason=metadata.get("reason"),
        )
        return strategy_id if ok else None

    async def upsert_symbol_config(
        self,
        strategy_id: str,
        symbol: str,
        parameters: dict[str, Any],
        metadata: dict[str, Any],
    ) -> str | None:
        ok = await self.client.set_strategy_config(
            strategy_id,
            parameters,
            metadata.get("created_by", "system"),
            symbol=symbol,
            reason=metadata.get("reason"),
        )
        return f"{strategy_id}:{symbol}" if ok else None

    async def delete_global_config(self, strategy_id: str) -> bool:
        return await self.client.delete_strategy_config(strategy_id)

    async def delete_symbol_config(self, strategy_id: str, symbol: str) -> bool:
        return await self.client.delete_strategy_config(strategy_id, symbol)

    async def create_audit_record(self, audit_data: dict[str, Any]) -> str | None:
        """The gateway write endpoint atomically creates its audit row."""
        return f"gateway:{audit_data.get('strategy_id')}"

    async def get_audit_trail(
        self, strategy_id: str, symbol: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        return await self.client.get_strategy_audit_trail(strategy_id, symbol, limit)

    async def list_all_strategy_ids(self) -> list[str]:
        return await self.client.list_strategy_configs()

    async def list_symbol_overrides(self, strategy_id: str) -> list[str]:
        return await self.client.list_strategy_symbols(strategy_id)

    async def rollback_strategy_config(
        self,
        strategy_id: str,
        changed_by: str,
        symbol: str | None = None,
        target_version: int | None = None,
        reason: str | None = None,
    ) -> bool:
        return await self.client.rollback_strategy_config(
            strategy_id, changed_by, symbol, target_version, reason
        )
