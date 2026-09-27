"""Data-manager-backed persistence for strategy lifecycle events."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class DataManagerLifecycleStore:
    """Persist lifecycle events through the data-manager HTTP API."""

    def __init__(self, base_url: str | None, timeout: float = 5.0) -> None:
        self._base_url = (base_url or "").rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def get_current_lifecycle_state(self, strategy_id: str) -> str | None:
        """Return the newest lifecycle state's value, or ``None`` on failure."""
        try:
            response = await self._client.get(
                f"{self._base_url}/api/v1/strategies/{strategy_id}/lifecycle/state"
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json().get("state")
        except Exception as exc:
            logger.error("Error fetching current lifecycle state for %s: %s", strategy_id, exc)
            return None

    async def create_lifecycle_event(self, event_data: dict[str, Any]) -> str | None:
        """Create one lifecycle event and return its data-manager ID."""
        strategy_id = event_data.get("strategy_id")
        payload = {
            "from_state": event_data.get("from_state"),
            "to_state": event_data.get("to_state"),
            "transitioned_by": event_data.get("transitioned_by", ""),
            "reason": event_data.get("reasoning_context"),
            "transitioned_at": event_data.get("transitioned_at"),
            "service": "ta-bot",
        }
        try:
            response = await self._client.post(
                f"{self._base_url}/api/v1/strategies/{strategy_id}/lifecycle/events",
                json=payload,
                params={"service": "ta-bot"},
            )
            response.raise_for_status()
            return response.json().get("event_id")
        except Exception as exc:
            logger.error("Error creating lifecycle event for %s: %s", strategy_id, exc)
            return None

    async def get_lifecycle_history(
        self, strategy_id: str, limit: int = 500
    ) -> list[dict[str, Any]]:
        """Return lifecycle events in ascending transition time order."""
        try:
            response = await self._client.get(
                f"{self._base_url}/api/v1/strategies/{strategy_id}/lifecycle/events",
                params={"limit": limit, "order": "asc", "service": "ta-bot"},
            )
            if response.status_code == 404:
                return []
            response.raise_for_status()
            return response.json().get("events", [])
        except Exception as exc:
            logger.error("Error fetching lifecycle history for %s: %s", strategy_id, exc)
            return []
