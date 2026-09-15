"""
Regression tests for petrosa-bot-ta-analysis#271.

Bug: StrategyConfigManager was never instantiated or registered via
config_routes.set_config_manager() in main.py, so config_routes._config_manager
stayed None and every /api/v1/strategies/*/config, /api/v1/strategies (list),
and /api/v1/config/validate endpoint permanently returned 503
"Strategy configuration manager not initialized". Additionally,
ta_bot/health.py defined a decoy no-op set_config_manager() (body: pass) which
looked like it wired things up but silently did nothing.

This test asserts that once a real StrategyConfigManager is registered via
config_routes.set_config_manager() (mirroring the wiring main.py now performs
at startup), at least one config endpoint responds without a 503.
"""

from fastapi.testclient import TestClient

from ta_bot.api import config_routes
from ta_bot.health import app
from ta_bot.services.config_manager import StrategyConfigManager


class TestConfigManagerRegistration271:
    """Ensure the strategy config manager DI wiring is in place."""

    def setup_method(self):
        # mongodb_client=None is fine here: list_strategies() and the other
        # read paths degrade gracefully (no global/symbol overrides reported)
        # when no database is attached. The point of this test is DI wiring,
        # not persistence behavior.
        self._manager = StrategyConfigManager(mongodb_client=None)
        config_routes.set_config_manager(self._manager)
        self.client = TestClient(app)

    def teardown_method(self):
        config_routes._config_manager = None

    def test_config_manager_not_none_after_registration(self):
        assert config_routes.get_config_manager() is self._manager

    def test_list_strategies_endpoint_does_not_503(self):
        """GET /api/v1/strategies previously always 503'd (#271)."""
        resp = self.client.get("/api/v1/strategies")
        assert resp.status_code != 503
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True

    def test_get_config_manager_raises_503_when_unregistered(self):
        """Sanity check: the 503 behavior is real when nothing is registered
        (i.e. this test module isn't accidentally asserting a no-op)."""
        config_routes._config_manager = None
        resp = self.client.get("/api/v1/strategies")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "INTERNAL_ERROR"
