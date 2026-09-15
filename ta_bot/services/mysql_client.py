"""
MySQL client for fetching candle data and persisting signals.

Per petrosa-bot-ta-analysis#284 (petrosa_k8s#1059 epic): persistence goes
exclusively through the Data Manager gateway (`DataManagerClient`). The
legacy raw-`pymysql` direct-MySQL fallback (`USE_DATA_MANAGER=false`) has
been removed — the shared DBaaS enforces a hard `max_user_connections=30`
ceiling across every service, and only `petrosa-data-manager` is allowed to
hold a connection pool. This service must never open a direct MySQL socket.
"""

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# Import Data Manager client
try:
    from .data_manager_client import DataManagerClient

    DATA_MANAGER_AVAILABLE = True
except ImportError as _dm_import_error:
    # AC3 (#267): fail loud, not silent. A missing/broken Data Manager client
    # import used to be swallowed here with no log line. Per #284 there is no
    # raw-MySQL fallback left to silently drop into, so this is now a hard
    # construction-time error (see MySQLClient.__init__) rather than a
    # degraded mode — but we still log at import time so the failure is
    # observable in deployed logs before the first construction attempt.
    logger.warning(
        "Data Manager client unavailable (%s: %s) — MySQLClient has NO "
        "raw-MySQL fallback (removed per #284) and will raise on "
        "construction. Fix the '.data_manager_client' import.",
        type(_dm_import_error).__name__,
        _dm_import_error,
    )
    DATA_MANAGER_AVAILABLE = False
    DataManagerClient = None


class MySQLClient:
    """
    Thin persistence facade backed exclusively by the Data Manager gateway.

    Per #284, this class no longer supports a direct/raw MySQL connection
    path. It exists so existing call sites (`NATSListener`, config managers)
    do not need to change their `connect()`/`fetch_candles()`/`persist_*()`
    call shape while the underlying transport is entirely HTTP to
    data-manager.
    """

    def __init__(self, use_data_manager: bool | None = None):
        """
        Initialize the MySQL client.

        Args:
            use_data_manager: Retained for call-site backward compatibility.
                Must be truthy (or omitted) — explicitly passing `False`
                raises `RuntimeError` immediately: the raw-MySQL fallback
                that flag used to select was removed in #284.
        """
        if use_data_manager is False:
            raise RuntimeError(
                "MySQLClient(use_data_manager=False) is no longer supported "
                "(petrosa-bot-ta-analysis#284): the raw-pymysql direct-MySQL "
                "fallback was removed. All persistence goes through the "
                "Data Manager gateway; do not construct a direct connection."
            )
        if not DATA_MANAGER_AVAILABLE:
            raise RuntimeError(
                "Data Manager client unavailable — MySQLClient has no "
                "raw-MySQL fallback (removed per #284). Fix the "
                "'.data_manager_client' import instead of relying on a "
                "direct connection."
            )

        self.use_data_manager = True
        self.data_manager_client = DataManagerClient()
        self.connection: Any = None  # No direct MySQL connection ever held.
        logger.info("Using Data Manager for data access")

    async def connect(self):
        """Connect via the Data Manager gateway."""
        await self.data_manager_client.connect()

    async def disconnect(self):
        """Disconnect from the Data Manager gateway."""
        await self.data_manager_client.disconnect()

    async def fetch_candles(
        self, symbol: str, period: str, limit: int = 250
    ) -> pd.DataFrame:
        """Fetch candle data via the Data Manager gateway."""
        return await self.data_manager_client.fetch_candles(symbol, period, limit)

    async def persist_signal(self, signal_data: dict[str, Any]) -> bool:
        """Persist a single signal via the Data Manager gateway."""
        return await self.data_manager_client.persist_signal(signal_data)

    async def persist_signals_batch(self, signals: list[dict[str, Any]]) -> bool:
        """Persist multiple signals via the Data Manager gateway in a batch."""
        return await self.data_manager_client.persist_signals_batch(signals)
