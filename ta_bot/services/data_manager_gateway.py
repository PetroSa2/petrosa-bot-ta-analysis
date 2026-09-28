"""Data Manager gateway for candles and signal persistence."""

from typing import Any

import pandas as pd

from .data_manager_client import DataManagerClient


class DataManagerGateway:
    """Thin HTTP gateway backed exclusively by Data Manager."""

    def __init__(self):
        self.data_manager_client = DataManagerClient()
        self.connection: Any = None

    async def connect(self):
        await self.data_manager_client.connect()

    async def disconnect(self):
        await self.data_manager_client.disconnect()

    async def fetch_candles(
        self, symbol: str, period: str, limit: int = 250
    ) -> pd.DataFrame:
        return await self.data_manager_client.fetch_candles(symbol, period, limit)

    async def persist_signal(self, signal_data: dict[str, Any]) -> bool:
        return await self.data_manager_client.persist_signal(signal_data)

    async def persist_signals_batch(self, signals: list[dict[str, Any]]) -> bool:
        return await self.data_manager_client.persist_signals_batch(signals)
