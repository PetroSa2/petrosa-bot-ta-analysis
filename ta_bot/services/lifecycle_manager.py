"""
Strategy lifecycle manager (FR9).

Handles admit→trial→graduate→demote→retire state-machine transitions
and provides the operator-queryable lifecycle timeline.
"""

import logging
from datetime import datetime
from typing import Any

try:
    from datetime import UTC
except ImportError:
    from datetime import timezone

    UTC = timezone.utc  # noqa: UP017

import httpx

from ta_bot.db.mongodb_client import MongoDBClient
from ta_bot.models.strategy_config import (
    VALID_LIFECYCLE_TRANSITIONS,
    StrategyLifecycleEvent,
    StrategyLifecycleState,
)

logger = logging.getLogger(__name__)

_DATA_MANAGER_JOIN_TIMEOUT = 3.0


class LifecycleTransitionError(ValueError):
    """Raised when a requested state transition is invalid."""


class StrategyLifecycleManager:
    """
    Manages strategy lifecycle state transitions and history queries.

    Persist transitions to `strategy_lifecycle_events` MongoDB collection.
    Optionally enriches timeline events with CIO context from the
    data-manager LifecycleRepository (AC4, best-effort with timeout).
    """

    def __init__(
        self,
        mongodb_client: MongoDBClient,
        data_manager_url: str | None = None,
    ) -> None:
        self._db = mongodb_client
        self._data_manager_url = data_manager_url

    # ------------------------------------------------------------------
    # State transition (AC1 + AC2)
    # ------------------------------------------------------------------

    async def transition(
        self,
        strategy_id: str,
        to_state: str,
        transitioned_by: str,
        decision_id: str | None = None,
        reasoning_context: str | None = None,
    ) -> StrategyLifecycleEvent:
        """
        Record a lifecycle state transition for strategy_id.

        Validates the transition against the state machine, then persists the event.

        Args:
            strategy_id: Strategy being transitioned.
            to_state: Target state (string value of StrategyLifecycleState).
            transitioned_by: Actor ID.
            decision_id: Optional CIO decision_id for cross-service join.
            reasoning_context: Human-readable reason.

        Returns:
            Persisted StrategyLifecycleEvent.

        Raises:
            LifecycleTransitionError: if to_state is unknown or the transition is invalid.
        """
        try:
            to_state_enum = StrategyLifecycleState(to_state)
        except ValueError:
            valid = [s.value for s in StrategyLifecycleState]
            raise LifecycleTransitionError(
                f"Unknown lifecycle state '{to_state}'. Valid states: {valid}"
            )

        current_state_str = await self._db.get_current_lifecycle_state(strategy_id)
        if current_state_str is not None:
            try:
                current_state_enum = StrategyLifecycleState(current_state_str)
            except ValueError:
                current_state_enum = None

            if current_state_enum is not None:
                allowed = VALID_LIFECYCLE_TRANSITIONS.get(current_state_enum, [])
                if to_state_enum not in allowed:
                    raise LifecycleTransitionError(
                        f"Invalid transition for {strategy_id}: "
                        f"'{current_state_str}' → '{to_state}'. "
                        f"Allowed from '{current_state_str}': "
                        f"{[s.value for s in allowed]}"
                    )

        event = StrategyLifecycleEvent(
            strategy_id=strategy_id,
            from_state=StrategyLifecycleState(current_state_str)
            if current_state_str
            else None,
            to_state=to_state_enum,
            transitioned_at=datetime.now(UTC),
            transitioned_by=transitioned_by,
            decision_id=decision_id,
            reasoning_context=reasoning_context,
        )

        event_data = event.model_dump(mode="json")
        event_data.pop("id", None)

        inserted_id = await self._db.create_lifecycle_event(event_data)
        event.id = inserted_id
        return event

    # ------------------------------------------------------------------
    # History query (AC3 + AC4)
    # ------------------------------------------------------------------

    async def get_history(
        self, strategy_id: str, join_cio: bool = True
    ) -> dict[str, Any]:
        """
        Return the full lifecycle timeline for strategy_id.

        Optionally enriches events with CIO context from data-manager
        LifecycleRepository (best-effort; degraded gracefully on timeout).

        Returns:
            Dict with keys: current_state, events (list), cio_join_status
        """
        raw_events = await self._db.get_lifecycle_history(strategy_id)

        events = []
        for doc in raw_events:
            doc_id = str(doc.get("_id", doc.get("id", "")))
            transitioned_at = doc.get("transitioned_at")
            if isinstance(transitioned_at, datetime):
                transitioned_at = transitioned_at.isoformat()

            events.append(
                {
                    "id": doc_id,
                    "strategy_id": doc.get("strategy_id", strategy_id),
                    "from_state": doc.get("from_state"),
                    "to_state": doc.get("to_state"),
                    "transitioned_at": transitioned_at,
                    "transitioned_by": doc.get("transitioned_by", ""),
                    "decision_id": doc.get("decision_id"),
                    "reasoning_context": doc.get("reasoning_context"),
                    "cio_context": None,
                }
            )

        current_state = events[-1]["to_state"] if events else None

        cio_join_status = "not_attempted"
        if join_cio and self._data_manager_url and events:
            cio_join_status = await self._enrich_with_cio_context(events)

        return {
            "current_state": current_state,
            "events": events,
            "cio_join_status": cio_join_status,
        }

    async def _enrich_with_cio_context(self, events: list[dict[str, Any]]) -> str:
        """
        AC4: attempt to merge CIO context from data-manager LifecycleRepository.

        Calls GET /api/v1/lifecycle/reconstruct?decision_id=<id> for each event
        that has a decision_id. Best-effort — any network failure sets status to
        'partial' or 'unavailable' without raising.

        Returns:
            cio_join_status string: "ok" | "partial" | "unavailable"
        """
        decision_ids = [e["decision_id"] for e in events if e.get("decision_id")]
        if not decision_ids:
            return "not_attempted"

        hits = 0
        base_url = self._data_manager_url.rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=_DATA_MANAGER_JOIN_TIMEOUT) as client:
                for event in events:
                    decision_id = event.get("decision_id")
                    if not decision_id:
                        continue
                    try:
                        response = await client.get(
                            f"{base_url}/api/v1/lifecycle/reconstruct",
                            params={"decision_id": decision_id},
                        )
                        if response.status_code == 200:
                            data = response.json()
                            if data.get("success") and data.get("data"):
                                event["cio_context"] = data["data"]
                                hits += 1
                    except Exception as exc:
                        logger.debug(
                            f"CIO context fetch failed for {decision_id}: {exc}"
                        )
        except Exception as exc:
            logger.warning(f"CIO join unavailable: {exc}")
            return "unavailable"

        if hits == 0:
            return "partial"
        if hits < len(decision_ids):
            return "partial"
        return "ok"
