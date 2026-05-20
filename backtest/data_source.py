"""Historical data sources for the backtest engine.

The engine talks to a `HistoricalDataSource` protocol rather than the
production data-manager client directly. This keeps the engine testable
(swap in a recorded JSON fixture) and lets the CLI bind to the live
`DataManagerClient` without leaking async-IO into the engine itself.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Protocol

import pandas as pd


class HistoricalDataSource(Protocol):
    """Anything that can yield a chronologically-sorted OHLCV DataFrame."""

    def load(
        self,
        *,
        symbol: str,
        period: str,
        range_from: datetime,
        range_to: datetime,
    ) -> pd.DataFrame:
        """Return candles in `[range_from, range_to]` indexed by `timestamp`."""


def _filter_window(
    df: pd.DataFrame, range_from: datetime, range_to: datetime
) -> pd.DataFrame:
    if df.empty:
        return df
    if df.index.name != "timestamp":
        if "timestamp" in df.columns:
            df = df.copy()
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp").set_index("timestamp")
        else:
            raise ValueError("DataFrame must have a 'timestamp' column or index")
    mask = (df.index >= pd.Timestamp(range_from)) & (df.index <= pd.Timestamp(range_to))
    return df.loc[mask]


class FixtureHistoricalSource:
    """Loads candles from a JSON fixture file. Used by tests and offline runs.

    The fixture format is a list of dicts with the same shape data-manager's
    `/candles` endpoint returns: `{"timestamp", "open", "high", "low",
    "close", "volume"}`.
    """

    def __init__(self, fixture_path: Path | str) -> None:
        self._path = Path(fixture_path)

    def load(
        self,
        *,
        symbol: str,
        period: str,
        range_from: datetime,
        range_to: datetime,
    ) -> pd.DataFrame:
        del symbol, period
        records = json.loads(self._path.read_text(encoding="utf-8"))
        df = pd.DataFrame(records)
        if df.empty:
            return df
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = df[col].astype(float)
        df = df.sort_values("timestamp").set_index("timestamp")
        return _filter_window(df, range_from, range_to)


class DataManagerHistoricalSource:
    """Adapter over `ta_bot.services.data_manager_client.DataManagerClient`.

    The live client is limit-based (no native date-range query), so we
    over-fetch and filter in memory. `max_candles` caps the request size
    in line with the data-manager's documented limit; operators who need
    a longer window can pass a larger value at construction time.
    """

    def __init__(
        self,
        *,
        client_factory=None,
        max_candles: int = 1000,
    ) -> None:
        self._client_factory = client_factory
        self._max_candles = max_candles

    def load(
        self,
        *,
        symbol: str,
        period: str,
        range_from: datetime,
        range_to: datetime,
    ) -> pd.DataFrame:
        from ta_bot.services.data_manager_client import DataManagerClient

        factory = self._client_factory or DataManagerClient
        client = factory()

        async def _run() -> pd.DataFrame:
            await client.connect()
            try:
                return await client.fetch_candles(
                    symbol=symbol, period=period, limit=self._max_candles
                )
            finally:
                await client.disconnect()

        df = asyncio.run(_run())
        if df.empty:
            return df
        return _filter_window(df, range_from, range_to)
