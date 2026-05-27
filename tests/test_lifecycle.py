"""
Tests for strategy lifecycle state machine, manager, and API endpoints (FR9).

AC coverage:
  AC1 — state machine (7 states, valid transitions)
  AC2 — lifecycle events persisted with decision_id + reasoning_context
  AC3 — GET /api/v1/strategies/{strategy_id}/lifecycle returns timeline
  AC4 — cross-service CIO join (mocked data-manager)
  AC5 — FR9 can move to GREEN (verified by AC1-AC4 passing)
"""

import os

import pytest

# Disable OTel before any imports
os.environ.setdefault("OTEL_NO_AUTO_INIT", "1")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from ta_bot.models.strategy_config import (
    VALID_LIFECYCLE_TRANSITIONS,
    StrategyLifecycleState,
)
from ta_bot.services.lifecycle_manager import (
    LifecycleTransitionError,
    StrategyLifecycleManager,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_db(current_state: str | None = None, history: list | None = None):
    """Return a MongoDBClient mock pre-wired for lifecycle tests."""
    db = MagicMock()
    db.get_current_lifecycle_state = AsyncMock(return_value=current_state)
    db.create_lifecycle_event = AsyncMock(return_value="mock_event_id_123")
    db.get_lifecycle_history = AsyncMock(return_value=history or [])
    return db


# ---------------------------------------------------------------------------
# AC1 — state machine model
# ---------------------------------------------------------------------------


class TestLifecycleStateMachine:
    def test_all_seven_states_exist(self):
        states = {s.value for s in StrategyLifecycleState}
        expected = {
            "registered",
            "backtested",
            "admitted",
            "live_trial",
            "graduated",
            "demoted",
            "retired",
        }
        assert states == expected

    def test_valid_transitions_cover_all_states(self):
        for state in StrategyLifecycleState:
            assert state in VALID_LIFECYCLE_TRANSITIONS, (
                f"{state} missing from transitions"
            )

    def test_registered_can_go_to_backtested(self):
        assert (
            StrategyLifecycleState.BACKTESTED
            in VALID_LIFECYCLE_TRANSITIONS[StrategyLifecycleState.REGISTERED]
        )

    def test_live_trial_can_graduate(self):
        assert (
            StrategyLifecycleState.GRADUATED
            in VALID_LIFECYCLE_TRANSITIONS[StrategyLifecycleState.LIVE_TRIAL]
        )

    def test_retired_can_re_register(self):
        assert (
            StrategyLifecycleState.REGISTERED
            in VALID_LIFECYCLE_TRANSITIONS[StrategyLifecycleState.RETIRED]
        )


# ---------------------------------------------------------------------------
# AC2 — lifecycle events persist with decision_id + reasoning_context
# ---------------------------------------------------------------------------


class TestLifecycleManagerTransition:
    @pytest.mark.asyncio
    async def test_initial_registration_has_no_from_state(self):
        db = _make_mock_db(current_state=None)
        manager = StrategyLifecycleManager(mongodb_client=db)

        event = await manager.transition(
            strategy_id="test_strategy",
            to_state="registered",
            transitioned_by="operator",
        )

        assert event.from_state is None
        assert event.to_state == StrategyLifecycleState.REGISTERED
        assert event.id == "mock_event_id_123"
        db.create_lifecycle_event.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_transition_persists_decision_id_and_context(self):
        db = _make_mock_db(current_state="admitted")
        manager = StrategyLifecycleManager(mongodb_client=db)

        event = await manager.transition(
            strategy_id="test_strategy",
            to_state="live_trial",
            transitioned_by="cio_agent",
            decision_id="dec_xyz",
            reasoning_context="Sharpe > 1.2 for 30 days",
        )

        assert event.decision_id == "dec_xyz"
        assert event.reasoning_context == "Sharpe > 1.2 for 30 days"
        assert event.to_state == StrategyLifecycleState.LIVE_TRIAL
        call_kwargs = db.create_lifecycle_event.call_args[0][0]
        assert call_kwargs["decision_id"] == "dec_xyz"
        assert call_kwargs["reasoning_context"] == "Sharpe > 1.2 for 30 days"

    @pytest.mark.asyncio
    async def test_invalid_state_raises_error(self):
        db = _make_mock_db(current_state=None)
        manager = StrategyLifecycleManager(mongodb_client=db)

        with pytest.raises(LifecycleTransitionError, match="Unknown lifecycle state"):
            await manager.transition(
                strategy_id="test_strategy",
                to_state="flying",
                transitioned_by="operator",
            )

    @pytest.mark.asyncio
    async def test_invalid_transition_raises_error(self):
        db = _make_mock_db(current_state="graduated")
        manager = StrategyLifecycleManager(mongodb_client=db)

        with pytest.raises(LifecycleTransitionError, match="Invalid transition"):
            await manager.transition(
                strategy_id="test_strategy",
                to_state="registered",
                transitioned_by="operator",
            )


# ---------------------------------------------------------------------------
# AC3 — GET lifecycle history endpoint
# ---------------------------------------------------------------------------


class TestLifecycleAPI:
    """Integration tests against the FastAPI app (TestClient)."""

    @pytest.fixture(autouse=True)
    def setup_app(self):
        from ta_bot.api import config_routes
        from ta_bot.health import app

        self._db = _make_mock_db(
            current_state="live_trial",
            history=[
                {
                    "_id": "abc123",
                    "strategy_id": "rsi_extreme_reversal",
                    "from_state": "admitted",
                    "to_state": "live_trial",
                    "transitioned_at": datetime(2026, 5, 27, 10, 0, 0),
                    "transitioned_by": "cio_agent",
                    "decision_id": None,
                    "reasoning_context": "30-day gate passed",
                }
            ],
        )
        lm = StrategyLifecycleManager(mongodb_client=self._db)
        config_routes.set_lifecycle_manager(lm)
        self.client = TestClient(app)
        yield
        config_routes._lifecycle_manager = None

    def test_get_lifecycle_returns_200(self):
        resp = self.client.get("/api/v1/strategies/rsi_extreme_reversal/lifecycle")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["strategy_id"] == "rsi_extreme_reversal"
        assert body["data"]["current_state"] == "live_trial"
        assert len(body["data"]["events"]) == 1

    def test_get_lifecycle_event_fields(self):
        resp = self.client.get("/api/v1/strategies/rsi_extreme_reversal/lifecycle")
        event = resp.json()["data"]["events"][0]
        assert event["from_state"] == "admitted"
        assert event["to_state"] == "live_trial"
        assert event["transitioned_by"] == "cio_agent"

    def test_get_lifecycle_empty_history(self):
        self._db.get_lifecycle_history.return_value = []
        self._db.get_current_lifecycle_state.return_value = None
        resp = self.client.get("/api/v1/strategies/unknown_strategy/lifecycle")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["current_state"] is None
        assert data["events"] == []

    def test_post_transition_returns_201(self):
        self._db.get_current_lifecycle_state.return_value = "admitted"
        resp = self.client.post(
            "/api/v1/strategies/rsi_extreme_reversal/lifecycle/transition",
            json={
                "to_state": "live_trial",
                "transitioned_by": "cio_agent",
                "decision_id": "dec_123",
                "reasoning_context": "Passed gate",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["to_state"] == "live_trial"
        assert body["data"]["decision_id"] == "dec_123"

    def test_post_invalid_transition_returns_error(self):
        self._db.get_current_lifecycle_state.return_value = "graduated"
        resp = self.client.post(
            "/api/v1/strategies/rsi_extreme_reversal/lifecycle/transition",
            json={
                "to_state": "registered",
                "transitioned_by": "operator",
            },
        )
        # Route uses HTTP 201 as default; errors are signalled via success:false in body
        assert resp.status_code == 201
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "INVALID_TRANSITION"


# ---------------------------------------------------------------------------
# AC4 — cross-service CIO join (mocked)
# ---------------------------------------------------------------------------


class TestCIOJoin:
    @pytest.mark.asyncio
    async def test_join_enriches_events_with_cio_context(self):
        db = _make_mock_db(
            history=[
                {
                    "_id": "ev1",
                    "strategy_id": "s1",
                    "from_state": "admitted",
                    "to_state": "live_trial",
                    "transitioned_at": datetime(2026, 5, 27),
                    "transitioned_by": "cio_agent",
                    "decision_id": "dec_abc",
                    "reasoning_context": None,
                }
            ]
        )
        manager = StrategyLifecycleManager(
            mongodb_client=db,
            data_manager_url="http://data-manager-mock",
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "data": {"cio_decision": "buy", "confidence": 0.85},
            }
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await manager.get_history("s1", join_cio=True)

        assert result["cio_join_status"] == "ok"
        assert result["events"][0]["cio_context"] == {
            "cio_decision": "buy",
            "confidence": 0.85,
        }

    @pytest.mark.asyncio
    async def test_join_unavailable_degrades_gracefully(self):
        db = _make_mock_db(
            history=[
                {
                    "_id": "ev1",
                    "strategy_id": "s1",
                    "from_state": None,
                    "to_state": "registered",
                    "transitioned_at": datetime(2026, 5, 27),
                    "transitioned_by": "operator",
                    "decision_id": "dec_xyz",
                    "reasoning_context": None,
                }
            ]
        )
        manager = StrategyLifecycleManager(
            mongodb_client=db,
            data_manager_url="http://data-manager-mock",
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=Exception("connection refused"))
            mock_client_cls.return_value = mock_client

            result = await manager.get_history("s1", join_cio=True)

        assert result["cio_join_status"] in {"partial", "unavailable"}
        assert result["events"][0]["cio_context"] is None
