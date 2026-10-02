"""Candle loading through the data-manager HTTP API."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import pandas as pd


class MissingBarsError(ValueError):
    """The requested candle window is incomplete."""

    def __init__(self, gaps: list[str]) -> None:
        self.gaps = gaps
        super().__init__(f"missing candle bars: {', '.join(gaps)}")


def expected_timestamps(
    start: datetime, end: datetime, timeframe: str
) -> pd.DatetimeIndex:
    if timeframe.endswith("m"):
        frequency = f"{int(timeframe[:-1])}min"
    elif timeframe.endswith("h"):
        frequency = f"{int(timeframe[:-1])}h"
    else:
        raise ValueError(f"unsupported timeframe: {timeframe}")
    return pd.date_range(start=start, end=end, freq=frequency, tz="UTC")


def normalize_candles(
    records: Any, start: datetime, end: datetime, timeframe: str
) -> pd.DataFrame:
    frame = records if isinstance(records, pd.DataFrame) else pd.DataFrame(records)
    if frame.empty:
        raise MissingBarsError([start.isoformat()])
    if "timestamp" not in frame.columns and frame.index.name != "timestamp":
        raise ValueError("candle data must contain timestamp")
    if "timestamp" in frame.columns:
        frame = frame.copy()
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        frame = frame.set_index("timestamp")
    else:
        frame = frame.copy()
        frame.index = pd.to_datetime(frame.index, utc=True)
    start_ts = pd.Timestamp(start).tz_convert("UTC")
    end_ts = pd.Timestamp(end).tz_convert("UTC")
    frame = frame.sort_index().loc[start_ts:end_ts]
    expected = expected_timestamps(start, end, timeframe)
    gaps = expected.difference(frame.index)
    if len(gaps):
        raise MissingBarsError([value.isoformat() for value in gaps])
    required = ("open", "high", "low", "close", "volume")
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"candle data missing columns: {', '.join(missing)}")
    return frame.loc[:, required].astype(float)


class DataManagerCandleLoader:
    """Synchronous adapter around the existing asynchronous API client."""

    def __init__(self, client_factory=None, limit: int = 10_000) -> None:
        self.client_factory = client_factory
        self.limit = limit

    def load(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        from ta_bot.services.data_manager_client import DataManagerClient

        client = (self.client_factory or DataManagerClient)()

        async def fetch():
            await client.connect()
            try:
                return await client.fetch_candles(
                    symbol=symbol, period=timeframe, limit=self.limit
                )
            finally:
                await client.disconnect()

        return normalize_candles(asyncio.run(fetch()), start, end, timeframe)
